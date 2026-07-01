# Data Dictionary — key fields & the leakage blacklist

Source: Lending Club accepted loans 2007–2018Q4 (Kaggle `wordsforthewise/lending-club`), ~2.26M rows, 151 columns. We stage ~30.

## Target

| Field | Definition |
|---|---|
| `is_default` | 1 if `loan_status` contains "Charged Off", else 0. Computed on **completed loans only** (Fully Paid / Charged Off). Open loans are right-censored and excluded — calling a loan that's 6 months old "good" would understate PD. |

## Origination-time features (safe to model on)

| Field | Notes |
|---|---|
| `loan_amnt`, `term_months`, `int_rate`, `installment` | Loan contract terms. `int_rate` embeds the underwriter's own risk view — powerful, and fair game (it's known at origination). |
| `grade`, `sub_grade` | LC's internal risk grade A–G. |
| `fico` | Midpoint of `fico_range_low/high` at origination. |
| `annual_inc`, `dti`, `emp_length_yrs`, `home_ownership`, `verification_status` | Borrower affordability profile. `annual_inc` is self-reported — see `verification_status`. |
| `revol_util`, `revol_bal`, `open_acc`, `total_acc`, `mort_acc` | Credit-bureau utilization snapshot. |
| `delinq_2yrs`, `pub_rec`, `inq_last_6mths` | Derogatory history. `inq_last_6mths` = recent credit-seeking behavior. |
| `loan_to_income`, `payment_to_income`, `rate_rank_in_grade`, `dti_vs_cohort` | Engineered in `02_features.sql`. |

## ☠️ Leakage blacklist — post-origination outcome data

These columns describe what happened **after** the loan was made. A model trained on them scores near-perfect and is worthless. They are dropped in staging, except two kept **only** for loss/LGD analysis and vintage timing:

| Column | Why it leaks |
|---|---|
| `total_pymnt`, `total_rec_prncp`, `total_rec_int` | Cash actually received — literally the outcome. Kept as `actual_total_pymnt` for LGD math only. |
| `recoveries`, `collection_recovery_fee` | Only nonzero for charged-off loans. Kept as `actual_recoveries` for LGD only. |
| `out_prncp`, `out_prncp_inv` | Remaining principal — zero iff loan completed. |
| `last_pymnt_d`, `last_pymnt_amnt`, `next_pymnt_d` | Payment behavior. `last_pymnt_d` used only to estimate default timing for vintage curves. |
| `last_fico_range_high/low` | FICO **after** origination — a defaulting borrower's score collapses. The single most tempting leak in this dataset. |
| `debt_settlement_flag`, `settlement_*`, `hardship_*` | Only exist because the loan went bad. |

Interview line worth internalizing: *"I validated the feature set by asking, for every column: could the bank have known this at the moment of approval?"*
