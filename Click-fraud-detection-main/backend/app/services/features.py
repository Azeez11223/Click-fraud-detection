"""Stable feature definitions shared by offline training and online scoring."""
from __future__ import annotations

FEATURE_NAMES = ("ip_click_count", "click_interval", "ua_missing", "ua_bot", "subnet_click_count", "ua_click_count")


def build_features(*, ip_click_count: int, click_interval: float, user_agent: str = "",
                   subnet_click_count: int = 0, ua_click_count: int = 0) -> dict[str, float]:
    ua = (user_agent or "").lower()
    bot_tokens = ("bot", "crawler", "spider", "headless", "phantom", "selenium", "curl", "python-requests")
    return {
        "ip_click_count": max(0, int(ip_click_count)),
        "click_interval": max(0.0, float(click_interval)),
        "ua_missing": float(not bool(user_agent.strip())),
        "ua_bot": float(any(token in ua for token in bot_tokens)),
        "subnet_click_count": max(0, int(subnet_click_count)),
        "ua_click_count": max(0, int(ua_click_count)),
    }


def training_features(row: dict) -> dict[str, float]:
    """Adapt a labelled dataset row to the online feature schema."""
    return build_features(
        ip_click_count=row.get("ip_click_count", 0),
        click_interval=row.get("click_interval", 0),
        user_agent=row.get("user_agent", ""),
        subnet_click_count=row.get("subnet_click_count", 0),
        ua_click_count=row.get("ua_click_count", 0),
    )
