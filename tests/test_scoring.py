from app.scoring import score_company


def test_score_is_in_valid_range():
    result = score_company({"company_name": "Test Co", "employee_count": 100, "regulatory_flags": []})
    assert 0 <= result["icp_score"] <= 100


def test_score_breakdown_has_three_entries():
    result = score_company({"company_name": "Test Co", "employee_count": 100, "regulatory_flags": ["crypto"]})
    assert len(result["score_breakdown"]) == 3


def test_breakdown_uses_readable_labels_not_raw_feature_names():
    result = score_company({"company_name": "Test Co", "regulatory_flags": ["crypto"]})
    # raw names like "flag_crypto" should never leak into output
    for label in result["score_breakdown"]:
        assert not label.startswith("flag_")
        assert "_" not in label


def test_more_regulatory_exposure_scores_higher():
    low = score_company({"company_name": "Low", "employee_count": 500, "regulatory_flags": []})
    high = score_company({"company_name": "High", "employee_count": 500, "regulatory_flags": ["crypto", "cross-border payments", "high-risk corridors"]})
    assert high["icp_score"] > low["icp_score"]


def test_active_signal_increases_score_for_same_company():
    """Regression test for the bug where has_recent_signal was trained
    into the model but never actually set anywhere — caught manually
    once already, shouldn't regress silently again."""
    base = {"company_name": "Test Co", "employee_count": 900, "funding_stage": "late-stage", "regulatory_flags": ["crypto"]}
    without_signal = score_company({**base})
    with_signal = score_company({**base, "has_recent_signal": 1})
    assert with_signal["icp_score"] > without_signal["icp_score"]
