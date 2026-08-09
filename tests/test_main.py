"""
Tests for app/main.py — the FastAPI wrapper. Previously had zero
coverage despite being one of the two documented ways to run the
pipeline (README: 'API mode').
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_COMPANY = {
    "company_name": "Test Fintech Co",
    "industry": "fintech",
    "employee_count": 250,
    "country": "USA",
    "funding_stage": "series_b",
    "regulatory_flags": ["crypto"],
}


def test_root_returns_status_ok():
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"


def test_enrich_endpoint():
    res = client.post("/enrich", json={"companies": [SAMPLE_COMPANY]})
    assert res.status_code == 200
    enriched = res.json()["enriched"]
    assert len(enriched) == 1
    assert enriched[0]["enrichment_source"] == "mock_v1"


def test_score_endpoint():
    res = client.post("/score", json={"companies": [SAMPLE_COMPANY]})
    assert res.status_code == 200
    scored = res.json()["scored"]
    assert len(scored) == 1
    assert 0 <= scored[0]["icp_score"] <= 100


def test_personalize_endpoint():
    res = client.post("/personalize", json={"companies": [SAMPLE_COMPANY]})
    assert res.status_code == 200
    drafts = res.json()["drafts"]
    assert len(drafts) == 1
    assert "subject" in drafts[0]
    assert "body" in drafts[0]


def test_pipeline_endpoint_end_to_end():
    res = client.post(
        "/pipeline",
        json={
            "companies": [
                SAMPLE_COMPANY,
                {"company_name": "Small Co", "employee_count": 10, "regulatory_flags": []},
            ]
        },
    )
    assert res.status_code == 200
    ranked = res.json()["ranked_leads"]
    assert len(ranked) == 2
    assert "email_draft" in ranked[0]
    # ranked by icp_score descending
    assert ranked[0]["icp_score"] >= ranked[1]["icp_score"]


def test_pipeline_with_empty_companies_list():
    res = client.post("/pipeline", json={"companies": []})
    assert res.status_code == 200
    assert res.json()["ranked_leads"] == []
