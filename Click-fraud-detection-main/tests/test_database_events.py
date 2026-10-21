import uuid

import database


def test_campaign_click_event_is_idempotent_and_scored():
    suffix = uuid.uuid4().hex[:12]
    user_id = database.insert_user(f"Replay {suffix}", f"replay-{suffix}@example.test", "test-hash")
    campaign_id = database.insert_campaign(user_id, "Replay", "Display", "Google", "Traffic")
    first = database.insert_campaign_click(campaign_id, "192.0.2.4", "HeadlessChrome", user_id, "event-42")
    again = database.insert_campaign_click(campaign_id, "192.0.2.4", "HeadlessChrome", user_id, "event-42")
    assert first["id"] == again["id"]
    assert again["replayed"] is True
    stored = database.get_campaign_clicks(campaign_id)
    assert len(stored) == 1
    assert stored[0]["decision"] in {"ALLOW", "REVIEW", "BLOCK"}
    assert stored[0]["model_version"]
    assert database.delete_campaign(campaign_id, user_id)
    assert database.delete_user_data(user_id)


def test_audit_records_exclude_raw_ip_and_support_offset_pagination():
    suffix = uuid.uuid4().hex[:12]
    user_id = database.insert_user(f"Audit {suffix}", f"audit-{suffix}@example.test", "test-hash")
    database.record_audit_event(user_id, "ip_list.upsert", "ip_list_entry", "17",
                                {"list_type": "block"})
    rows = database.get_audit_events(limit=1, offset=0)
    assert rows[0]["actor_user_id"] == user_id
    assert rows[0]["action"] == "ip_list.upsert"
    assert "192.0.2." not in rows[0]["metadata"]
    assert database.delete_user_data(user_id)
