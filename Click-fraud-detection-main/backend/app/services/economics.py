"""Small, transparent campaign threshold and historical what-if calculations."""
from __future__ import annotations


def recommended_block_threshold(cpc: float, avg_conversion_value: float,
                                expected_conversion_rate: float) -> float:
    """Bayes threshold: C_fp / (C_fp + C_fn), with estimated false-positive/negative costs."""
    false_positive_cost = avg_conversion_value * expected_conversion_rate
    false_negative_cost = cpc
    total = false_positive_cost + false_negative_cost
    return false_positive_cost / total if total else 0.5


def threshold_what_if(clicks: list[dict], *, cpc: float, avg_conversion_value: float,
                      expected_conversion_rate: float, threshold: float) -> dict:
    """Estimate spend/conversion tradeoffs from historical model scores and stored labels."""
    fraud = [row for row in clicks if row.get("classification") == "FRAUD"]
    legit = [row for row in clicks if row.get("classification") == "VALID"]
    blocked_fraud = sum(float(row.get("score") or 0) >= threshold for row in fraud)
    blocked_legit = sum(float(row.get("score") or 0) >= threshold for row in legit)
    return {
        "threshold": threshold,
        "estimated_wasted_spend_saved": round(blocked_fraud * cpc, 2),
        "estimated_legitimate_conversions_lost": round(blocked_legit * expected_conversion_rate, 3),
        "estimated_conversion_value_lost": round(blocked_legit * expected_conversion_rate * avg_conversion_value, 2),
        "sample_size": len(clicks), "labelled_fraud_count": len(fraud),
        "labelled_legitimate_count": len(legit),
    }
