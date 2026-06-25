from app.retrieval import retrieve_for_company


def test_known_company_gets_its_own_curated_fact():
    docs = retrieve_for_company({"company_name": "Bitpanda", "regulatory_flags": ["crypto"]})
    assert any("Bitpanda" in d for d in docs)


def test_known_company_gets_matching_industry_context():
    docs = retrieve_for_company({"company_name": "Bitpanda", "regulatory_flags": ["crypto", "cross-border payments"]})
    combined = " ".join(docs).lower()
    assert "mica" in combined or "travel rule" in combined or "wallet clustering" in combined


def test_unknown_company_falls_back_to_semantic_search():
    docs = retrieve_for_company({"company_name": "TotallyMadeUpCo123", "regulatory_flags": ["lending"]})
    assert len(docs) > 0  # should never return empty, even for unseen companies


def test_company_with_no_flags_and_not_curated_still_returns_something():
    docs = retrieve_for_company({"company_name": "AnotherMadeUpCo", "regulatory_flags": []})
    assert len(docs) > 0
