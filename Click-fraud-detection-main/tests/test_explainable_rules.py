import pytest

from app.services.rules import rule_decision


@pytest.mark.parametrize(("kwargs", "expected"), [
    ({"blocked": True}, "BLOCKLISTED_IP"),
    ({"ip_click_count": 20}, "HIGH_FREQUENCY_IP"),
    ({"click_interval": 0.5}, "RAPID_REPEAT"),
    ({"ua_bot": True}, "HEADLESS_UA"),
    ({"ua_click_count": 15}, "UA_FLOOD"),
    ({"datacenter_ip": True}, "DATACENTER_IP"),
])
def test_rule_reason_codes(kwargs, expected):
    _, reasons = rule_decision(**kwargs)
    assert reasons == [expected]
