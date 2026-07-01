-- ============================================================
-- 02_features.sql — window-function feature engineering
-- Everything here is computable AT ORIGINATION TIME (no leakage).
-- This file is the SQL showpiece: NTILE, PERCENT_RANK, AVG OVER
-- with cohort partitions, FILTER clauses.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS features;

CREATE OR REPLACE TABLE features.loan_features AS
WITH base AS (
    SELECT
        *,
        DATE_TRUNC('quarter', issue_date)::DATE AS vintage_quarter,
        loan_amnt / NULLIF(annual_inc, 0)       AS loan_to_income,
        installment * 12 / NULLIF(annual_inc, 0) AS payment_to_income
    FROM staging.loans
),

deciled AS (
    SELECT
        *,
        -- Income decile across the whole book (1 = lowest earners)
        NTILE(10) OVER (ORDER BY annual_inc)                    AS income_decile,
        -- FICO band quintile
        NTILE(5)  OVER (ORDER BY fico)                          AS fico_quintile,

        -- Peer-relative positioning: where does this loan sit WITHIN
        -- its grade cohort? A high rate for your grade means the
        -- underwriter priced you as the worst of your peers.
        PERCENT_RANK() OVER (PARTITION BY grade ORDER BY int_rate) AS rate_rank_in_grade,
        PERCENT_RANK() OVER (PARTITION BY grade ORDER BY dti)      AS dti_rank_in_grade,

        -- Deviation from cohort average (grade × term)
        dti - AVG(dti) OVER (PARTITION BY grade, term_months)      AS dti_vs_cohort,
        int_rate - AVG(int_rate) OVER (PARTITION BY sub_grade)     AS rate_vs_subgrade
    FROM base
)

SELECT * FROM deciled;

-- ------------------------------------------------------------
-- Segment lookup: default rate by grade × purpose × income decile.
-- The FILTER clause + window trick computes each segment's lift
-- over the whole-book default rate in one pass.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE features.segment_risk AS
WITH seg AS (
    SELECT
        grade,
        purpose,
        income_decile,
        COUNT(*)                                    AS n_loans,
        SUM(loan_amnt)                              AS disbursed,
        AVG(is_default)                             AS default_rate,
        AVG(fico)                                   AS avg_fico,
        AVG(int_rate)                               AS avg_rate,
        SUM(loan_amnt) FILTER (WHERE is_default = 1) AS defaulted_amount
    FROM features.loan_features
    GROUP BY grade, purpose, income_decile
)
SELECT
    seg.*,
    -- lift vs the TRUE book default rate (loan-weighted), not the
    -- unweighted mean of segment rates — those differ materially
    default_rate
      / NULLIF((SELECT AVG(is_default) FROM features.loan_features), 0)
                                                    AS lift_vs_book,
    RANK() OVER (ORDER BY default_rate DESC)        AS risk_rank
FROM seg
WHERE n_loans >= 200;   -- suppress noise segments

-- Worst 15 segments with meaningful volume — the "3.2× segment" lives here
SELECT grade, purpose, income_decile, n_loans,
       ROUND(default_rate * 100, 1) AS default_pct,
       ROUND(lift_vs_book, 2)       AS lift
FROM features.segment_risk
ORDER BY default_rate DESC
LIMIT 15;
