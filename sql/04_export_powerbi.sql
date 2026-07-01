-- ============================================================
-- 04_export_powerbi.sql — export analysis tables for Power BI
-- Parquet for speed; loan-level fact table sampled columns only.
-- ============================================================

COPY (SELECT loan_id, is_default, loan_amnt, term_months, int_rate,
             grade, sub_grade, purpose, home_ownership, annual_inc,
             dti, fico, income_decile, fico_quintile, loan_to_income,
             vintage_quarter, issue_date, addr_state
      FROM features.loan_features)
TO 'data/processed/fact_loans.parquet' (FORMAT PARQUET);

COPY (SELECT * FROM features.segment_risk)
TO 'data/processed/segment_risk.parquet' (FORMAT PARQUET);

COPY (SELECT * FROM risk.vintage_curves)
TO 'data/processed/vintage_curves.parquet' (FORMAT PARQUET);

COPY (SELECT * FROM risk.grade_loss)
TO 'data/processed/grade_loss.parquet' (FORMAT PARQUET);

COPY (SELECT * FROM risk.segment_expected_loss)
TO 'data/processed/segment_expected_loss.parquet' (FORMAT PARQUET);

-- CSV copies of the small tables for quick inspection
COPY (SELECT * FROM risk.grade_loss) TO 'data/processed/grade_loss.csv' (HEADER);
COPY (SELECT * FROM risk.segment_expected_loss) TO 'data/processed/segment_expected_loss.csv' (HEADER);
