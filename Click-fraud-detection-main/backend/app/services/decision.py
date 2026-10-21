"""Cost-sensitive conversion from risk score to an action."""
from __future__ import annotations

import os


def decide(score: float, block_threshold: float | None = None) -> str:
    review = float(os.getenv("FRAUD_REVIEW_THRESHOLD", "0.35"))
    block = float(block_threshold if block_threshold is not None else os.getenv("FRAUD_BLOCK_THRESHOLD", "0.75"))
    if block_threshold is not None:
        review = min(review, max(0.0, block - 0.01))
    if not 0 <= review < block <= 1:
        raise ValueError("Thresholds must satisfy 0 <= review < block <= 1")
    if score >= block:
        return "BLOCK"
    if score >= review:
        return "REVIEW"
    return "ALLOW"
