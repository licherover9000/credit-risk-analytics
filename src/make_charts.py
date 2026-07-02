"""Generate the publication charts embedded in the README.

Usage:  python src/make_charts.py   (after run_pipeline.py + business_metrics.py)
Outputs: docs/img/*.png (committed — these render on GitHub)
"""
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)

# ---- 1. Vintage curves: one line per issue-year (averaged over quarters) ----
vc = con.execute("""
    SELECT EXTRACT(year FROM vintage_quarter)::INT AS yr, mob,
           AVG(cum_default_rate) AS cum_dr
    FROM risk.vintage_curves
    WHERE yr BETWEEN 2009 AND 2016 AND mob <= 48
    GROUP BY yr, mob ORDER BY yr, mob
""").fetchdf()
fig, ax = plt.subplots(figsize=(9, 5.5))
cmap = plt.get_cmap("viridis")
years = sorted(vc["yr"].unique())
for i, yr in enumerate(years):
    d = vc[vc["yr"] == yr]
    ax.plot(d["mob"], d["cum_dr"] * 100, label=str(yr),
            color=cmap(i / max(1, len(years) - 1)))
ax.set_xlabel("Months on book")
ax.set_ylabel("Cumulative default rate %")
ax.set_title("Vintage curves: 2012-2016 vintages deteriorate as origination scales")
ax.legend(title="Issue year", ncol=2, fontsize=9)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(IMG / "vintage_curves.png", dpi=150)

# ---- 2. PD vs LGD by grade ----
gl = con.execute("SELECT * FROM risk.grade_loss ORDER BY grade").fetchdf()
fig, ax = plt.subplots(figsize=(8, 5))
x = range(len(gl))
ax.bar([i - 0.2 for i in x], gl["pd_observed"] * 100, 0.4, label="PD (default rate) %")
ax.bar([i + 0.2 for i in x], gl["lgd"] * 100, 0.4, label="LGD (loss severity) %")
ax.set_xticks(list(x), gl["grade"])
ax.set_xlabel("Grade")
ax.set_ylabel("%")
ax.set_title("PD climbs monotonically A->G; LGD stays flat (~37-40%)")
ax.legend()
ax.grid(alpha=0.3, axis="y")
fig.tight_layout()
fig.savefig(IMG / "pd_lgd_by_grade.png", dpi=150)

# ---- 3. Segment heatmap: grade x income decile ----
seg = con.execute("""
    SELECT grade, income_decile, SUM(defaulted_amount) / SUM(disbursed) AS bad_share,
           SUM(n_loans * default_rate) / SUM(n_loans) AS default_rate
    FROM features.segment_risk GROUP BY grade, income_decile
""").fetchdf()
pivot = seg.pivot(index="grade", columns="income_decile", values="default_rate")
fig, ax = plt.subplots(figsize=(9, 5))
im = ax.imshow(pivot * 100, cmap="Reds", aspect="auto")
ax.set_xticks(range(pivot.shape[1]), pivot.columns)
ax.set_yticks(range(pivot.shape[0]), pivot.index)
ax.set_xlabel("Income decile (1 = lowest)")
ax.set_ylabel("Grade")
ax.set_title("Default rate % by grade x income decile")
for i in range(pivot.shape[0]):
    for j in range(pivot.shape[1]):
        v = pivot.iloc[i, j]
        if pd.notna(v):
            ax.text(j, i, f"{v*100:.0f}", ha="center", va="center",
                    color="white" if v > 0.3 else "black", fontsize=8)
fig.colorbar(im, label="Default rate %")
fig.tight_layout()
fig.savefig(IMG / "segment_heatmap.png", dpi=150)

con.close()

# ---- 4. Cutoff tradeoff (from business_metrics output) ----
ct = pd.read_csv(ROOT / "reports" / "cutoff_table.csv")
fig, ax1 = plt.subplots(figsize=(9, 5.5))
ax1.plot(ct["pd_cutoff"], ct["approval_rate"] * 100, lw=2, label="Approval rate %")
ax1.set_xlabel("PD cutoff (decline if modeled PD >= x)")
ax1.set_ylabel("Approval rate %")
ax1.axvline(0.25, color="gray", ls="--", alpha=0.7)
ax1.annotate("recommended cutoff: 25%\n71% approval, 15.1% default",
             xy=(0.25, 71), xytext=(0.3, 45),
             arrowprops=dict(arrowstyle="->", color="gray"))
ax2 = ax1.twinx()
ax2.plot(ct["pd_cutoff"], ct["default_rate"] * 100, color="crimson", lw=2,
         label="Default rate of approved book %")
ax2.set_ylabel("Default rate of approved book %", color="crimson")
ax1.set_title("The cutoff decision: approval volume vs credit risk")
ax1.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(IMG / "cutoff_tradeoff.png", dpi=150)

print(f"Charts written to {IMG}")
