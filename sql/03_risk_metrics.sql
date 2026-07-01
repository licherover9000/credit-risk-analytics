-- ============================================================
-- 03_risk_metrics.sql — portfolio risk analytics
--   1. Vintage curves (cumulative charge-off by months-on-book)
--   2. Realized loss rates & LGD by grade
--   3. Expected-loss table for the cutoff decision
-- ============================================================

CREATE SCHEMA IF NOT EXISTS risk;

-- ------------------------------------------------------------
-- 1. VINTAGE CURVES
-- For charged-off loans, months from issue to last payment ≈ time
-- to default. For each issue-quarter cohort we build the running
-- cumulative default rate by months-on-book — the classic chart a
-- risk team uses to ask "are newer vintages going bad faster?"
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE risk.vintage_curves AS
WITH cohort_sizes AS (
    SELECT vintage_quarter, COUNT(*) AS cohort_n
    FROM features.loan_features
    GROUP BY vintage_quarter
),
default_timing AS (
    SELECT
        vintage_quarter,
        -- months on book at default (charged-off loans only)
        GREATEST(1, DATEDIFF('month', issue_date, last_pymnt_date)) AS mob
    FROM features.loan_features
    WHERE is_default = 1 AND last_pymnt_date IS NOT NULL
),
defaults_by_mob AS (
    SELECT vintage_quarter, mob, COUNT(*) AS n_defaults
    FROM default_timing
    WHERE mob <= 60
    GROUP BY vintage_quarter, mob
)
SELECT
    d.vintage_quarter,
    d.mob,
    d.n_defaults,
    c.cohort_n,
    -- running cumulative default rate — the vintage curve itself
    SUM(d.n_defaults) OVER (
        PARTITION BY d.vintage_quarter
        ORDER BY d.mob
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) * 1.0 / c.cohort_n                            AS cum_default_rate
FROM defaults_by_mob d
JOIN cohort_sizes c USING (vintage_quarter)
ORDER BY d.vintage_quarter, d.mob;

-- ------------------------------------------------------------
-- 2. REALIZED LOSS & LGD BY GRADE
-- LGD = 1 − (recovered cash / exposure at default). We approximate
-- exposure with the funded amount net of principal repaid via
-- total payments received. This feeds the expected-loss model.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE risk.grade_loss AS
SELECT
    grade,
    COUNT(*)                                        AS n_loans,
    AVG(is_default)                                 AS pd_observed,
    SUM(loan_amnt)                                  AS disbursed,
    -- realized net loss on defaulted loans
    SUM(CASE WHEN is_default = 1
             THEN loan_amnt - actual_total_pymnt - actual_recoveries
             ELSE 0 END)                            AS net_loss,
    -- loss given default (severity), floored at 0
    GREATEST(0, SUM(CASE WHEN is_default = 1
             THEN loan_amnt - actual_total_pymnt - actual_recoveries END)
      / NULLIF(SUM(CASE WHEN is_default = 1 THEN loan_amnt END), 0)) AS lgd,
    -- portfolio loss rate: net loss as % of everything disbursed
    SUM(CASE WHEN is_default = 1
             THEN loan_amnt - actual_total_pymnt - actual_recoveries
             ELSE 0 END) / SUM(loan_amnt)           AS loss_rate
FROM features.loan_features
GROUP BY grade
ORDER BY grade;

-- ------------------------------------------------------------
-- 3. EXPECTED LOSS BY SEGMENT  (EL = PD × LGD × EAD)
-- Joins segment PDs with grade-level LGD. This is the table the
-- risk memo and the Power BI cutoff simulator are built from.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE risk.segment_expected_loss AS
SELECT
    s.grade,
    s.purpose,
    s.income_decile,
    s.n_loans,
    s.disbursed,
    s.default_rate                                  AS pd,
    g.lgd,
    s.default_rate * g.lgd * s.disbursed            AS expected_loss,
    s.default_rate * g.lgd                          AS el_rate,       -- EL per ₹1 disbursed
    s.avg_rate / 100.0 - s.default_rate * g.lgd     AS approx_margin  -- price minus risk
FROM features.segment_risk s
JOIN risk.grade_loss g USING (grade)
ORDER BY el_rate DESC;
