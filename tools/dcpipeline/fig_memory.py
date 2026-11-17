"""Figure 3: US HBM installed in new AI data-center capacity (EB/yr), NVIDIA-intensity basis."""
from pathlib import Path

import pandas as pd

import sjfig

HERE = Path(__file__).resolve().parent
d = pd.read_csv(HERE / "out/memory.csv")
d = d[~d.asic_adjusted]

fig, ax = sjfig.figure("note", width="single", aspect=1.0)
for case, color, ls, mk, lab in (("baseline_schedule", sjfig.PALETTE["baseline"], "-", "o", "계약·유틸리티 일정"),
                                 ("no_social", sjfig.PALETTE["contrast"], "--", "s", "정치·지역·세제·용수 제거"),
                                 ("all", sjfig.PALETTE["key"], "-", "o", "모든 제약 (P10–P90)")):
    x = d[d.case == case]
    if case == "all":
        ax.fill_between(x.year, x.hbm_eb_p10, x.hbm_eb_p90, color=color, alpha=0.18, lw=0)
    ax.plot(x.year, x.hbm_eb_p50, color=color, ls=ls, marker=mk,
            mfc="white" if case == "no_social" else color, label=lab)
for case, fc, lab in (("ms_previous", "white", "모건스탠리 수정 전 경로"), ("ms_revised", sjfig.PALETTE["ink"], "모건스탠리 11월 수정 경로")):
    x = d[d.case == case]
    ax.scatter(x.year, x.hbm_eb_p50, marker="D", s=22, facecolor=fc, edgecolor=sjfig.PALETTE["ink"], zorder=5, label=lab)
ax.set_xlabel("연도")
ax.set_ylabel("미국 신규 설치 HBM (EB/년)")
ax.set_ylim(0, None)
ax.set_xticks(range(2027, 2032))
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=7.5)
sjfig.audit(fig)
sjfig.save(fig, "fig3_us_hbm", "note", outdir=str(HERE / "figures"), source="tools/dcpipeline/out/memory.csv")
