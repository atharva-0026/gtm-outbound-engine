"""
Tests for app/enrichment.py, in particular the ENRICHMENT_PROVIDER
dispatcher added to close out issue #2. Previously had zero test
coverage at all.
"""
import pytest

from app.enrichment import enrich_companies


def test_default_provider_is_mock(monkeypatch):
    monkeypatch.delenv("ENRICHMENT_PROVIDER", raising=False)
    result = enrich_companies([{"company_name": "Acme"}])
    assert result[0]["enrichment_source"] == "mock_v1"


def test_mock_fills_expected_default_fields(monkeypatch):
    monkeypatch.delenv("ENRICHMENT_PROVIDER", raising=False)
    result = enrich_companies([{"company_name": "Acme"}])[0]
    assert result["employee_count"] == 50
    assert result["funding_stage"] == "unknown"
    assert result["country"] == "unknown"
    assert result["regulatory_flags"] == []


def test_mock_does_not_override_existing_fields(monkeypatch):
    monkeypatch.delenv("ENRICHMENT_PROVIDER", raising=False)
    result = enrich_companies([{"company_name": "Acme", "employee_count": 900}])[0]
    assert result["employee_count"] == 900


def test_explicit_mock_provider_matches_default(monkeypatch):
    monkeypatch.setenv("ENRICHMENT_PROVIDER", "mock")
    result = enrich_companies([{"company_name": "Acme"}])
    assert result[0]["enrichment_source"] == "mock_v1"


def test_unimplemented_provider_raises_clear_error_not_silent_noop(monkeypatch):
    """Regression test: a misconfigured ENRICHMENT_PROVIDER must fail
    loudly, not silently return unenriched data or empty results that
    could be mistaken for a working real integration."""
    monkeypatch.setenv("ENRICHMENT_PROVIDER", "apollo")
    with pytest.raises(NotImplementedError, match="apollo"):
        enrich_companies([{"company_name": "Acme"}])
