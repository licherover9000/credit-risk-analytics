# Risk Committee Memo — PD Cutoff Recommendation

**To:** Credit Risk Committee · **From:** Analytics · **Date:** _____ · **Decision requested:** approve PD cutoff for personal-loan underwriting

*(Template — every blank is filled from pipeline outputs: `reports/cutoff_table.csv`, `reports/model_metrics.txt`, `features.segment_risk`. One page, no more.)*

## Recommendation

Decline applications with modeled PD ≥ **__%** (on top of existing policy rules). At this cutoff we keep an approval rate of **__%** while cutting the approved book's default rate from **__%** to **__%**, saving an estimated **₹__ Cr expected credit loss per ₹100 Cr disbursed**.

## How we got here

1. **Policy rules first** (DTI > 60, FICO < 640, utilization > 120%): decline __% of volume, capturing a pocket with __% default rate. Rules stay because they are explainable and auditable.
2. **Model on the rest**: gradient boosting, out-of-time validated (trained ≤ ____, tested on newer vintages). AUC __, Gini __, calibrated (Brier __). Logistic baseline scored AUC __ — retained as challenger.
3. **Cutoff chosen on economics, not accuracy**: from the tradeoff curve, tightening beyond PD __% costs ~__pp of approvals per ₹__ Cr of additional loss saved — past the point where margin on approved loans covers it.

## What the segmentation shows

- Highest-risk pocket: **grade __ × purpose __ × income decile __** defaults at **__%** = **__× the book average** (n = ____ loans).
- Vintage curves show ____ (e.g., "2015–2016 vintages deteriorate fastest in months 12–24").

## Risks & caveats

- PDs are calibrated on 2007–2018 US data; levels won't transfer to another book, but the *ranking* and the *methodology* do.
- Self-reported income: __% of approved-but-defaulted loans were income-unverified — recommend verification above ₹__ loan size.
- Model to be monitored quarterly for PD calibration drift; challenger logistic kept for benchmark.
