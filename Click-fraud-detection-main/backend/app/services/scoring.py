"""Process-wide model loading and rules-only fallback."""
from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse


@lru_cache(maxsize=1)
def _load_model():
    path = os.getenv("MODEL_PATH", "models/model.json")
    model_url = os.getenv("MODEL_URL")
    expected_hash = os.getenv("MODEL_SHA256", "").lower()
    if model_url and expected_hash:
        if urlparse(model_url).scheme != "https":
            return None
        path = os.path.join(tempfile.gettempdir(), "adshield-model.json")
        cached = Path(path).read_bytes() if os.path.isfile(path) else b""
        if not cached or hashlib.sha256(cached).hexdigest() != expected_hash:
            try:
                with urllib.request.urlopen(model_url, timeout=15) as response:  # noqa: S310 - URL scheme is restricted to HTTPS above.
                    if urlparse(response.geturl()).scheme != "https":
                        return None
                    content = response.read(50 * 1024 * 1024 + 1)
                if len(content) > 50 * 1024 * 1024 or hashlib.sha256(content).hexdigest() != expected_hash:
                    return None
                with open(path, "wb") as artifact:
                    artifact.write(content)
            except (OSError, ValueError):
                return None
    if not os.path.isfile(path):
        return None
    try:
        from xgboost import XGBClassifier
    except ImportError:
        return None
    model = XGBClassifier()
    model.load_model(path)
    return model


_FEATURE_REASON = {
    "ip_click_count": "HIGH_FREQUENCY_IP", "click_interval": "RAPID_REPEAT",
    "ua_missing": "MISSING_UA", "ua_bot": "HEADLESS_UA",
    "subnet_click_count": "SUBNET_BURST", "ua_click_count": "UA_FLOOD",
}


def score(features: dict[str, float]) -> dict:
    model = _load_model()
    if model is None:
        risk = min(1.0, features["ip_click_count"] / 20.0 * 0.65 + features["ua_bot"] * 0.35)
        return {"score": risk, "model_version": "rules-only", "reason_codes": [], "degraded": True}
    import numpy as np
    import xgboost as xgb
    ordered = list(features)
    frame = xgb.DMatrix(np.asarray([[features[key] for key in ordered]], dtype=float), feature_names=ordered)
    booster = model.get_booster()
    probability = float(booster.predict(frame)[0])
    reasons: list[str] = []
    try:
        contributions = booster.predict(frame, pred_contribs=True)[0][:-1]
        reasons = [_FEATURE_REASON.get(ordered[i], ordered[i].upper())
                   for i in sorted(range(len(ordered)), key=lambda i: abs(float(contributions[i])), reverse=True)[:3]]
    except (AttributeError, ValueError, TypeError):
        reasons = []
    return {"score": probability, "model_version": os.getenv("MODEL_VERSION", "unknown"),
            "reason_codes": reasons, "degraded": False}
