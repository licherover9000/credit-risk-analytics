-- ============================================================
-- 01_staging.sql — raw ingest, typing, target definition, leakage drop
-- Engine: DuckDB (Postgres-compatible dialect; date parsing uses
-- strptime — in Postgres this becomes to_date(issue_d, 'Mon-YYYY')).
-- ============================================================

CREATE SCHEMA IF NOT EXISTS staging;

-- ---------- raw landing (all VARCHAR, exactly as received) ----------
CREATE OR REPLACE TABLE staging.loans_raw AS
SELECT *
FROM read_csv_auto('data/raw/accepted_2007_to_2018Q4.csv.gz',
                   all_varchar = true,      -- land as text, type explicitly below
                   sample_size  = -1);

-- ---------- typed, cleaned, completed loans only ----------
-- Target definition: a loan is a "default" if it charged off.
-- We keep ONLY completed loans (Fully Paid / Charged Off).
-- Open loans (Current, Late, Grace) are right-censored: we don't yet
-- know their outcome, and calling them "good" would understate PD.
CREATE OR REPLACE TABLE staging.loans AS
SELECT
    id                                                        AS loan_id,
    -- ---- target ----
    CASE WHEN loan_status LIKE '%Charged Off%' THEN 1 ELSE 0 END AS is_default,

    -- ---- loan terms (known at origination) ----
    TRY_CAST(loan_amnt AS DOUBLE)                             AS loan_amnt,
    TRY_CAST(REGEXP_EXTRACT(term, '\d+') AS INTEGER)          AS term_months,
    TRY_CAST(REPLACE(int_rate, '%', '') AS DOUBLE)            AS int_rate,
    TRY_CAST(installment AS DOUBLE)                           AS installment,
    grade,
    sub_grade,
    purpose,

    -- ---- borrower profile (known at origination) ----
    CASE
        WHEN emp_length = '10+ years' THEN 10
        WHEN emp_length = '< 1 year'  THEN 0
        ELSE TRY_CAST(REGEXP_EXTRACT(emp_length, '\d+') AS INTEGER)
    END                                                       AS emp_length_yrs,
    home_ownership,
    TRY_CAST(annual_inc AS DOUBLE)                            AS annual_inc,
    verification_status,
    TRY_CAST(dti AS DOUBLE)                                   AS dti,
    (TRY_CAST(fico_range_low AS DOUBLE)
       + TRY_CAST(fico_range_high AS DOUBLE)) / 2.0           AS fico,
    TRY_CAST(open_acc AS DOUBLE)                              AS open_acc,
    TRY_CAST(pub_rec AS DOUBLE)                               AS pub_rec,
    TRY_CAST(revol_bal AS DOUBLE)                             AS revol_bal,
    TRY_CAST(REPLACE(revol_util, '%', '') AS DOUBLE)          AS revol_util,
    TRY_CAST(total_acc AS DOUBLE)                             AS total_acc,
    TRY_CAST(mort_acc AS DOUBLE)                              AS mort_acc,
    TRY_CAST(delinq_2yrs AS DOUBLE)                           AS delinq_2yrs,
    TRY_CAST(inq_last_6mths AS DOUBLE)                        AS inq_last_6mths,
    addr_state,
    application_type,

    -- ---- dates ----
    strptime(issue_d, '%b-%Y')::DATE                          AS issue_date,
    -- For charged-off loans, last payment date ≈ default timing.
    -- Used ONLY for vintage-curve construction, NEVER as a model feature.
    strptime(NULLIF(last_pymnt_d, ''), '%b-%Y')::DATE         AS last_pymnt_date,

    -- ---- realized economics (outcome data — for LOSS analysis only,
    --      blacklisted as model features; see docs/data_dictionary.md) ----
    TRY_CAST(total_pymnt AS DOUBLE)                           AS actual_total_pymnt,
    TRY_CAST(recoveries AS DOUBLE)                            AS actual_recoveries

FROM staging.loans_raw
WHERE loan_status IN ('Fully Paid', 'Charged Off',
                      'Does not meet the credit policy. Status:Fully Paid',
                      'Does not meet the credit policy. Status:Charged Off')
  AND TRY_CAST(loan_amnt AS DOUBLE) IS NOT NULL
  AND TRY_CAST(annual_inc AS DOUBLE) IS NOT NULL
  AND issue_d IS NOT NULL;

-- Sanity summary printed by the pipeline runner
SELECT
    COUNT(*)                                   AS n_loans,
    ROUND(AVG(is_default) * 100, 2)            AS default_rate_pct,
    MIN(issue_date)                            AS first_vintage,
    MAX(issue_date)                            AS last_vintage
FROM staging.loans;
