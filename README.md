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

# CLI mode — fastest way to see it work
python run_pipeline.py data/sample_leads.csv

# API mode
uvicorn app.main:app --reload
# then POST to http://127.0.0.1:8000/pipeline
```

## What it does

- `app/enrichment.py` — fills in missing firmographic fields (mocked, swappable)
- `app/scoring.py` — weighted ICP score, regulatory exposure as primary signal, full breakdown for explainability
- `app/personalize.py` — generates a personalized outreach draft per company
- `app/main.py` — FastAPI wrapper, `/pipeline` runs the full motion end-to-end
- `run_pipeline.py` — CLI runner, no server needed, writes `pipeline_output.json`

## Upgrade path (do these in order, this week)

1. **Swap mock enrichment for Clay.** Sign up, run Clay University's free
   course, replace `enrich_companies()` with a real Clay table pull.
2. **Swap the email template for a real LLM call.** Pass `regulatory_flags`
   and `icp_score` into the Claude API and let it write the email instead
   of filling a template. Keep the structured output format.
3. **Replace the rule-based scorer with a trained model** once you have
   even 20-30 labeled outcomes (responded / didn't respond). XGBoost +
   SHAP, same as Aegis — you already know this pattern.
4. **Point it at a real list.** You already have one: the 30+ companies
   from your AML/RegTech cold outreach (Flagright, Hawk AI, Salv, Unit21,
   Signzy, Greenlite...). Run them through this pipeline. Now you have a
   live demo you can show *those same companies* — "I built a GTM engine
   and ran it against companies like yours" is a much stronger opener
   than a cold email.

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
