from fastapi import FastAPI
from pydantic import BaseModel

from app.enrichment import enrich_companies
from app.rag_personalize import generate_outreach_rag as generate_outreach
from app.scoring import score_company

app = FastAPI(title="GTM Outbound Engine")


class Company(BaseModel):
    company_name: str
    industry: str | None = None
    employee_count: int | None = None
    country: str | None = None
    funding_stage: str | None = None
    regulatory_flags: list[str] | None = []


class CompanyList(BaseModel):
    companies: list[Company]


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "GTM Outbound Engine running. POST a company list to /pipeline.",
    }


@app.post("/enrich")
def enrich(payload: CompanyList):
    enriched = enrich_companies([c.model_dump() for c in payload.companies])
    return {"enriched": enriched}


@app.post("/score")
def score(payload: CompanyList):
    scored = [score_company(c.model_dump()) for c in payload.companies]
    return {"scored": scored}


@app.post("/personalize")
def personalize(payload: CompanyList):
    drafts = [generate_outreach(c.model_dump()) for c in payload.companies]
    return {"drafts": drafts}


@app.post("/pipeline")
def pipeline(payload: CompanyList):
    """Full GTM motion: enrich -> score -> personalize -> rank."""
    results = []
    for c in payload.companies:
        cd = c.model_dump()
        enriched = enrich_companies([cd])[0]
        scored = score_company(enriched)
        draft = generate_outreach(scored)
        results.append({**scored, "email_draft": draft})

    results.sort(key=lambda x: x["icp_score"], reverse=True)
    return {"ranked_leads": results}
