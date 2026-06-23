# GTM Outbound Engine

ICP scoring + personalized outreach generation for RegTech/fintech sales motions.
Pipeline: **enrich → score → personalize → rank**.

This is the same architecture pattern as Aegis (AML risk scoring + RAG-based
SAR narrative generation), retargeted from compliance to sales. That's the
point — it proves the underlying skill (build a system that scores entities
and generates personalized text at scale) transfers directly to GTM
engineering.

## Run it

```bash
pip install -r requirements.txt

# train the model once (writes model/icp_model.joblib)
python train_model.py

# CLI mode — fastest way to see it work
python run_pipeline.py data/real_leads.csv

# API mode
uvicorn app.main:app --reload
# then POST to http://127.0.0.1:8000/pipeline
```

## What it does

- `app/enrichment.py` — fills in missing firmographic fields (mocked, swappable)
- `app/features.py` — shared feature engineering, used identically by training and inference
- `app/scoring.py` — XGBoost classifier + SHAP, predicts conversion probability as a 0-100 ICP score with the top 3 feature contributions per company
- `app/personalize.py` — generates a personalized outreach draft per company
- `app/main.py` — FastAPI wrapper, `/pipeline` runs the full motion end-to-end
- `run_pipeline.py` — CLI runner, no server needed, writes `pipeline_output.json`
- `train_model.py` — generates the training data and trains the model

## The model

**Run `python train_model.py` once before scoring anything** — it writes
`model/icp_model.joblib`. The model file is committed to this repo, so a
fresh clone works out of the box without retraining, but the script is
there so you can see exactly how it was built and retrain whenever the
data changes.

There's no real conversion data yet (no live outbound motion has run).
The training set is synthetic, generated from a domain-informed process:
regulatory exposure (crypto, cross-border, correspondent banking) drives
conversion likelihood up, company size drives it down (longer sales
cycles, more likely to have in-house compliance), and funding stage has
a deliberate *non-linear* sweet spot around Series B/C rather than a
straight line — early-stage companies aren't ready to buy, very mature
ones already have solutions. That non-linearity is the actual reason to
use XGBoost instead of a hand-weighted score: a linear model or a rule
table can't represent a "sweet spot," a tree-based model can.

Current test set: AUC 0.83, accuracy 0.77, on a held-out 20% split.

Every score ships with its top 3 SHAP contributions — which features
pushed this company's score up or down, and by how much. Same
explainability principle as the SHAP layer on Aegis's risk scoring.

When real outcomes exist (responded / didn't, closed-won / lost),
replace `generate_synthetic_dataset()` in `train_model.py` with a loader
for that real labeled data and retrain. Nothing else changes.

## Upgrade path (next, in order)

1. **Swap mock enrichment for Clay.** Sign up, run Clay University's free
   course, replace `enrich_companies()` with a real Clay table pull.
2. **Swap the email template for a real LLM call.** Pass `regulatory_flags`,
   `icp_score`, and the SHAP breakdown into the Claude API and let it write
   the email instead of filling a template.
3. **Get real labels.** Once you've run any outbound (even 20-30 sends),
   retrain on actual responded/didn't-respond outcomes instead of synthetic
   data.
4. **Signal monitoring.** Re-score accounts automatically when a new
   funding round or regulatory licence is announced.

## Metrics to capture once you run it on real data

- Companies enriched / scored
- Time to process 100 leads (manual baseline vs. this pipeline)
- Response rate on personalized vs. generic outreach (if you A/B it)

These three numbers are what go in the portfolio writeup — "automated lead
scoring for X companies, cut manual triage time by Y%" is the line that
gets interviews.

## Ship it

1. Push this repo to GitHub (you already have the GitHub setup from Aegis)
2. Write a 3-paragraph LinkedIn post: problem → what you built → result
3. Apply to GTM Engineer / Growth Engineer / RevOps Engineer roles, link this repo
