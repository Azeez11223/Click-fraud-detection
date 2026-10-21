"""Small integration check run by CI after applying the Alembic schema."""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="Postgres integration requires DATABASE_URL"
)

def test_postgres_user_campaign_and_transaction_roundtrip():
    import database

    suffix = uuid.uuid4().hex[:12]
    user_id = database.insert_user(f"CI {suffix}", f"ci-{suffix}@example.test", "test-hash")
    assert user_id is not None
    campaign_id = database.insert_campaign(user_id, "CI campaign", "Display", "Google", "Traffic")
    assert campaign_id
    assert database.get_campaign_by_id(campaign_id, user_id)["name"] == "CI campaign"
    assert database.delete_campaign(campaign_id, user_id)
    conn = database.get_connection()
    try:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()
