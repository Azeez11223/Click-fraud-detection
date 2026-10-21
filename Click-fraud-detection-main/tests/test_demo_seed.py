import database
from data.seed_demo import DEMO_NAME, seed_demo


def test_demo_seed_is_labelled_and_rerunnable(user_a):
    user_id = user_a["user"]["id"]
    campaign_id, inserted = seed_demo(user_id)
    again_id, second_inserted = seed_demo(user_id)

    assert campaign_id == again_id
    assert inserted == 20
    assert second_inserted == 0
    campaign = database.get_campaign_by_id(campaign_id, user_id)
    assert campaign["name"] == DEMO_NAME
    clicks = database.get_campaign_clicks(campaign_id, limit=30)
    assert len(clicks) == 20
    assert all(click["decision"] in {"ALLOW", "REVIEW", "BLOCK"} for click in clicks)
