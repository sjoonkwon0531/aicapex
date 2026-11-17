"""Check modelled state load (contract MW -> demand via convert.py) against the utilities'
own data-center forecasts filed with PJM (Sept 2026).

The utility forecasts are not ground truth. They are the utilities' expectations, built
from customer contract schedules with their own utilization discounts. The ratio
model / utility shows how much more friction the model assumes than the utility does.
"""
from pathlib import Path

import numpy as np
import pandas as pd

import convert
import model

HERE = Path(__file__).resolve().parent
T = pd.read_csv(HERE / "data/utility_forecasts.csv")


def main():
    tr, co = model.load()
    model.simulate(tr, co, 8000, 0.5, 0.5, seed=11)
    L = dict(model.LAST)
    rows = []
    for t in T.itertuples():
        # one state at a time; forecast increments are measured from the base year
        it, ld, _ = convert.convert(L["delay"], [t.state], L["n"])
        itb, ldb, _ = convert.convert(L["base"], [t.state], L["n"])
        a, b = t.from_year, t.to_year
        if t.basis == "load":
            m, mb = ld[b] - ld[a], ldb[b] - ldb[a]
        else:  # contract MW energized
            m = L["delay"][(t.state, b)] - L["delay"][(t.state, a)]
            mb = L["base"][(t.state, b)] - L["base"][(t.state, a)]
        rows.append({"state": t.state, "utility": t.utility, "basis": t.basis, "period": f"{a}-{b}",
                     "utility_increment_gw": t.increment_gw,
                     "model_p10": np.percentile(m, 10), "model_p50": np.median(m), "model_p90": np.percentile(m, 90),
                     "model_contract_schedule_p50": np.median(mb),
                     "ratio_model_to_utility": np.median(m) / t.increment_gw if t.increment_gw else np.nan})
    df = pd.DataFrame(rows).round(2)
    df.to_csv(HERE / "out/calibration.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
