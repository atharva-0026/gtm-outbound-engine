from app.features import FEATURE_NAMES, build_features


def test_build_features_returns_all_expected_keys():
    feats = build_features({"company_name": "Test Co"})
    for name in FEATURE_NAMES:
        assert name in feats


def test_missing_fields_default_safely():
    feats = build_features({})
    assert feats["employee_count_log"] > 0  # defaults to 50 employees, not 0 or crash
    assert feats["funding_stage_ord"] == 0  # unknown
    assert feats["has_recent_signal"] == 0


def test_regulatory_flags_are_case_insensitive():
    feats = build_features({"regulatory_flags": ["CRYPTO", "Cross-Border Payments"]})
    assert feats["flag_crypto"] == 1
    assert feats["flag_cross_border_payments"] == 1
    assert feats["flag_lending"] == 0


def test_funding_stage_ordering():
    seed = build_features({"funding_stage": "Seed"})
    series_c = build_features({"funding_stage": "Series C"})
    public = build_features({"funding_stage": "Public"})
    assert seed["funding_stage_ord"] < series_c["funding_stage_ord"] < public["funding_stage_ord"]


def test_has_recent_signal_flag_passes_through():
    feats = build_features({"has_recent_signal": 1})
    assert feats["has_recent_signal"] == 1
