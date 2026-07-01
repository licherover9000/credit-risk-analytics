# Power BI Risk Dashboard — build spec

Data source: **Get Data → Parquet** → the five files in `data/processed/`. Model them star-style: `fact_loans` is the fact; `segment_risk`, `grade_loss`, `vintage_curves`, `segment_expected_loss` are pre-aggregated analysis tables (no relationships needed to fact except grade if desired).

## Page 1 — Portfolio Overview
- KPI cards: total disbursed, loan count, book default rate, portfolio loss rate, avg FICO.
- Default rate by grade (column), by vintage year (line), disbursed by purpose (bar).
- Slicers: term, grade, purpose, vintage year.

## Page 2 — Segment Risk Heatmap
- Matrix: grade (rows) × income decile (columns), values = default rate, conditional-format red scale. This is where the "3.2× segment" jumps out visually.
- Table beneath: top-15 risk segments from `segment_risk` with lift and n.

## Page 3 — Vintage Curves
- Line chart from `vintage_curves`: x = `mob`, y = `cum_default_rate`, legend = `vintage_quarter` (filter to quarters with ≥ 36 months observation).

## Page 4 — Cutoff Simulator (the closer)
- Import `reports/cutoff_table.csv`. What-if parameter or slider on `pd_cutoff`; cards show approval rate, default rate, loss per ₹100 Cr at the selected cutoff. Dual-axis line: approval vs default rate.

## Core DAX measures

```dax
Default Rate = DIVIDE(SUM(fact_loans[is_default]), COUNTROWS(fact_loans))

Disbursed ₹Cr = SUM(fact_loans[loan_amnt]) * 83 / 10000000  -- USD→INR→Cr

Default Rate Lift =
DIVIDE([Default Rate],
       CALCULATE([Default Rate], REMOVEFILTERS(fact_loans)))

Bad ₹ Share =  -- share of money, not loans, that went bad
DIVIDE(CALCULATE(SUM(fact_loans[loan_amnt]), fact_loans[is_default] = 1),
       SUM(fact_loans[loan_amnt]))
```

Publish to Power BI Service (free tier) → "Publish to web" for the shareable resume link.
