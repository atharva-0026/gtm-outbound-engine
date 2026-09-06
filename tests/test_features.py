import math

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


def test_zero_employee_count_is_respected_not_treated_as_missing():
    """Regression test: employee_count = company.get('employee_count')
    or 50 previously treated an explicit 0 the same as a missing value
    (0 is falsy), silently defaulting a genuinely-reported 0-employee
    company to 50. A pre-launch startup with 0 employees is a
    realistic input, not an edge case to ignore."""
    feats = build_features({"employee_count": 0})
    assert feats["employee_count_log"] == math.log1p(0) == 0.0


def test_explicit_none_employee_count_still_defaults_to_fifty():
    feats_none = build_features({"employee_count": None})
    feats_missing = build_features({})
    assert feats_none["employee_count_log"] == feats_missing["employee_count_log"]


def test_find_duplicate_company_names_detects_duplicates():
    """Regression test: dashboard.py used company_name as an implicit
    unique key (session_state keys, by_name lookups). Two companies
    sharing a name previously collapsed silently with no warning -
    this function is what now detects that so the UI can warn the user."""
    from app.features import find_duplicate_company_names

    companies = [
        {"company_name": "Acme Corp"},
        {"company_name": "Beta Inc"},
        {"company_name": "Acme Corp"},
        {"company_name": "Gamma LLC"},
    ]
    assert find_duplicate_company_names(companies) == {"Acme Corp"}


def test_find_duplicate_company_names_returns_empty_set_when_all_unique():
    from app.features import find_duplicate_company_names

    companies = [{"company_name": "A"}, {"company_name": "B"}, {"company_name": "C"}]
    assert find_duplicate_company_names(companies) == set()


def test_find_duplicate_company_names_handles_empty_list():
    from app.features import find_duplicate_company_names

    assert find_duplicate_company_names([]) == set()


def test_find_duplicate_company_names_detects_multiple_duplicate_groups():
    from app.features import find_duplicate_company_names

    companies = [
        {"company_name": "Acme"}, {"company_name": "Acme"},
        {"company_name": "Beta"}, {"company_name": "Beta"},
        {"company_name": "Gamma"},
    ]
    assert find_duplicate_company_names(companies) == {"Acme", "Beta"}


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
