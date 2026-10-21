import pytest
from app.services.decision import decide
from app.services.features import FEATURE_NAMES, build_features, training_features
from app.services.rules import rule_decision


def test_training_and_serving_features_share_the_same_contract():
    source = {"ip_click_count": 8, "click_interval": 2.5, "user_agent": "HeadlessChrome"}
    training = training_features(source)
    serving = build_features(ip_click_count=8, click_interval=2.5, user_agent="HeadlessChrome")
    assert tuple(training) == FEATURE_NAMES
    assert training == serving
    assert training["ua_bot"] == 1.0


def test_cost_sensitive_decision_boundaries(monkeypatch):
    monkeypatch.setenv("FRAUD_REVIEW_THRESHOLD", "0.3")
    monkeypatch.setenv("FRAUD_BLOCK_THRESHOLD", "0.7")
    assert decide(0.29) == "ALLOW"
    assert decide(0.3) == "REVIEW"
    assert decide(0.7) == "BLOCK"


def test_explicit_ip_rules_precede_model(monkeypatch):
    monkeypatch.setenv("IP_REVIEW_CLICK_THRESHOLD", "5")
    monkeypatch.setenv("IP_BLOCK_CLICK_THRESHOLD", "20")
    assert rule_decision(blocked=True)[0] == "BLOCK"
    assert rule_decision(whitelisted=True, blocked=False)[0] == "ALLOW"
    assert rule_decision(ip_click_count=5)[0] == "REVIEW"


def test_threshold_configuration_rejects_reversed_values(monkeypatch):
    monkeypatch.setenv("FRAUD_REVIEW_THRESHOLD", "0.8")
    monkeypatch.setenv("FRAUD_BLOCK_THRESHOLD", "0.4")
    with pytest.raises(ValueError):
        decide(0.5)
