"""
Shared feature engineering — used identically by train_model.py (training)
and scoring.py (inference), so train/serve never drift apart.
"""

import math

FUNDING_STAGE_ORDER = {
    "unknown": 0,
    "seed": 1,
    "series a": 2,
    "series b": 3,
    "series c": 4,
    "late-stage": 5,
    "public": 6,
}

REGULATORY_FLAGS = [
    "crypto",
    "cross-border payments",
    "high-risk corridors",
    "correspondent banking",
    "neobank",
    "lending",
]

FEATURE_NAMES = [
    "employee_count_log",
    "funding_stage_ord",
    "flag_crypto",
    "flag_cross_border_payments",
    "flag_high_risk_corridors",
    "flag_correspondent_banking",
    "flag_neobank",
    "flag_lending",
    "has_recent_signal",
]

FEATURE_LABELS = {
    "employee_count_log": "company size",
    "funding_stage_ord": "funding stage",
    "num_regulatory_flags": "regulatory complexity",
    "flag_crypto": "crypto exposure",
    "flag_cross_border_payments": "cross-border payments",
    "flag_high_risk_corridors": "high-risk corridors",
    "flag_correspondent_banking": "correspondent banking",
    "flag_neobank": "neobank model",
    "flag_lending": "lending exposure",
    "has_recent_signal": "active buying signal",
}


def build_features(company: dict) -> dict:
    # `or 50` (rather than an explicit None check) would silently treat
    # a genuinely reported 0 employees the same as a missing value,
    # since 0 is falsy in Python - `0 or 50` evaluates to 50. A
    # pre-launch startup with 0 employees on file is exactly the kind
    # of lead this tool might process, so this must distinguish
    # "missing" from "explicitly zero".
    employee_count = company.get("employee_count")
    if employee_count is None:
        employee_count = 50
    # math.log1p(x) raises ValueError ("math domain error") for x <= -1.
    # employee_count is a plain int in the Pydantic model with no
    # non-negative constraint, so a negative value (bad data entry,
    # or a malicious/malformed request) reaches here unvalidated and
    # crashes the entire request - not just that one company's score,
    # since main.py's /pipeline loops over companies with no
    # per-company error handling. Confirmed reachable through the real
    # FastAPI endpoint with employee_count=-500.
    if employee_count < 0:
        raise ValueError(f"employee_count must be non-negative, got {employee_count}")
    funding_stage = (company.get("funding_stage") or "unknown").lower()
    flags = {f.lower() for f in (company.get("regulatory_flags") or [])}

    return {
        "employee_count_log": math.log1p(employee_count),
        "funding_stage_ord": FUNDING_STAGE_ORDER.get(funding_stage, 0),
        "num_regulatory_flags": len(flags),
        "flag_crypto": int("crypto" in flags),
        "flag_cross_border_payments": int("cross-border payments" in flags),
        "flag_high_risk_corridors": int("high-risk corridors" in flags),
        "flag_correspondent_banking": int("correspondent banking" in flags),
        "flag_neobank": int("neobank" in flags),
        "flag_lending": int("lending" in flags),
        "has_recent_signal": int(bool(company.get("has_recent_signal", 0))),
    }


def find_duplicate_company_names(companies: list[dict]) -> set[str]:
    """
    Returns the set of company_name values that appear more than once
    in companies. company_name is used as an implicit unique key in
    several places (dashboard.py's session_state keys, by_name lookups)
    - duplicates would silently collapse to one entry with no
    indication anything was lost, so callers should warn the user
    rather than let that happen invisibly.
    """
    seen = set()
    duplicates = set()
    for c in companies:
        name = c.get("company_name")
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return duplicates


def results_to_csv(results: list[dict], edited_drafts: dict[str, dict] | None = None) -> str:
    """
    Builds a CSV string from scored/personalized results, ready to
    hand to a lead's CRM or email tool - the app previously had no
    export path at all, so the only way to get scored leads out was
    reading them off the screen by hand.

    edited_drafts, if given, maps company_name -> {"subject": ..., "body": ...}
    for drafts the user has hand-edited in the UI (dashboard.py's
    subject_{name}/body_{name} widget state) - those take precedence
    over the originally-generated draft, so exporting reflects what the
    user actually sees on screen, not stale generated copy.
    """
    import csv
    import io

    edited_drafts = edited_drafts or {}
    fieldnames = [
        "company_name", "icp_score", "industry", "country",
        "funding_stage", "employee_count", "top_driver",
        "email_subject", "email_body",
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for r in results:
        name = r.get("company_name", "")
        breakdown = r.get("score_breakdown") or {}
        top_driver = next(iter(breakdown), "")

        draft = r.get("email_draft") or {}
        edited = edited_drafts.get(name, {})
        subject = edited.get("subject") if edited.get("subject") is not None else draft.get("subject", "")
        body = edited.get("body") if edited.get("body") is not None else draft.get("body", "")

        writer.writerow({
            "company_name": name,
            "icp_score": r.get("icp_score", ""),
            "industry": r.get("industry", ""),
            "country": r.get("country", ""),
            "funding_stage": r.get("funding_stage", ""),
            "employee_count": r.get("employee_count", ""),
            "top_driver": top_driver,
            "email_subject": subject,
            "email_body": body,
        })

    return buf.getvalue()
