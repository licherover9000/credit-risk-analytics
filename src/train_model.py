"""Decision ladder: policy rules + calibrated PD model.

Layer 1 — hard policy rules (explainable auto-declines).
Layer 2 — gradient-boosted PD model on rule-passing loans,
          benchmarked against a logistic baseline, probability-calibrated.

Split is OUT-OF-TIME (train on older vintages, test on the newest 20%),
because a random split lets the model peek at future macro conditions —
the classic credit-modeling mistake.

Usage:  python src/train_model.py
Outputs: reports/model_metrics.txt, reports/test_scores.parquet
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "warehouse.duckdb"
REPORTS = ROOT / "reports"

NUMERIC = [
    "loan_amnt", "term_months", "int_rate", "installment", "emp_length_yrs",
    "annual_inc", "dti", "fico", "open_acc", "pub_rec", "revol_bal",
    "revol_util", "total_acc", "mort_acc", "delinq_2yrs", "inq_last_6mths",
    "loan_to_income", "payment_to_income", "rate_rank_in_grade",
    "dti_rank_in_grade", "dti_vs_cohort", "rate_vs_subgrade",
]
CATEGORICAL = ["grade", "purpose", "home_ownership", "verification_status",
               "application_type"]
TARGET = "is_default"


def apply_policy_rules(df: pd.DataFrame) -> pd.Series:
    """Layer 1: hard declines. Returns True where the rule fires."""
    return (
        (df["dti"] > 60)
        | (df["fico"] < 640)
        | (df["revol_util"] > 120)
        | ((df["annual_inc"] < 200_000 / 83) & (df["loan_amnt"] / df["annual_inc"] > 0.8))
    )


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    df = con.execute(
        f"SELECT {', '.join(NUMERIC + CATEGORICAL + [TARGET, 'issue_date'])} "
        "FROM features.loan_features"
    ).fetchdf()
    con.close()
    print(f"Loaded {len(df):,} completed loans; default rate {df[TARGET].mean():.2%}")

    # ---- Layer 1: policy rules ----
    rule_declined = apply_policy_rules(df)
    print(f"Policy rules decline {rule_declined.mean():.1%} of applications "
          f"(default rate inside declines: {df.loc[rule_declined, TARGET].mean():.2%})")
    df = df[~rule_declined].copy()

    # ---- Out-of-time split ----
    cutoff = df["issue_date"].quantile(0.8)
    train, test = df[df["issue_date"] <= cutoff], df[df["issue_date"] > cutoff]
    print(f"Train ≤ {cutoff.date()} ({len(train):,}) | Test > ({len(test):,})")

    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                          ("sc", StandardScaler())]), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])

    models = {
        "logistic_baseline": Pipeline([
            ("pre", pre),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]),
        "gradient_boosting": Pipeline([
            ("pre", pre),
            ("clf", CalibratedClassifierCV(
                HistGradientBoostingClassifier(
                    max_iter=400, learning_rate=0.08, max_depth=6,
                    early_stopping=True, random_state=42),
                method="isotonic", cv=3)),
        ]),
    }

    lines, best_name, best_auc, best_scores = [], None, 0.0, None
    X_tr, y_tr = train[NUMERIC + CATEGORICAL], train[TARGET]
    X_te, y_te = test[NUMERIC + CATEGORICAL], test[TARGET]

    for name, model in models.items():
        model.fit(X_tr, y_tr)
        pd_hat = model.predict_proba(X_te)[:, 1]
        auc = roc_auc_score(y_te, pd_hat)
        brier = brier_score_loss(y_te, pd_hat)
        gini = 2 * auc - 1
        lines.append(f"{name:20s}  AUC {auc:.4f}  Gini {gini:.4f}  Brier {brier:.4f}")
        print(lines[-1])
        if auc > best_auc:
            best_name, best_auc, best_scores = name, auc, pd_hat

    # persist test-set scores for business_metrics.py
    out = test[["loan_amnt", "int_rate", "grade", "purpose", TARGET]].copy()
    out["pd_hat"] = best_scores
    out.to_parquet(REPORTS / "test_scores.parquet")
    (REPORTS / "model_metrics.txt").write_text(
        "\n".join(lines) + f"\n\nchampion: {best_name}\n", encoding="utf-8")
    print(f"\nChampion: {best_name}. Scores → reports/test_scores.parquet")


if __name__ == "__main__":
    main()
