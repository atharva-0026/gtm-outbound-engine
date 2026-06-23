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
    "num_regulatory_flags",
    "flag_crypto",
    "flag_cross_border_payments",
    "flag_high_risk_corridors",
    "flag_correspondent_banking",
    "flag_neobank",
    "flag_lending",
]


def build_features(company: dict) -> dict:
    employee_count = company.get("employee_count") or 50
    funding_stage = (company.get("funding_stage") or "unknown").lower()
    flags = set(f.lower() for f in (company.get("regulatory_flags") or []))

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
    }
