"""
preprocess.py
Feature engineering and preprocessing for click fraud detection.
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import pickle
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ENCODER_PATH = os.path.join(BASE_DIR, "..", "models", "encoder.pkl")

# Categorical columns to encode
CAT_COLS = ["device_type", "browser", "geo_location"]

# Final feature columns fed to the model
FEATURE_COLS = [
    "device_type", "browser", "geo_location",
    "click_interval", "ip_click_count",
    "hour", "is_night", "is_high_freq_ip", "is_rapid_click",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all feature engineering steps:
      - Parse timestamp → extract hour
      - Create is_night flag (22:00 – 06:00)
      - Create is_high_freq_ip flag (>= 50 clicks from same IP)
      - Create is_rapid_click flag (click_interval < 2 seconds)
    """
    df = df.copy()

    # Parse timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["hour"] = df["timestamp"].dt.hour.fillna(0).astype(int)

    # Night-time flag: 10 PM → 6 AM
    df["is_night"] = df["hour"].apply(lambda h: 1 if h >= 22 or h < 6 else 0)

    # High frequency IP flag
    df["is_high_freq_ip"] = (df["ip_click_count"] >= 50).astype(int)

    # Rapid click behaviour (bot-like)
    df["is_rapid_click"] = (df["click_interval"] < 2.0).astype(int)

    return df


def label_encode(df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
    """
    Label-encode categorical columns.
    If fit=True, trains new encoders and saves them.
    If fit=False, loads existing encoders.
    """
    df = df.copy()

    if fit:
        encoders = {}
        for col in CAT_COLS:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
        os.makedirs(os.path.dirname(ENCODER_PATH), exist_ok=True)
        with open(ENCODER_PATH, "wb") as f:
            pickle.dump(encoders, f)
    else:
        with open(ENCODER_PATH, "rb") as f:
            encoders = pickle.load(f)
        for col in CAT_COLS:
            le = encoders[col]
            # Handle unseen labels gracefully
            df[col] = df[col].astype(str).apply(
                lambda x: le.transform([x])[0] if x in le.classes_ else -1
            )

    return df


def preprocess_single(record: dict) -> pd.DataFrame:
    """
    Preprocess a single prediction request dict into a model-ready DataFrame.
    """
    df = pd.DataFrame([record])
    df = engineer_features(df)
    df = label_encode(df, fit=False)

    # Ensure all expected columns exist
    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0

    return df[FEATURE_COLS]


def preprocess_training_data(df: pd.DataFrame):
    """
    Full preprocessing pipeline for training.
    Returns (X, y) ready for XGBoost.
    """
    df = engineer_features(df)
    df = label_encode(df, fit=True)

    X = df[FEATURE_COLS]
    y = df["is_fraud"]
    return X, y
