"""Deterministic policy rules, kept independent of the model."""
from __future__ import annotations

import os


def rule_decision(*, blocked: bool = False, whitelisted: bool = False,
                  ip_click_count: int = 0, ua_bot: bool = False,
                  click_interval: float = 0.0, ua_click_count: int = 0,
                  datacenter_ip: bool = False) -> tuple[str | None, list[str]]:
    if blocked:
        return "BLOCK", ["BLOCKLISTED_IP"]
    if whitelisted:
        return "ALLOW", ["ALLOWLISTED_IP"]
    if datacenter_ip:
        return "REVIEW", ["DATACENTER_IP"]
    block_count = int(os.getenv("IP_BLOCK_CLICK_THRESHOLD", "20"))
    review_count = int(os.getenv("IP_REVIEW_CLICK_THRESHOLD", "5"))
    if ip_click_count >= block_count:
        return "BLOCK", ["HIGH_FREQUENCY_IP"]
    if click_interval > 0 and click_interval < 2:
        return "REVIEW", ["RAPID_REPEAT"]
    if ua_click_count >= max(1, int(os.getenv("UA_REVIEW_10MIN_THRESHOLD", "15"))):
        return "REVIEW", ["UA_FLOOD"]
    if ua_bot:
        return "REVIEW", ["HEADLESS_UA"]
    if ip_click_count >= review_count:
        return "REVIEW", ["HIGH_FREQUENCY_IP"]
    return None, []
