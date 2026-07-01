"""Turn model scores into the numbers a risk committee cares about.

Produces the approval-rate vs default-rate tradeoff curve and an
expected-credit-loss table per PD cutoff, in ₹ per ₹100 Cr disbursed.

Usage:  python src/business_metrics.py   (after train_model.py)
Outputs: reports/cutoff_table.csv, reports/tradeoff_curve.png
"""
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
# loss_per_100cr is loss ÷ disbursed × 100 — a ratio, so it reads the same
# in ₹ Cr per ₹100 Cr disbursed regardless of the source currency (USD)


def main() -> None:
    scores = pd.read_parquet(REPORTS / "test_scores.parquet")

    # grade-level LGD from realized losses (built in 03_risk_metrics.sql)
    con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    lgd = con.execute("SELECT grade, lgd FROM risk.grade_loss").fetchdf()
    con.close()
    scores = scores.merge(lgd, on="grade", how="left")
    scores["lgd"] = scores["lgd"].fillna(scores["lgd"].mean())

    base_default = scores["is_default"].mean()
    base_disbursed = scores["loan_amnt"].sum()

    rows = []
    for cutoff in np.arange(0.05, 0.61, 0.01):
        approved = scores[scores["pd_hat"] < cutoff]
        if len(approved) == 0:
            continue
        # realized outcomes of the loans we WOULD have approved
        el = (approved.loc[approved["is_default"] == 1, "loan_amnt"]
              * approved.loc[approved["is_default"] == 1, "lgd"]).sum()
        rows.append({
            "pd_cutoff": round(cutoff, 2),
            "approval_rate": len(approved) / len(scores),
            "default_rate": approved["is_default"].mean(),
            "disbursed_share": approved["loan_amnt"].sum() / base_disbursed,
            # realized loss per ₹100 Cr disbursed at this cutoff
            "loss_per_100cr_inr": el / approved["loan_amnt"].sum() * 100,
        })
    table = pd.DataFrame(rows)
    table.to_csv(REPORTS / "cutoff_table.csv", index=False)

    # ---- tradeoff chart ----
    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    ax1.plot(table["pd_cutoff"], table["approval_rate"] * 100, label="Approval rate %")
    ax1.set_xlabel("PD cutoff (decline if PD ≥ x)")
    ax1.set_ylabel("Approval rate %")
    ax2 = ax1.twinx()
    ax2.plot(table["pd_cutoff"], table["default_rate"] * 100, color="crimson",
             label="Default rate of approved book %")
    ax2.set_ylabel("Default rate %", color="crimson")
    fig.suptitle("Approval vs risk: choosing the PD cutoff")
    fig.tight_layout()
    fig.savefig(REPORTS / "tradeoff_curve.png", dpi=150)

    # ---- headline numbers for the memo ----
    print(f"Unfiltered test book: default rate {base_default:.2%}")
    print(table.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    print("\nPick the cutoff where marginal loss saved stops paying for "
          "marginal approvals lost — and defend it in docs/risk_memo.md.")


if __name__ == "__main__":
    main()
