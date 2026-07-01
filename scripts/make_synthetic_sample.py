"""Generate a small synthetic Lending-Club-shaped CSV for pipeline smoke tests.

Writes data/raw/accepted_2007_to_2018Q4.csv.gz with ~20k plausible rows so
the SQL + modeling pipeline can be verified end-to-end before the real
Kaggle download. The real download simply overwrites this file.

Usage:  python scripts/make_synthetic_sample.py
"""
import gzip
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
N = 20_000
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "accepted_2007_to_2018Q4.csv.gz"

grades = np.array(list("ABCDEFG"))
g_idx = rng.choice(7, N, p=[0.17, 0.28, 0.27, 0.15, 0.08, 0.035, 0.015])
grade = grades[g_idx]
sub = np.char.add(grade, rng.integers(1, 6, N).astype(str))

fico = np.clip(rng.normal(700 - g_idx * 12, 25), 620, 850).round()
int_rate = np.clip(rng.normal(7 + g_idx * 3.2, 1.5), 5, 31).round(2)
loan_amnt = rng.choice(np.arange(1000, 40001, 25), N)
term = rng.choice([" 36 months", " 60 months"], N, p=[0.7, 0.3])
annual_inc = np.clip(rng.lognormal(11.1, 0.55, N), 8000, 8_000_000).round()
dti = np.clip(rng.normal(18 + g_idx * 1.5, 8), 0, 55).round(2)
issue = rng.choice(pd.date_range("2012-01-01", "2018-10-01", freq="MS"), N)

# default probability rises with grade index and dti; gives realistic ~20% rate
logit = -2.4 + g_idx * 0.45 + (dti - 18) * 0.03 + (700 - fico) * 0.004
p_def = 1 / (1 + np.exp(-logit))
is_def = rng.random(N) < p_def

mob = rng.integers(3, 40, N)  # months to last payment
last_pymnt = pd.Series(issue) + pd.to_timedelta(mob * 30, "D")

df = pd.DataFrame({
    "id": np.arange(1, N + 1),
    "loan_status": np.where(is_def, "Charged Off", "Fully Paid"),
    "loan_amnt": loan_amnt,
    "term": term,
    "int_rate": int_rate,
    "installment": (loan_amnt * (int_rate / 1200) * 1.5).round(2),
    "grade": grade,
    "sub_grade": sub,
    "emp_length": rng.choice(["< 1 year", "2 years", "5 years", "10+ years", ""], N),
    "home_ownership": rng.choice(["RENT", "MORTGAGE", "OWN"], N, p=[0.4, 0.48, 0.12]),
    "annual_inc": annual_inc,
    "verification_status": rng.choice(["Verified", "Source Verified", "Not Verified"], N),
    "purpose": rng.choice(["debt_consolidation", "credit_card", "home_improvement",
                           "small_business", "medical", "car"], N,
                          p=[0.55, 0.22, 0.08, 0.05, 0.05, 0.05]),
    "dti": dti,
    "fico_range_low": fico - 2,
    "fico_range_high": fico + 2,
    "open_acc": rng.integers(1, 30, N),
    "pub_rec": rng.choice([0, 0, 0, 1], N),
    "revol_bal": rng.integers(0, 80_000, N),
    "revol_util": np.clip(rng.normal(50, 25, N), 0, 130).round(1),
    "total_acc": rng.integers(3, 60, N),
    "mort_acc": rng.integers(0, 6, N),
    "delinq_2yrs": rng.choice([0, 0, 0, 0, 1, 2], N),
    "inq_last_6mths": rng.choice([0, 0, 1, 1, 2, 3], N),
    "addr_state": rng.choice(["CA", "TX", "NY", "FL", "IL"], N),
    "application_type": "Individual",
    "issue_d": pd.Series(issue).dt.strftime("%b-%Y"),
    "last_pymnt_d": last_pymnt.dt.strftime("%b-%Y"),
    "total_pymnt": np.where(is_def, loan_amnt * rng.uniform(0.1, 0.7, N),
                            loan_amnt * rng.uniform(1.05, 1.35, N)).round(2),
    "recoveries": np.where(is_def, loan_amnt * rng.uniform(0, 0.1, N), 0).round(2),
})

OUT.parent.mkdir(parents=True, exist_ok=True)
with gzip.open(OUT, "wt", newline="") as f:
    df.to_csv(f, index=False)
print(f"Wrote {len(df):,} synthetic rows -> {OUT}")
print(f"Synthetic default rate: {is_def.mean():.1%}")
