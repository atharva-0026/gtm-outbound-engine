"""
Closed-loop re-scoring.

When a new signal is detected (app/signals.py), this decides what to do
with it:

- If it's a funding signal that mentions a recognizable stage ("Series
  C", etc.) and that stage is later than what's on file, funding_stage
  gets updated and the account is genuinely re-scored — the ICP score
  can actually move, because a real input feature changed.
- For every signal regardless of category, the outreach draft gets
  regenerated with the news injected as fresh context, so messaging
  stays current even when the signal doesn't move the model's inputs.

This distinction matters: an acquisition or partnership doesn't change
a company's AML risk exposure, so it shouldn't move the score — but it's
still worth referencing in an email. Only funding-stage changes are
wired to actually shift inputs right now. Regulatory signals are a
natural next case (a new money-transmission licence plausibly *should*
move risk exposure) but that requires reliably extracting which
licence/jurisdiction from free-text headlines, which keyword matching
can't do safely — flagged as a future upgrade, not faked here.
"""

from app.enrichment import enrich_companies
from app.features import FUNDING_STAGE_ORDER
from app.personalize import generate_outreach as _template_outreach
from app.rag_personalize import generate_outreach_rag

SIGNAL_PRIORITY = {"funding": 0, "regulatory": 1, "acquisition": 2, "partnership": 3, "other": 4}


def extract_funding_stage(title: str):
    lowered = title.lower()

    if "ipo" in lowered or "goes public" in lowered:
        return "public"

    import re

    if re.search(r"series [d-z]\b", lowered):
        return "late-stage"

    candidates = [s for s in FUNDING_STAGE_ORDER if s != "unknown" and s in lowered]
    if not candidates:
        return None
    return max(candidates, key=lambda s: FUNDING_STAGE_ORDER[s])


def apply_signal_updates(company: dict, signal: dict) -> dict:
    """Returns a copy of company with funding_stage updated if (and only
    if) the signal is a funding signal mentioning a later stage than
    what's currently on file."""
    updated = dict(company)
    if signal.get("category") != "funding":
        return updated

    detected = extract_funding_stage(signal.get("title", ""))
    if not detected:
        return updated

    current_ord = FUNDING_STAGE_ORDER.get((company.get("funding_stage") or "unknown").lower(), 0)
    if FUNDING_STAGE_ORDER[detected] > current_ord:
        updated["funding_stage"] = detected
    return updated


def rescore_with_signal(company: dict, signal: dict, use_rag: bool = True) -> dict:
    updated_company = apply_signal_updates(company, signal)
    stage_changed = updated_company.get("funding_stage") != company.get("funding_stage")

    updated_company["has_recent_signal"] = 1

    enriched = enrich_companies([updated_company])[0]

    from app.scoring import score_company  # local import avoids a circular import at module load

    scored = score_company(enriched)

    extra_context = [f"Recent news ({signal['category']}): {signal['title']}"]
    draft = (
        generate_outreach_rag(scored, extra_context=extra_context)
        if use_rag
        else _template_outreach(scored)
    )

    return {
        **scored,
        "email_draft": draft,
        "triggered_by_signal": signal["title"],
        "funding_stage_updated": stage_changed,
    }


def process_new_signals(companies: list, new_signals_by_company: dict, use_rag: bool = True) -> dict:
    """For each company with new signals, re-scores using the
    highest-priority signal (funding > regulatory > acquisition >
    partnership > other) as the trigger. Returns {company_name: result}."""
    by_name = {c.get("company_name"): c for c in companies}
    updated = {}

    for name, signals in new_signals_by_company.items():
        company = by_name.get(name)
        if not company or not signals:
            continue
        top_signal = sorted(signals, key=lambda s: SIGNAL_PRIORITY.get(s.get("category"), 5))[0]
        updated[name] = rescore_with_signal(company, top_signal, use_rag=use_rag)

    return updated
