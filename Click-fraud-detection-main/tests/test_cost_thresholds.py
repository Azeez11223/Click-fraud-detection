import pytest

from app.services.decision import decide
from app.services.economics import recommended_block_threshold, threshold_what_if


def test_cost_based_threshold_matches_expected_cost_ratio():
    assert recommended_block_threshold(1.0, 10.0, 0.1) == pytest.approx(0.5)


def test_campaign_threshold_override_controls_block_decision():
    assert decide(0.6, block_threshold=0.55) == "BLOCK"
    assert decide(0.6, block_threshold=0.7) == "REVIEW"


def test_historical_what_if_estimates_saved_spend_and_conversion_loss():
    rows = [
        {"classification": "FRAUD", "score": 0.9},
        {"classification": "VALID", "score": 0.8},
        {"classification": "VALID", "score": 0.2},
    ]
    result = threshold_what_if(rows, cpc=2, avg_conversion_value=50,
                               expected_conversion_rate=0.1, threshold=0.75)
    assert result["estimated_wasted_spend_saved"] == 2
    assert result["estimated_legitimate_conversions_lost"] == 0.1
    assert result["estimated_conversion_value_lost"] == 5


def test_campaign_cost_settings_are_owned(client, user_a, user_b):
    created = client.post("/campaigns", headers=user_a["headers"], json={
        "name": "Economics test", "ad_type": "Search", "platform": "Google", "purpose": "Sales",
        "cpc": 1.5, "avg_conversion_value": 30, "expected_conversion_rate": 0.1,
    })
    assert created.status_code == 200
    campaign_id = created.json()["campaign_id"]
    assert client.get(f"/campaigns/{campaign_id}/threshold-analysis", headers=user_a["headers"]).status_code == 200
    changed_costs = client.patch(f"/campaigns/{campaign_id}/economics", headers=user_a["headers"],
        json={"cpc": 2.25, "avg_conversion_value": 42, "expected_conversion_rate": 0.08})
    assert changed_costs.status_code == 200
    current = client.get(f"/campaigns/{campaign_id}", headers=user_a["headers"]).json()
    assert current["cpc"] == 2.25
    assert current["avg_conversion_value"] == 42
    assert current["expected_conversion_rate"] == 0.08
    saved = client.patch(f"/campaigns/{campaign_id}/block-threshold", headers=user_a["headers"],
                         json={"block_threshold": 0.62})
    assert saved.status_code == 200
    assert client.get(f"/campaigns/{campaign_id}/threshold-analysis", headers=user_b["headers"]).status_code == 404
    assert client.patch(f"/campaigns/{campaign_id}/block-threshold", headers=user_b["headers"],
                        json={"block_threshold": 0.9}).status_code == 404
