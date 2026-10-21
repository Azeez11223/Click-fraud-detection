"""Cost-sensitive conversion from risk score to an action."""
from __future__ import annotations

import os


def decide(score: float) -> str:
    review = float(os.getenv("FRAUD_REVIEW_THRESHOLD", "0.35"))
    block = float(os.getenv("FRAUD_BLOCK_THRESHOLD", "0.75"))
    if not 0 <= review < block <= 1:
        raise ValueError("Thresholds must satisfy 0 <= review < block <= 1")
    if score >= block:
        return "BLOCK"
    if score >= review:
        return "REVIEW"
    return "ALLOW"
