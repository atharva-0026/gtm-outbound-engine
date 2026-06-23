"""
ICP (Ideal Customer Profile) scoring.

Rule-based and fully transparent on purpose — every score breaks down
into named components, same principle as the SHAP explainability layer
on Aegis. When you have real outcome data (closed-won/lost), replace
this with a trained model (XGBoost) and keep the breakdown output for
explainability.
"""

from typing import Dict

REGULATORY_WEIGHTS = {
    "crypto": 25,
    "cross-border payments": 20,
    "high-risk corridors": 20,
    "correspondent banking": 15,
    "neobank": 10,
    "lending": 8,
}

SIZE_BANDS = [
    (0, 50, 10),
    (51, 200, 20),
    (201, 1000, 15),
    (1001, 10**9, 5),
]


def _size_score(employee_count: int) -> int:
    for low, high, score in SIZE_BANDS:
        if low <= employee_count <= high:
            return score
    return 5


def score_company(company: Dict) -> Dict:
    company = dict(company)
    reg_flags = company.get("regulatory_flags", []) or []
    reg_score = sum(REGULATORY_WEIGHTS.get(f.lower(), 5) for f in reg_flags)

    size_score = _size_score(company.get("employee_count", 50) or 50)

    funding_stage = (company.get("funding_stage") or "").lower()
    funding_score = 10 if funding_stage in ("series a", "series b") else 5

    total = min(100, reg_score + size_score + funding_score)

    company["icp_score"] = total
    company["score_breakdown"] = {
        "regulatory_exposure": reg_score,
        "company_size_fit": size_score,
        "funding_stage_fit": funding_score,
    }
    return company
