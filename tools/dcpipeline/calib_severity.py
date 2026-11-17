"""Calibrate constraint severity to observed slip rates (Currence, formerly Sightline Climate).

Metric: slip share for year Y = GW whose baseline (contract) year is Y but whose modelled
online year is later than Y, divided by GW with baseline year Y. Same definition as
Currence's "share of capacity slated for a year that missed it".

Targets (data/evidence.csv, US rows): 2025 actual 26% of projects missed + ~10% quietly pushed;
2026 at risk 30-50%. We target 2027 slip = 0.38 (band 0.30-0.45).

Only S1-S2 delays are scaled by k_near: near-term slips are what Currence observes.
S3-S4 have no observational target; k_far is reported as a sensitivity.
"""
from pathlib import Path

import numpy as np
import pandas as pd

import model

HERE = Path(__file__).resolve().parent
TARGET, BAND = 0.38, (0.30, 0.45)


def scaled(co, k_near, k_far):
    c = co.copy().astype({"delay_low": float, "delay_high": float})
    near = c.stage.isin(["S1", "S2"])
    for col in ("delay_low", "delay_high"):
        c.loc[near, col] = c.loc[near, col] * k_near
        c.loc[~near, col] = c.loc[~near, col] * k_far
    return c


def slip_share(year):
    num = den = 0.0
    for _, _, yb, yd, gw in model.LAST["tranches"]:
        m = yb == year
        den += np.sum(gw[m])
        num += np.sum(gw[m & (yd > year)])
    return num / den


def main():
    tr, co = model.load(raw=True)
    rows = []
    for k in np.round(np.arange(0.2, 1.21, 0.1), 2):
        model.simulate(tr, scaled(co, k, 1.0), 6000, 0.5, 0.5, seed=11)
        rows.append({"k_near": k, "slip2027": slip_share(2027), "slip2028": slip_share(2028)})
    g = pd.DataFrame(rows).round(3)
    g.to_csv(HERE / "out/severity_grid.csv", index=False)
    print(g.to_string(index=False))
    k_star = float(np.interp(TARGET, g.slip2027, g.k_near))
    k_lo = float(np.interp(BAND[0], g.slip2027, g.k_near))
    k_hi = float(np.interp(BAND[1], g.slip2027, g.k_near))
    print(f"k_near* = {k_star:.2f} (band {k_lo:.2f}-{k_hi:.2f})")
    # k_far: no observational target. Central 0.8 (between 'same bias as near-term' 0.6
    # and 'far-term judgment unbiased' 1.0); scenarios at both ends are reported by convert.py.
    pd.DataFrame([{"k_near": round(k_star, 2), "k_near_low": round(k_lo, 2), "k_near_high": round(k_hi, 2),
                   "k_far": 0.8, "k_far_low": 0.6, "k_far_high": 1.0,
                   "target_slip2027": TARGET}]).to_csv(HERE / "data/severity.csv", index=False)


if __name__ == "__main__":
    main()
