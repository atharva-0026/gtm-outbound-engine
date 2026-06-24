from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from app.enrichment import enrich_companies
from app.scoring import score_company
from app.rag_personalize import generate_outreach_rag as generate_outreach

app = FastAPI(title="GTM Outbound Engine")


class Company(BaseModel):
    company_name: str
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    country: Optional[str] = None
    funding_stage: Optional[str] = None
    regulatory_flags: Optional[List[str]] = []


class CompanyList(BaseModel):
    companies: List[Company]


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "GTM Outbound Engine running. POST a company list to /pipeline.",
    }


@app.post("/enrich")
def enrich(payload: CompanyList):
    enriched = enrich_companies([c.dict() for c in payload.companies])
    return {"enriched": enriched}


@app.post("/score")
def score(payload: CompanyList):
    scored = [score_company(c.dict()) for c in payload.companies]
    return {"scored": scored}


@app.post("/personalize")
def personalize(payload: CompanyList):
    drafts = [generate_outreach(c.dict()) for c in payload.companies]
    return {"drafts": drafts}


@app.post("/pipeline")
def pipeline(payload: CompanyList):
    """Full GTM motion: enrich -> score -> personalize -> rank."""
    results = []
    for c in payload.companies:
        cd = c.dict()
        enriched = enrich_companies([cd])[0]
        scored = score_company(enriched)
        draft = generate_outreach(scored)
        results.append({**scored, "email_draft": draft})

    results.sort(key=lambda x: x["icp_score"], reverse=True)
    return {"ranked_leads": results}
