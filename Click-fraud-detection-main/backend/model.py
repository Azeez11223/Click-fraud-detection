"""
model.py
XGBoost model training, evaluation, and inference.
"""
import os
import sys
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier   # fallback if xgboost missing
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_score,
                             recall_score, f1_score, classification_report)

# Try XGBoost first, fall back to sklearn GBM
try:
    from xgboost import XGBClassifier
    USE_XGB = True
except ImportError:
    USE_XGB = False
    print("[WARN] xgboost not installed - using sklearn GradientBoostingClassifier as fallback.")

# Try SMOTE
try:
    from imblearn.over_sampling import SMOTE
    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import preprocess_training_data, preprocess_single

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "model.pkl")
DATA_PATH  = os.path.join(BASE_DIR, "..", "data", "dataset.csv")

# Global metrics cache
_metrics: dict = {}


def get_scale_pos_weight(y):
    """Compute scale_pos_weight = negatives / positives."""
    neg = (y == 0).sum()
    pos = (y == 1).sum()
    return neg / pos if pos > 0 else 1.0


def train_model(use_smote: bool = False) -> dict:
    """Train model from dataset.csv. Returns evaluation metrics dict."""
    global _metrics

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Run: python data/generate_dataset.py"
        )

    # Load & preprocess
    df = pd.read_csv(DATA_PATH)
    print(f"[INFO] Loaded {len(df):,} rows | Fraud rate: {df['is_fraud'].mean()*100:.1f}%")

    X, y = preprocess_training_data(df)

    # Stratified train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Handle class imbalance
    if use_smote and HAS_SMOTE:
        print("[INFO] Applying SMOTE...")
        sm = SMOTE(random_state=42)
        X_train, y_train = sm.fit_resample(X_train, y_train)
        spw = 1.0
    elif use_smote and not HAS_SMOTE:
        print("[WARN] imbalanced-learn not installed; using scale_pos_weight instead.")
        spw = get_scale_pos_weight(y_train)
    else:
        spw = get_scale_pos_weight(y_train)
        print(f"[INFO] scale_pos_weight = {spw:.2f}")

    # Build model
    if USE_XGB:
        model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=spw,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)],
                  verbose=False)
    else:
        model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )
        model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    _metrics = {
        "accuracy":  round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1_score":  round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
    }
    print("[METRICS]", _metrics)
    print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"]))

    # Persist
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"[SAVED] Model saved -> {MODEL_PATH}")

    return _metrics


def load_model():
    """Load saved model from disk."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Train the model first via POST /train."
        )
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_single(record: dict) -> dict:
    """Run inference on one click record. Returns prediction + confidence."""
    model = load_model()
    X = preprocess_single(record)
    prob  = float(model.predict_proba(X)[0][1])
    label = "Fraud" if prob >= 0.5 else "Legit"
    return {"prediction": label, "confidence": round(prob, 4)}


def get_metrics() -> dict:
    """Return cached metrics."""
    global _metrics
    if not _metrics:
        if os.path.exists(MODEL_PATH):
            return {"note": "Model loaded from disk. Retrain to refresh metrics."}
        return {"note": "Model not trained yet. POST /train to begin."}
    return _metrics
