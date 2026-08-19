"""
Regression test: FEATURE_NAMES (app/features.py) previously included
"has_recent_signal", but train_model.py's synthetic data generator
never produced that column — every run of `python train_model.py`
(including the CI step that runs it on every push/PR) crashed with
KeyError: "['has_recent_signal'] not in index". The shipped
model/icp_model.joblib was trained separately at some point and drifted
out of sync with what the checked-in script could actually reproduce.

This test generates a small synthetic batch directly and checks every
FEATURE_NAMES column is present, so this specific mismatch can't
silently reappear.
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def test_synthetic_dataset_has_every_feature_column():
    from train_model import generate_synthetic_dataset
    from app.features import FEATURE_NAMES

    df = generate_synthetic_dataset(n=20, seed=1)

    missing = [col for col in FEATURE_NAMES if col not in df.columns]
    assert not missing, f"generate_synthetic_dataset() is missing columns: {missing}"


def test_shipped_model_matches_feature_names():
    """The committed model artifact's expected feature order must match
    FEATURE_NAMES exactly, or scoring.py would silently feed columns in
    the wrong order."""
    import joblib

    from app.features import FEATURE_NAMES

    model = joblib.load(os.path.join(BASE_DIR, "model", "icp_model.joblib"))
    booster_features = model.get_booster().feature_names

    assert booster_features == FEATURE_NAMES, (
        f"model expects {booster_features}, but FEATURE_NAMES is {FEATURE_NAMES}"
    )
