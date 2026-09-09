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


def test_personalize_returns_real_icp_score_not_always_zero():
    """Regression test: /personalize previously passed raw, un-scored
    company data straight to generate_outreach(), so icp_score in the
    response was ALWAYS 0 regardless of the company's actual risk
    profile. SAMPLE_COMPANY has employee_count=250 and a crypto flag,
    a real risk profile that should not score as exactly 0."""
    res = client.post("/personalize", json={"companies": [SAMPLE_COMPANY]})
    assert res.status_code == 200
    drafts = res.json()["drafts"]
    assert drafts[0]["icp_score"] != 0, (
        "icp_score should reflect the company's actual scored risk, not "
        "the un-enriched default of 0"
    )


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


def test_pipeline_isolates_one_bad_company_instead_of_crashing_whole_batch():
    """Regression test: employee_count=-500 (valid per the Pydantic
    model's plain int type, but causes math.log1p to raise
    'math domain error') previously crashed the ENTIRE /pipeline
    request, losing every other company's results too."""
    res = client.post(
        "/pipeline",
        json={
            "companies": [
                {"company_name": "GoodCo1", "employee_count": 100, "regulatory_flags": []},
                {"company_name": "BadCo", "employee_count": -500, "regulatory_flags": []},
                {"company_name": "GoodCo2", "employee_count": 50, "regulatory_flags": []},
            ]
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["ranked_leads"]) == 2
    names = {r["company_name"] for r in body["ranked_leads"]}
    assert names == {"GoodCo1", "GoodCo2"}
    assert len(body["errors"]) == 1
    assert body["errors"][0]["company_name"] == "BadCo"
    assert "employee_count must be non-negative" in body["errors"][0]["error"]


def test_score_isolates_one_bad_company_instead_of_crashing_whole_batch():
    res = client.post(
        "/score",
        json={
            "companies": [
                {"company_name": "GoodCo", "employee_count": 100, "regulatory_flags": []},
                {"company_name": "BadCo", "employee_count": -500, "regulatory_flags": []},
            ]
        },
    )
    assert res.status_code == 200
    scored = res.json()["scored"]
    assert len(scored) == 2
    good = next(s for s in scored if s["company_name"] == "GoodCo")
    bad = next(s for s in scored if s["company_name"] == "BadCo")
    assert "icp_score" in good
    assert "employee_count must be non-negative" in bad["error"]
