"""
ICP (Ideal Customer Profile) scoring — XGBoost classifier + SHAP.

Predicts probability of conversion, scaled to a 0-100 ICP score. Every
score ships with its top 3 SHAP feature contributions, same
explainability principle as Aegis's risk-scoring SHAP layer — the model
isn't a black box, every score traces back to *why*.

Requires a trained model. Run `python train_model.py` once first (see
that file for what the model is trained on and why).
"""

import os

import numpy as np
import shap
import xgboost as xgb

from app.features import FEATURE_LABELS, FEATURE_NAMES, build_features

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "icp_model.json")

_model = None
_explainer = None


def _load():
    global _model, _explainer
    if _model is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                "Model not found at model/icp_model.json. "
                "Run `python train_model.py` first to train it."
            )
        # Native XGBoost JSON format, not joblib/pickle: pickled
        # XGBClassifier objects are tied to the xgboost version that
        # wrote them and warn (or break) on load under a newer one.
        _model = xgb.XGBClassifier()
        _model.load_model(_MODEL_PATH)
        _explainer = shap.TreeExplainer(_model)
    return _model, _explainer


def score_company(company: dict) -> dict:
    model, explainer = _load()
    company = dict(company)

    feats = build_features(company)
    x = np.array([[feats[name] for name in FEATURE_NAMES]])

    proba = float(model.predict_proba(x)[0, 1])
    icp_score = round(proba * 100, 1)

    shap_values = explainer.shap_values(x)[0]
    top_contributions = sorted(
        zip(FEATURE_NAMES, shap_values, strict=True), key=lambda kv: abs(kv[1]), reverse=True
    )[:3]

    company["icp_score"] = icp_score
    company["score_breakdown"] = {
        FEATURE_LABELS.get(name, name): round(float(val), 3) for name, val in top_contributions
    }
    company["score_method"] = "xgboost_shap_v1"
    return company
