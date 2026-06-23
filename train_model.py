"""
Trains the ICP scoring model.

No real conversion data exists yet (no live outbound motion has run).
This generates a synthetic dataset from a domain-informed generative
process — deliberately non-linear and non-monotonic (funding stage has
a "sweet spot" around Series B/C, not a straight-line relationship) so
the model has to learn real structure instead of memorizing a weighted
formula a human could write by hand. That non-linearity is also the
honest justification for XGBoost over a simple weighted score.

When real outcome data exists (responded / didn't, closed-won / lost),
replace generate_synthetic_dataset() with a loader for that data and
retrain. Nothing else in the pipeline needs to change.

Run: python train_model.py
"""

import math
import os

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

from app.features import FEATURE_NAMES, FUNDING_STAGE_ORDER

RANDOM_SEED = 42


def generate_synthetic_dataset(n=1200, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)
    funding_stages = list(FUNDING_STAGE_ORDER.keys())
    rows = []

    for _ in range(n):
        employee_count = int(np.clip(rng.lognormal(mean=5.5, sigma=1.3), 5, 50000))
        funding_stage = rng.choice(funding_stages)
        funding_ord = FUNDING_STAGE_ORDER[funding_stage]

        flags = set()
        if rng.random() < 0.25:
            flags.add("crypto")
        if "crypto" in flags and rng.random() < 0.6:
            flags.add("cross-border payments")
        elif rng.random() < 0.30:
            flags.add("cross-border payments")
        if rng.random() < 0.15:
            flags.add("high-risk corridors")
        if rng.random() < 0.15:
            flags.add("correspondent banking")
        if rng.random() < 0.20:
            flags.add("neobank")
        if rng.random() < 0.20:
            flags.add("lending")

        employee_log = math.log1p(employee_count)
        flag_crypto = int("crypto" in flags)
        flag_cb = int("cross-border payments" in flags)
        flag_hrc = int("high-risk corridors" in flags)
        flag_corr = int("correspondent banking" in flags)
        flag_neo = int("neobank" in flags)
        flag_lend = int("lending" in flags)
        num_flags = len(flags)

        # Non-linear sweet spot around Series B/C (ord 3-4)
        funding_component = 1.0 - 0.15 * (funding_ord - 3.5) ** 2

        logit = (
            -2.2
            + 1.8 * flag_crypto
            + 1.4 * flag_cb
            + 1.3 * flag_hrc
            + 1.0 * flag_corr
            + 0.4 * flag_neo
            + 0.2 * flag_lend
            + 0.5 * num_flags
            + 0.6 * (flag_crypto * flag_cb)
            - 0.18 * employee_log
            + 0.7 * funding_component
            + rng.normal(0, 0.6)
        )
        p = 1 / (1 + math.exp(-logit))
        label = int(rng.random() < p)

        rows.append(
            {
                "employee_count_log": employee_log,
                "funding_stage_ord": funding_ord,
                "num_regulatory_flags": num_flags,
                "flag_crypto": flag_crypto,
                "flag_cross_border_payments": flag_cb,
                "flag_high_risk_corridors": flag_hrc,
                "flag_correspondent_banking": flag_corr,
                "flag_neobank": flag_neo,
                "flag_lending": flag_lend,
                "employee_count": employee_count,
                "funding_stage": funding_stage,
                "converted": label,
            }
        )

    return pd.DataFrame(rows)


def main():
    df = generate_synthetic_dataset()
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/synthetic_training_data.csv", index=False)

    X = df[FEATURE_NAMES]
    y = df["converted"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]

    print(f"Trained on {len(X_train)} samples, tested on {len(X_test)}")
    print(f"Test AUC:      {roc_auc_score(y_test, probs):.3f}")
    print(f"Test Accuracy: {accuracy_score(y_test, preds):.3f}")
    print(f"Base rate (% converted in data): {y.mean():.1%}")

    os.makedirs("model", exist_ok=True)
    joblib.dump(model, "model/icp_model.joblib")
    print("Saved model to model/icp_model.joblib")


if __name__ == "__main__":
    main()
