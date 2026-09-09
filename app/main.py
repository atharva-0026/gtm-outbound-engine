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
    scored = []
    for c in payload.companies:
        try:
            scored.append(score_company(c.model_dump()))
        except (ValueError, TypeError) as e:
            # A single company with bad data (e.g. a negative
            # employee_count, which the Pydantic model's plain `int`
            # type doesn't reject) previously crashed this entire
            # request, losing every other company's score too.
            scored.append({"company_name": c.company_name, "error": str(e)})
    return {"scored": scored}


@app.post("/personalize")
def personalize(payload: CompanyList):
    # generate_outreach() reads icp_score from the company dict it's
    # given (used in both the drafted email copy and the response's
    # icp_score field). This endpoint previously passed raw,
    # un-enriched, un-scored company data straight through, so
    # icp_score was ALWAYS 0 regardless of the company's actual risk
    # profile - confirmed reachable: a crypto exchange with obvious
    # risk exposure still returned icp_score: 0 here. The README
    # documents the pipeline order as "enrich -> score -> personalize
    # -> rank", so this standalone step must run enrich+score first to
    # match, exactly like /pipeline already does per-company.
    drafts = []
    for c in payload.companies:
        enriched = enrich_companies([c.model_dump()])[0]
        scored = score_company(enriched)
        drafts.append(generate_outreach(scored))
    return {"drafts": drafts}


@app.post("/pipeline")
def pipeline(payload: CompanyList):
    """Full GTM motion: enrich -> score -> personalize -> rank."""
    results = []
    errors = []
    for c in payload.companies:
        try:
            cd = c.model_dump()
            enriched = enrich_companies([cd])[0]
            scored = score_company(enriched)
            draft = generate_outreach(scored)
            results.append({**scored, "email_draft": draft})
        except (ValueError, TypeError) as e:
            # Confirmed reachable: a single company with
            # employee_count=-500 (valid per the Pydantic model, which
            # has no non-negative constraint on this plain int field)
            # crashed the ENTIRE /pipeline request with an unhandled
            # ValueError from math.log1p(), wiping out results for
            # every other successfully-processable company in the
            # batch. Isolate failures per-company instead.
            errors.append({"company_name": c.company_name, "error": str(e)})

    results.sort(key=lambda x: x["icp_score"], reverse=True)
    response = {"ranked_leads": results}
    if errors:
        response["errors"] = errors
    return response
