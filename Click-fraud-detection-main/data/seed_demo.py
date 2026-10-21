"""Seed one clearly labelled synthetic campaign for a local portfolio demo."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import database


DEMO_NAME = "[SYNTHETIC DEMO] Click review walkthrough"


def seed_demo(user_id: int) -> tuple[int, int]:
    database.init_db()
    if database.get_user_by_id(user_id) is None:
        raise ValueError(f"No local account found for user id {user_id}")

    existing = next((campaign for campaign in database.get_campaigns_by_user(user_id)
                     if campaign["name"] == DEMO_NAME), None)
    campaign_id = existing["id"] if existing else database.insert_campaign(
        user_id, DEMO_NAME, "Search", "Google", "Traffic")

    inserted = 0
    for index in range(8):
        result = database.insert_campaign_click(
            campaign_id, f"203.0.113.{index + 10}",
            "Mozilla/5.0 (Demo) Chrome/120.0", user_id,
            event_id=f"synthetic-demo-legit-{index}")
        inserted += not result["replayed"]

    for index in range(12):
        result = database.insert_campaign_click(
            campaign_id, "198.51.100.42", "Mozilla/5.0 HeadlessChrome/120.0 Bot",
            user_id, event_id=f"synthetic-demo-burst-{index}")
        inserted += not result["replayed"]

    return campaign_id, inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, type=int,
                        help="ID of the account you created in the local dashboard")
    args = parser.parse_args()
    campaign_id, inserted = seed_demo(args.user_id)
    print(f"Synthetic demo campaign id: {campaign_id}")
    print(f"New synthetic events inserted: {inserted}")
    print("Scenario: 8 reserved test-network addresses and 12 headless rapid-repeat events.")
    print("Stored classifications are detector outputs, not ground-truth labels or performance metrics.")
    print("Open Campaigns in the dashboard and select the [SYNTHETIC DEMO] campaign.")


if __name__ == "__main__":
    main()
