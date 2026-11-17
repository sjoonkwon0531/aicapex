"""Figure: (a) median added delay by state x stage with the binding constraint,
(b) 9-state annual additions: contract schedule vs modelled, with counterfactuals."""
from pathlib import Path

import numpy as np
import pandas as pd

import sjfig

HERE = Path(__file__).resolve().parent
st = pd.read_csv(HERE / "out/delay_by_state_stage.csv")
ag = pd.read_csv(HERE / "out/online_9states.csv")
cf = pd.read_csv(HERE / "out/counterfactuals.csv").set_index("case")

KO = {"generation": "발전", "interconnect": "접속", "equipment": "장비", "politics": "주정부",
      "local": "지역", "tax": "세제", "water": "용수", "none": "–"}
STATES = ["TX", "VA", "GA", "OH", "PA", "IN", "UT", "AZ", "WI"]
STAGES = ["S1", "S2", "S3", "S4"]
STAGE_LAB = ["S1\n통전 대기", "S2\n공사 중", "S3\n계약·인허가", "S4\n계획"]

fig, (ax1, ax2) = sjfig.figure("note", width="double", aspect=0.46, ncols=2,
                               gridspec_kw={"width_ratios": [1, 1.25]})

# a: heatmap of median total added delay (months)
M = np.full((len(STATES), len(STAGES)), np.nan)
B = [["" for _ in STAGES] for _ in STATES]
for r in st.itertuples():
    i, j = STATES.index(r.state), STAGES.index(r.stage)
    M[i, j] = r.total_delay_p50
    B[i][j] = KO[r.binding_top] if r.total_delay_p50 >= 1 else "–"
im = ax1.imshow(np.ma.masked_invalid(M), cmap="cividis", vmin=0, vmax=60, aspect="auto")
ax1.set_facecolor(sjfig.PALETTE["light"])
for i in range(len(STATES)):
    for j in range(len(STAGES)):
        if np.isnan(M[i, j]):
            ax1.text(j, i, "자료 없음", ha="center", va="center", fontsize=7.5, color=sjfig.PALETTE["ink"])
            continue
        c = "white" if M[i, j] < 35 else sjfig.PALETTE["ink"]
        ax1.text(j, i, f"{M[i, j]:.0f}  {B[i][j]}", ha="center", va="center", fontsize=8.5, color=c)
ax1.set_xticks(range(len(STAGES)), STAGE_LAB)
ax1.set_yticks(range(len(STATES)), STATES)
ax1.tick_params(length=0)
for s in ax1.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax1, fraction=0.05, pad=0.02)
cb.set_label("추가 지연 중앙값 (개월)")
cb.outline.set_visible(False)

# b: annual additions
yrs = ag.year.to_numpy()
m = (yrs >= 2026) & (yrs <= 2033)
y = yrs[m]
ax2.plot(y, ag.add_base_p50[m], color=sjfig.PALETTE["baseline"], marker="o", label="계약·유틸리티 일정")
ax2.fill_between(y, ag.add_delay_p10[m], ag.add_delay_p90[m], color=sjfig.PALETTE["key"], alpha=0.18, lw=0)
ax2.plot(y, ag.add_delay_p50[m], color=sjfig.PALETTE["key"], marker="o", label="모든 제약 (P10–P90)")
yy = [2027, 2028, 2029, 2030, 2031]
ax2.plot(yy, [cf.loc["no_social", f"add{v}"] for v in yy], color=sjfig.PALETTE["contrast"], ls="--",
         marker="s", mfc="white", label="정치·지역·세제·용수 제거")
ax2.plot(yy, [cf.loc["no_power", f"add{v}"] for v in yy], color=sjfig.PALETTE["green"], ls=":",
         marker="^", mfc="white", label="발전·접속 제거")
ax2.set_xlabel("연도")
ax2.set_ylabel("9개 주 연간 신규 가동 (GW, 계약·부하 기준)")
ax2.set_ylim(0, None)
ax2.set_xticks(y)
ax2.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="none", framealpha=0.92)

sjfig.label_panels(fig, [ax1, ax2])
sjfig.audit(fig)
sjfig.save(fig, "fig1_delay_by_stage", "note", outdir=str(HERE / "figures"),
           source="tools/dcpipeline/out/*.csv")
