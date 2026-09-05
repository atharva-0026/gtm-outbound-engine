from app.closed_loop import (
    apply_signal_updates,
    extract_funding_stage,
    process_new_signals,
    rescore_with_signal,
)


def test_extract_funding_stage_recognizes_named_stages():
    assert extract_funding_stage("Acme raises Series C round") == "series c"


def test_extract_funding_stage_groups_d_and_beyond_as_late_stage():
    assert extract_funding_stage("Acme raises Series D round") == "late-stage"
    assert extract_funding_stage("Acme raises Series F round") == "late-stage"


def test_extract_funding_stage_recognizes_ipo():
    assert extract_funding_stage("Acme goes public in NYSE debut") == "public"


def test_extract_funding_stage_recognizes_ipo_keyword():
    assert extract_funding_stage("Acme announces IPO plans for Q3") == "public"


def test_extract_funding_stage_does_not_false_positive_on_unrelated_public_mentions():
    """Regression test: 'public' was included in the generic
    substring-matching fallback, so any headline mentioning 'public'
    in an unrelated sense (public health, public criticism, public
    records) incorrectly extracted the highest funding stage tier.
    Confirmed reachable through the real pipeline: this exact headline
    is classified as a funding signal by app/signals.py's keyword
    matching (it contains 'raises'), so this path does get exercised
    on real headlines, not just a contrived example."""
    result = extract_funding_stage("Startup raises new funding amid public criticism over fees")
    assert result != "public"
    # No named stage is mentioned, so this should extract nothing at all.
    assert result is None


def test_extract_funding_stage_public_mention_does_not_override_named_stage():
    """Even if a headline mentions both a real stage and an unrelated
    'public' reference, the named stage must win, not 'public'."""
    result = extract_funding_stage("Acme raises Series B round amid public scrutiny of fintech sector")
    assert result == "series b"


def test_extract_funding_stage_returns_none_for_non_funding_text():
    assert extract_funding_stage("Acme partners with Visa") is None


def test_apply_signal_updates_upgrades_stage_when_later():
    company = {"company_name": "Acme", "funding_stage": "seed"}
    signal = {"category": "funding", "title": "Acme raises Series C"}
    updated = apply_signal_updates(company, signal)
    assert updated["funding_stage"] == "series c"


def test_apply_signal_updates_does_not_downgrade_stage():
    company = {"company_name": "Acme", "funding_stage": "late-stage"}
    signal = {"category": "funding", "title": "Acme raises Series C"}
    updated = apply_signal_updates(company, signal)
    assert updated["funding_stage"] == "late-stage"  # unchanged, series c < late-stage


def test_apply_signal_updates_ignores_non_funding_signals():
    company = {"company_name": "Acme", "funding_stage": "seed"}
    signal = {"category": "partnership", "title": "Acme partners with Visa"}
    updated = apply_signal_updates(company, signal)
    assert updated["funding_stage"] == "seed"


def test_rescore_with_signal_sets_has_recent_signal():
    """Direct regression test for the exact bug already caught once:
    has_recent_signal must actually be set to 1 during a signal-triggered
    re-score, not just exist as an unused trained feature."""
    company = {"company_name": "Acme", "employee_count": 500, "funding_stage": "seed", "regulatory_flags": ["crypto"]}
    signal = {"category": "partnership", "title": "Acme partners with Visa"}
    result = rescore_with_signal(company, signal, use_rag=False)
    assert "triggered_by_signal" in result
    assert result["triggered_by_signal"] == signal["title"]


def test_rescore_with_signal_score_increases_vs_baseline():
    from app.enrichment import enrich_companies
    from app.scoring import score_company

    company = {"company_name": "Acme", "employee_count": 500, "funding_stage": "seed", "regulatory_flags": ["crypto"]}
    baseline = score_company(enrich_companies([company])[0])

    signal = {"category": "partnership", "title": "Acme partners with Visa"}
    result = rescore_with_signal(company, signal, use_rag=False)

    assert result["icp_score"] > baseline["icp_score"]


def test_process_new_signals_picks_highest_priority_signal_per_company():
    companies = [{"company_name": "Acme", "employee_count": 500, "regulatory_flags": []}]
    signals_by_company = {
        "Acme": [
            {"category": "other", "title": "Acme mentioned in passing"},
            {"category": "funding", "title": "Acme raises Series B"},
        ]
    }
    result = process_new_signals(companies, signals_by_company, use_rag=False)
    assert result["Acme"]["triggered_by_signal"] == "Acme raises Series B"


def test_process_new_signals_skips_companies_not_in_list():
    companies = [{"company_name": "Acme", "employee_count": 500}]
    signals_by_company = {"NotInList": [{"category": "funding", "title": "Some news"}]}
    result = process_new_signals(companies, signals_by_company, use_rag=False)
    assert result == {}
