"""Translate US IT-capacity additions into HBM and CPU-attached LPDDR demand (EB/yr).

HBM_y = IT_add_y (GW) x 1000 x rack_share x HBM_per_MW(y)  [TB]  / 1e6 -> EB
HBM_per_MW(y) = sum_g mix(y,g) x HBM_per_MW(g) for NVIDIA rack generations,
                then the custom-ASIC share is applied with a relative HBM intensity.
The 'nvidia_only' line sets the ASIC intensity equal to NVIDIA's (ratio 1).
Memory is assigned to the year IT capacity is built out (fill increment), not contract energization.
"""
from pathlib import Path

import numpy as np
import pandas as pd

import convert
import model

HERE = Path(__file__).resolve().parent
P = pd.read_csv(HERE / "data/memory_params.csv").set_index("key")
MIX = pd.read_csv(HERE / "data/gen_mix.csv").set_index("year")
GENS = ["GB200", "GB300", "VR", "KY"]
YEARS = range(2027, 2032)


def u(rng, key, n):
    r = P.loc[key]
    return rng.uniform(r.low, r.high, n)


def intensities(n, seed=5):
    rng = np.random.default_rng(seed)
    hb = {g: u(rng, f"{g}_hbm_tb_per_mw", n) for g in GENS}
    lp = {g: u(rng, f"{g}_lpddr_tb_per_mw", n) for g in GENS}
    rack = u(rng, "rack_share_of_it", n)
    a = u(rng, "asic_share", n)
    r = u(rng, "asic_hbm_ratio", n)
    return hb, lp, rack, a, r


def memory_paths(it_add, n, asic=True):
    """it_add: {year: array GW}. Returns {year: (hbm_EB, lpddr_EB)} arrays."""
    hb, lp, rack, a, r = intensities(n)
    out = {}
    for y in YEARS:
        mix = MIX.loc[min(y, MIX.index.max())]
        h = sum(mix[g] * hb[g] for g in GENS)
        l = sum(mix[g] * lp[g] for g in GENS)
        if asic:
            h = (1 - a) * h + a * h * r
            l = (1 - a) * l          # ASIC hosts: CPU memory not modelled
        mw = it_add[y] * 1000 * rack
        out[y] = (mw * h / 1e6, mw * l / 1e6)
    return out


def it_adds(case):
    tr, co = model.load()
    if case == "no_social":
        co.loc[co.constraint.isin(["politics", "local", "tax", "water"]), "p_active"] = 0.0
    model.simulate(tr, co, 8000, 0.5, 0.5, seed=11)
    L = dict(model.LAST)
    key = "base" if case == "baseline_schedule" else "delay"
    it, _, sh = convert.convert(L[key], L["states"], L["n"])
    return {y: (it[y] - it[y - 1]) / sh for y in YEARS}, L["n"]


def main():
    rows = []
    for case in ("baseline_schedule", "all", "no_social"):
        add, n = it_adds(case)
        for asic in (False, True):
            mem = memory_paths(add, n, asic)
            for y in YEARS:
                h, l = mem[y]
                rows.append({"case": case, "asic_adjusted": asic, "year": y,
                             "us_it_add_gw_p50": np.median(add[y]),
                             "hbm_eb_p10": np.percentile(h, 10), "hbm_eb_p50": np.median(h),
                             "hbm_eb_p90": np.percentile(h, 90),
                             "lpddr_eb_p50": np.median(l)})
    # Morgan Stanley path (2028, 2029 only), same intensities
    n = 8000
    for label, path in (("ms_revised", convert.MS["rev"]), ("ms_previous", convert.MS["prev"])):
        add = {y: np.full(n, path.get(y, np.nan)) for y in YEARS}
        for asic in (False, True):
            mem = memory_paths(add, n, asic)
            for y in (2028, 2029):
                h, l = mem[y]
                rows.append({"case": label, "asic_adjusted": asic, "year": y, "us_it_add_gw_p50": path[y],
                             "hbm_eb_p10": np.percentile(h, 10), "hbm_eb_p50": np.median(h),
                             "hbm_eb_p90": np.percentile(h, 90), "lpddr_eb_p50": np.median(l)})
    df = pd.DataFrame(rows).round(2)
    df.to_csv(HERE / "out/memory.csv", index=False)
    print(df[~df.asic_adjusted].to_string(index=False))
    print(df[df.asic_adjusted & df.year.isin([2028, 2029])].to_string(index=False))


if __name__ == "__main__":
    main()
