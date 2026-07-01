# Risk Committee Memo — PD Cutoff Recommendation

**To:** Credit Risk Committee · **From:** Analytics · **Date:** July 2026 · **Decision requested:** approve PD cutoff for personal-loan underwriting

*(All numbers reproduce from the pipeline: `reports/cutoff_table.csv`, `reports/model_metrics.txt`, `features.segment_risk`. Book: 1.35M completed Lending Club loans, 2007–2018.)*

## Recommendation

Decline applications with modeled PD ≥ **25%** (on top of existing policy rules). At this cutoff we keep an approval rate of **71.2%** while cutting the approved book's default rate from **21.7% to 15.1%**, reducing realized credit loss from **₹9.38 Cr to ₹6.32 Cr per ₹100 Cr disbursed — a saving of ₹3.1 Cr per ₹100 Cr**.

## How we got here

1. **Policy rules first** (DTI > 60, FICO < 640, utilization > 120%): on this book they decline only 0.2% of volume — the originator had already pre-screened these extremes out. The layer stays: it is the explainable, auditable backstop for applications the model never sees, and it will bind on a broader top-of-funnel population.
2. **Model on the rest**: gradient boosting with isotonic calibration, validated **out-of-time** (trained on 1.08M loans issued ≤ Oct 2016, tested on 262k newer loans). Test AUC **0.713**, Gini **0.426**, Brier **0.154**. Logistic baseline scored AUC 0.701 — retained as challenger; the 1.2pt AUC gap is worth ~₹0.2–0.3 Cr per ₹100 Cr at the operating point.
3. **Cutoff chosen on economics, not accuracy**: tightening from PD 30% to 25% gives up 10.7pp of approvals to save ~₹1.0 Cr per ₹100 Cr; tightening further to 20% gives up another 15pp to save ~₹1.2 Cr — approvals fall faster than losses beyond 25%. At an average portfolio yield of ~13%, the margin on marginal approvals below the 25% line no longer covers their expected loss.

## What the segmentation shows

- Highest-risk pocket: **grade G × debt-consolidation × income deciles 1–5** defaults at **52.8–57.7%** = up to **2.89× the book average** (n = 555–608 per cell; grade F equivalents run 49–52% on 1.8k–2.3k loans per cell).
- PD is cleanly monotonic across grades (A: 6.0% → G: 49.7%) while **LGD is flat at 37–40%** across all grades — unsecured recovery doesn't depend on who defaulted. Loss rate therefore runs 2.4% (A) to 20.0% (G) of disbursed.
- **Vintage curves tell the growth-vs-quality story**: crisis vintages (2007–08) defaulted at 22–29% by month 36; post-crisis tightening pushed 2009–2011 vintages to 12–13%; quality then deteriorated steadily 2012→2016 (15.2% → 20.2%) as origination volume scaled.

## Risks & caveats

- **Verification-status inversion**: income-*verified* loans default at 23.9% vs 14.7% for unverified — verification was triggered *by* riskiness (selection effect), so it must not be read as protective, and naïve "require verification" policies would not have saved these losses.
- PDs are calibrated on 2007–2018 US data; the levels won't transfer to another book, but the ranking, segmentation, and cutoff methodology do.
- Model monitored quarterly for calibration drift; logistic challenger retained as benchmark.
