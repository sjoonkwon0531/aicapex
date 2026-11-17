"""Stage x constraint delay model for US data center capacity (9 states).

Inputs (data/):
  tranches.csv     capacity tranche per state x stage: GW range, baseline online year,
                   attrition range. Baseline year = the utility/ISO/contract schedule
                   before the frictions in constraints.csv.
  constraints.csv  per state x stage: constraint type, probability it is active,
                   added delay range (months). Mostly research assessments (see README).

Method (one Monte Carlo draw):
  1. Two latent shocks: z_power (generation, interconnect, equipment) and
     z_social (politics, local, tax, water), correlated with rho. The correlation
     encodes the coupling: power scarcity -> bills -> political backlash.
  2. Each active constraint's delay = low + (high-low) * Phi(sqrt(w) z_factor + sqrt(1-w) e).
  3. Constraints at one stage act in parallel (gates): stage delay = max of active ones.
     The max is the binding constraint.
  4. A tranche at stage k also passes the later stages (k-1 ... S1). Their delays are
     added with pass-through alpha (temporary measures may lapse before it arrives).
  5. Online time = baseline year + total delay. Attrition removes a share of GW
     (identical in baseline and delayed runs, so the comparison is pure timing).

Units: utility contract/load MW of mixed basis. Use outputs for timing and shares,
not as absolute GW comparable with Morgan Stanley's IT-capacity figures.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
STAGES = ["S1", "S2", "S3", "S4"]
FACTOR = {"generation": "power", "interconnect": "power", "equipment": "power",
          "politics": "social", "local": "social", "tax": "social", "water": "social"}
LOADING = {"equipment": 0.3}   # equipment lead times mostly independent of the grid shock
DEFAULT_W = 0.6
YEARS = np.arange(2026, 2036)
LAST = {}  # per-draw state x year cumulative arrays from the latest simulate() call


def load(raw=False, k_far=None):
    """Tranches and constraints. Unless raw=True, delay ranges are scaled by the
    severity calibration in data/severity.csv (k_near for S1-S2, k_far for S3-S4)."""
    tr = pd.read_csv(HERE / "data/tranches.csv")
    co = pd.read_csv(HERE / "data/constraints.csv").astype({"delay_low": float, "delay_high": float})
    sev = HERE / "data/severity.csv"
    if not raw and sev.exists():
        s = pd.read_csv(sev).iloc[0]
        kf = s.k_far if k_far is None else k_far
        near = co.stage.isin(["S1", "S2"])
        for col in ("delay_low", "delay_high"):
            co.loc[near, col] *= s.k_near
            co.loc[~near, col] *= kf
    return tr, co


def simulate(tr, co, n=20000, rho=0.5, alpha=0.5, seed=7):
    rng = np.random.default_rng(seed)
    cov = np.array([[1, rho], [rho, 1]])
    z = rng.multivariate_normal([0, 0], cov, size=n)
    zf = {"power": z[:, 0], "social": z[:, 1]}

    def stage_delay(state, stage):
        """Return (delay months, binding constraint name or '') arrays for one stage."""
        rows = co[(co.state == state) & (co.stage == stage)]
        if rows.empty:
            return np.zeros(n), np.full(n, "", dtype=object)
        d = np.zeros((n, len(rows)))
        for j, r in enumerate(rows.itertuples()):
            w = LOADING.get(r.constraint, DEFAULT_W)
            u = norm.cdf(np.sqrt(w) * zf[FACTOR[r.constraint]] + np.sqrt(1 - w) * rng.standard_normal(n))
            active = rng.random(n) < r.p_active
            d[:, j] = np.where(active, r.delay_low + (r.delay_high - r.delay_low) * u, 0.0)
        idx = d.argmax(axis=1)
        dmax = d.max(axis=1)
        names = rows.constraint.to_numpy()[idx].astype(object)
        names[dmax <= 0] = ""
        return dmax, names

    recs, online_base, online_delay = [], {}, {}
    tranche_log = []
    for t in tr.itertuples():
        k = STAGES.index(t.stage)
        own, own_bind = stage_delay(t.state, t.stage)
        down = np.zeros(n)
        for s in STAGES[:k]:
            dd, _ = stage_delay(t.state, s)
            down += alpha * dd
        total = own + down
        gw = rng.uniform(t.gw_low, t.gw_high, n) * (1 - rng.uniform(t.attrition_low, t.attrition_high, n))
        # spread each tranche over +/-0.5 yr around its baseline year (avoids year-edge artifacts)
        b0 = t.base_year + rng.uniform(-0.5, 0.5, n)
        yb = np.floor(b0).astype(int)
        yd = np.floor(b0 + total / 12.0).astype(int)
        tranche_log.append((t.state, t.stage, yb, yd, gw))
        for y in YEARS:
            online_base.setdefault((t.state, y), np.zeros(n))
            online_delay.setdefault((t.state, y), np.zeros(n))
            online_base[(t.state, y)] += np.where(yb <= y, gw, 0.0)
            online_delay[(t.state, y)] += np.where(yd <= y, gw, 0.0)
        shares = pd.Series(own_bind).replace("", "none").value_counts(normalize=True)
        recs.append({
            "state": t.state, "stage": t.stage, "gw_mid": (t.gw_low + t.gw_high) / 2,
            "base_year": t.base_year,
            "own_delay_p50": np.median(own), "total_delay_p10": np.percentile(total, 10),
            "total_delay_p50": np.median(total), "total_delay_p90": np.percentile(total, 90),
            "binding_top": shares.drop("none", errors="ignore").idxmax() if (shares.drop("none", errors="ignore").size) else "none",
            **{f"bind_{c}": shares.get(c, 0.0) for c in list(FACTOR) + ["none"]},
        })
    # utility connection throughput caps (GW/yr): excess rolls into the next year
    if (HERE / "data/throughput.csv").exists():
        caps = pd.read_csv(HERE / "data/throughput.csv")
        for c in caps.itertuples():
            if c.state not in set(tr.state):
                continue
            cap = rng.uniform(c.cap_low, c.cap_high, n)
            carry = np.zeros(n)
            prev_raw = np.zeros(n)
            cum = np.zeros(n)
            for y in YEARS:
                raw = online_delay[(c.state, y)]
                if y >= c.from_year:
                    avail = (raw - prev_raw) + carry
                    take = np.minimum(avail, cap)
                    carry = avail - take
                else:
                    take = raw - prev_raw
                prev_raw = raw.copy()
                cum = cum + take
                online_delay[(c.state, y)] = cum.copy()
    stage_tab = pd.DataFrame(recs)
    yr = []
    for (s, y), b in online_base.items():
        d = online_delay[(s, y)]
        yr.append({"state": s, "year": y, "base_p50": np.median(b),
                   "delay_p10": np.percentile(d, 10), "delay_p50": np.median(d),
                   "delay_p90": np.percentile(d, 90)})
    year_tab = pd.DataFrame(yr).sort_values(["state", "year"])
    agg = {}
    for y in YEARS:
        b = sum(online_base[(s, y)] for s in tr.state.unique())
        d = sum(online_delay[(s, y)] for s in tr.state.unique())
        agg[y] = (b, d)
    rows = []
    for y, (b, d) in agg.items():
        bp, dp = agg.get(y - 1, (0 * b, 0 * d))
        rows.append({"year": y, "base_p50": np.median(b), "delay_p10": np.percentile(d, 10),
                     "delay_p50": np.median(d), "delay_p90": np.percentile(d, 90),
                     "gap_p50": np.median(b - d),
                     "add_base_p50": np.median(b - bp), "add_delay_p50": np.median(d - dp),
                     "add_delay_p10": np.percentile(d - dp, 10), "add_delay_p90": np.percentile(d - dp, 90)})
    agg_tab = pd.DataFrame(rows)
    LAST.update(base=online_base, delay=online_delay, tranches=tranche_log, states=list(tr.state.unique()), n=n)
    return stage_tab, year_tab, agg_tab, agg


def gw_weighted_binding(stage_tab):
    cols = [c for c in stage_tab.columns if c.startswith("bind_") and c != "bind_none"]
    out = {}
    for st in STAGES:
        m = stage_tab.stage == st
        tot = (stage_tab.loc[m, cols].mul(stage_tab.loc[m, "gw_mid"], axis=0)).sum()
        out[st] = (tot / tot.sum()).rename(lambda c: c[5:])
    return pd.DataFrame(out).T.round(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--rho", type=float, default=0.5)
    ap.add_argument("--alpha", type=float, default=0.5)
    a = ap.parse_args()
    tr, co = load()
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    st, yt, ag, _ = simulate(tr, co, a.n, a.rho, a.alpha)
    st.round(3).to_csv(out / "delay_by_state_stage.csv", index=False)
    yt.round(3).to_csv(out / "online_by_year.csv", index=False)
    ag.round(3).to_csv(out / "online_9states.csv", index=False)
    gw_weighted_binding(st).to_csv(out / "binding_share_by_stage.csv")
    # sensitivity on the two structural assumptions
    sens = []
    for rho in (0.0, 0.5, 0.8):
        for alpha in (0.0, 0.5, 1.0):
            _, _, g, _ = simulate(tr, co, 8000, rho, alpha, seed=11)
            r = g.set_index("year")
            sens.append({"rho": rho, "alpha": alpha,
                         **{f"gap{y}_p50": r.loc[y, "gap_p50"] for y in (2027, 2028, 2029, 2030, 2031)},
                         **{f"ratio{y}": r.loc[y, "delay_p50"] / r.loc[y, "base_p50"] for y in (2028, 2029, 2030)},
                         "band2029_p10_p90": r.loc[2029, "delay_p90"] - r.loc[2029, "delay_p10"]})
    pd.DataFrame(sens).round(3).to_csv(out / "sensitivity.csv", index=False)
    # counterfactuals: switch off one family of constraints at a time
    cf = []
    for name, drop in (("all", []), ("no_social", ["politics", "local", "tax", "water"]),
                       ("no_power", ["generation", "interconnect"]), ("no_equipment", ["equipment"])):
        c2 = co.copy()
        c2.loc[c2.constraint.isin(drop), "p_active"] = 0.0
        _, _, g, _ = simulate(tr, c2, 8000, a.rho, a.alpha, seed=11)
        r = g.set_index("year")
        cf.append({"case": name, **{f"cum{y}": r.loc[y, "delay_p50"] for y in (2027, 2028, 2029, 2030, 2031)},
                   **{f"add{y}": r.loc[y, "add_delay_p50"] for y in (2027, 2028, 2029, 2030, 2031)}})
    base = g.set_index("year")
    cf.append({"case": "baseline_schedule", **{f"cum{y}": base.loc[y, "base_p50"] for y in (2027, 2028, 2029, 2030, 2031)},
               **{f"add{y}": base.loc[y, "add_base_p50"] for y in (2027, 2028, 2029, 2030, 2031)}})
    pd.DataFrame(cf).round(2).to_csv(out / "counterfactuals.csv", index=False)
    print(pd.DataFrame(cf).round(1).to_string(index=False))
    print(st[["state", "stage", "gw_mid", "own_delay_p50", "total_delay_p10", "total_delay_p50",
              "total_delay_p90", "binding_top"]].round(1).to_string(index=False))
    print(ag.round(1).to_string(index=False))
    print(gw_weighted_binding(st))
    print(pd.DataFrame(sens).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
