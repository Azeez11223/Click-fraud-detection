"""Delete expired raw event rows from PostgreSQL when explicitly configured."""
import os

import psycopg2


def purge():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for retention")
    days = max(1, int(os.getenv("RETENTION_DAYS", "90")))
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            removed = {}
            for table in ("campaign_clicks", "platform_events", "clicks_data", "predictions"):
                cur.execute(f"DELETE FROM {table} WHERE created_at < NOW() - (%s * INTERVAL '1 day')", (days,))
                removed[table] = cur.rowcount
    print(removed)

if __name__ == "__main__":
    purge()
