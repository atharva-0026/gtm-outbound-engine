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
