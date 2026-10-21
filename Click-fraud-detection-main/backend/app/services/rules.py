"""Deterministic policy rules, kept independent of the model."""
from __future__ import annotations

import os


def rule_decision(*, blocked: bool = False, whitelisted: bool = False,
                  ip_click_count: int = 0, ua_bot: bool = False) -> tuple[str | None, list[str]]:
    if blocked:
        return "BLOCK", ["ip_blocklisted"]
    if whitelisted:
        return "ALLOW", ["ip_allowlisted"]
    block_count = int(os.getenv("IP_BLOCK_CLICK_THRESHOLD", "20"))
    review_count = int(os.getenv("IP_REVIEW_CLICK_THRESHOLD", "5"))
    if ip_click_count >= block_count:
        return "BLOCK", ["ip_click_rate_high"]
    if ua_bot:
        return "REVIEW", ["automated_user_agent"]
    if ip_click_count >= review_count:
        return "REVIEW", ["ip_click_rate_elevated"]
    return None, []
