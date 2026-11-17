"""Figure 2: modelled US IT-capacity additions vs Morgan Stanley (Nov 2026)."""
from pathlib import Path

import pandas as pd

import sjfig

HERE = Path(__file__).resolve().parent
d = pd.read_csv(HERE / "out/conversion.csv")
d = d[d.year.between(2026, 2032)]

fig, ax = sjfig.figure("note", width="single", aspect=0.78)
for case, color, ls, mk, lab in (("baseline_schedule", sjfig.PALETTE["baseline"], "-", "o", "계약·유틸리티 일정"),
                                 ("no_social", sjfig.PALETTE["contrast"], "--", "s", "정치·지역·세제·용수 제거"),
                                 ("all", sjfig.PALETTE["key"], "-", "o", "모든 제약 (P10–P90)")):
    x = d[d.case == case]
    if case == "all":
        ax.fill_between(x.year, x.us_it_add_p10, x.us_it_add_p90, color=color, alpha=0.18, lw=0)
    ax.plot(x.year, x.us_it_add_p50, color=color, ls=ls, marker=mk,
            mfc="white" if case == "no_social" else color, label=lab)
ax.scatter([2028, 2029], [24.9, 22.7], marker="D", s=22, facecolor="white", edgecolor=sjfig.PALETTE["ink"],
           zorder=5, label="모건스탠리 수정 전")
ax.scatter([2028, 2029], [19.9, 27.6], marker="D", s=22, color=sjfig.PALETTE["ink"], zorder=5,
           label="모건스탠리 11월 수정")
ax.set_xlabel("연도")
ax.set_ylabel("미국 연간 신규 IT 용량 (GW)")
ax.set_ylim(0, None)
ax.set_xticks(range(2026, 2033))
ax.legend(loc="lower right", fontsize=7.5, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92)
sjfig.audit(fig)
sjfig.save(fig, "fig2_us_it_vs_ms", "note", outdir=str(HERE / "figures"), source="tools/dcpipeline/out/conversion.csv")
