"""Convert modelled contract-MW energization into (a) IT capacity online and
(b) grid power demand, then compare with Morgan Stanley's US IT-capacity additions.

Conversion (per tranche-year, per draw):
  energized contract C in year y (assumed mid-year)
  fill(a)  = f0 + (1 - f0) * min(a / R, 1)     share of contract built out and equipped, a = age (yr)
  IT(a)    = C * fill(a) / PUE                  IT (critical) capacity online
  load(a)  = C * fill(a) * LF                   grid demand (LF = mature demand / contract)
Parameter ranges (data/conversion.csv) come from Dominion (5-yr ramp, 63% mature utilization),
PPL (ESA 70%), and the ERCOT observed/approved ratio (44-46%).

US scaling: the 9 states hold ~58-68% of the DCMap US pipeline (Aug 2026). Pipeline share is
not the same as share of annual additions, so the US-scaled line is indicative only.
"""
from pathlib import Path

import numpy as np
import pandas as pd

import model

HERE = Path(__file__).resolve().parent
P = pd.read_csv(HERE / "data/conversion.csv").set_index("param")
MS = {"rev": {2028: 19.9, 2029: 27.6}, "prev": {2028: 24.9, 2029: 22.7}}  # US IT GW additions


def draws(name, n, rng):
    r = P.loc[name]
    return rng.uniform(r.low, r.high, n)


def convert(cum_by_state_year, states, n, rng_seed=3):
    rng = np.random.default_rng(rng_seed)
    f0, R, LF, PUE, share = (draws(k, n, rng) for k in ("f0", "ramp_years", "load_factor", "pue", "us_share"))
    yrs = model.YEARS
    it_cum = {y: np.zeros(n) for y in yrs}
    ld_cum = {y: np.zeros(n) for y in yrs}
    for s in states:
        prev = np.zeros(n)
        for y in yrs:
            inc = cum_by_state_year[(s, y)] - prev
            prev = cum_by_state_year[(s, y)]
            for Y in yrs[yrs >= y]:
                age = (Y + 1) - (y + 0.5)              # at end of year Y
                fill = f0 + (1 - f0) * np.minimum(age / R, 1.0)
                it_cum[Y] += inc * fill / PUE
                ld_cum[Y] += inc * fill * LF
    return it_cum, ld_cum, share


def summarise(it_cum, ld_cum, share, label):
    rows, prev_it = [], 0
    for y in model.YEARS:
        add = it_cum[y] - prev_it
        prev_it = it_cum[y]
        us = add / share
        rows.append({"case": label, "year": y,
                     "it_cum_p50": np.median(it_cum[y]), "it_add_p10": np.percentile(add, 10),
                     "it_add_p50": np.median(add), "it_add_p90": np.percentile(add, 90),
                     "us_it_add_p10": np.percentile(us, 10), "us_it_add_p50": np.median(us),
                     "us_it_add_p90": np.percentile(us, 90),
                     "load_cum_p50": np.median(ld_cum[y])})
    return rows


def main():
    tr, co = model.load()
    out = []
    store = {}
    for label, drop in (("all", []), ("no_social", ["politics", "local", "tax", "water"])):
        c2 = co.copy()
        c2.loc[c2.constraint.isin(drop), "p_active"] = 0.0
        model.simulate(tr, c2, 8000, 0.5, 0.5, seed=11)
        L = dict(model.LAST)
        it, ld, sh = convert(L["delay"], L["states"], L["n"])
        out += summarise(it, ld, sh, label)
        store[label] = (it, sh)
        if label == "all":
            itb, ldb, shb = convert(L["base"], L["states"], L["n"])
            out += summarise(itb, ldb, shb, "baseline_schedule")
    df = pd.DataFrame(out).round(2)
    df.to_csv(HERE / "out/conversion.csv", index=False)
    # political effect in IT terms (paired draws: same seeds)
    it_a, sh = store["all"]
    it_n, _ = store["no_social"]
    pol = []
    for y in (2027, 2028, 2029, 2030, 2031):
        add_a = it_a[y] - it_a[y - 1]
        add_n = it_n[y] - it_n[y - 1]
        d = (add_a - add_n) / sh
        pol.append({"year": y, "us_it_add_effect_p50": np.median(d),
                    "us_it_add_effect_p10": np.percentile(d, 10), "us_it_add_effect_p90": np.percentile(d, 90),
                    "ms_revision": MS["rev"].get(y, np.nan) - MS["prev"].get(y, np.nan)})
    pdf = pd.DataFrame(pol).round(2)
    pdf.to_csv(HERE / "out/political_effect_vs_ms.csv", index=False)
    show = df[df.year.between(2026, 2032)][["case", "year", "it_add_p50", "us_it_add_p10", "us_it_add_p50",
                                             "us_it_add_p90", "load_cum_p50"]]
    print(show.to_string(index=False))
    print(pdf.to_string(index=False))
    print("MS US IT additions revised:", MS["rev"], "previous:", MS["prev"])
    # severity scenarios (data/severity.csv): US IT additions and the 2027 slip share
    sev = pd.read_csv(HERE / "data/severity.csv").iloc[0]
    tr_raw, co_raw = model.load(raw=True)
    sc = []
    for name, kn, kf in (("optimistic", sev.k_near_low, sev.k_far_low), ("near_only", sev.k_near, 1.0),
                         ("central", sev.k_near, sev.k_far), ("same_bias", sev.k_near, sev.k_far_low),
                         ("pessimistic", sev.k_near_high, sev.k_far_high), ("uncalibrated", 1.0, 1.0)):
        c = co_raw.copy()
        near = c.stage.isin(["S1", "S2"])
        for col in ("delay_low", "delay_high"):
            c.loc[near, col] *= kn
            c.loc[~near, col] *= kf
        model.simulate(tr_raw, c, 6000, 0.5, 0.5, seed=11)
        L = dict(model.LAST)
        it, _, sh = convert(L["delay"], L["states"], L["n"])
        num = den = 0.0
        for _, _, yb, yd, gw in L["tranches"]:
            m = yb == 2027
            den += gw[m].sum(); num += gw[m & (yd > 2027)].sum()
        row = {"scenario": name, "k_near": kn, "k_far": kf, "slip2027": num / den}
        for y in (2027, 2028, 2029, 2030):
            row[f"us_it_add_{y}_p50"] = np.median((it[y] - it[y - 1]) / sh)
        sc.append(row)
    scd = pd.DataFrame(sc).round(2)
    scd.to_csv(HERE / "out/severity_scenarios.csv", index=False)
    print(scd.to_string(index=False))


if __name__ == "__main__":
    main()
