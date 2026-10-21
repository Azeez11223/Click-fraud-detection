"""
components/api.py — AdShield v3
All API helpers including new IP lists, datasets, and platform events.
Security fixes:
  - API_BASE from env/st.secrets (not hardcoded localhost)
  - Bare except replaced with specific exceptions
  - simulate_click removed (click ingest now requires X-API-Key, not browser-callable)
"""
import os
import requests
import streamlit as st

# API_BASE from st.secrets or env, with a sensible dev default
_DEFAULT_API = "http://localhost:8000"


def _get_api_base() -> str:
    """Resolve API base URL from Streamlit secrets or env var."""
    # Streamlit Community Cloud: st.secrets
    try:
        return st.secrets["API_BASE"]
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    # Fallback: env var
    return os.environ.get("API_BASE", _DEFAULT_API)


API_BASE = _get_api_base()


def _response_payload(response):
    """Decode JSON and keep a useful message for legacy Streamlit pages."""
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        payload = {"detail": "API returned an invalid response"}
    if isinstance(payload, dict) and "error" in payload:
        payload.setdefault("detail", payload["error"].get("message", "Request failed"))
    return payload


def get_auth_headers():
    t = st.session_state.get("token")
    return {"Authorization": f"Bearer {t}"} if t else {}


def _get(path, default=None, timeout=5, auth=False):
    try:
        headers = get_auth_headers() if auth else {}
        r = requests.get(f"{API_BASE}{path}", headers=headers, timeout=timeout)
        if auth and r.status_code == 401:
            st.session_state.token = None
            st.session_state.user = None
            return default
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return default
    except requests.exceptions.Timeout:
        return default
    except requests.exceptions.HTTPError:
        return default
    except requests.exceptions.RequestException:
        return default


def _post(path, payload=None, params=None, auth=False, timeout=10):
    try:
        headers = get_auth_headers() if auth else {}
        r = requests.post(
            f"{API_BASE}{path}",
            json=payload or {},
            params=params or {},
            headers=headers,
            timeout=timeout,
        )
        return _response_payload(r), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to API"}, 503
    except requests.exceptions.Timeout:
        return {"detail": "Request timed out"}, 504
    except requests.exceptions.RequestException as e:
        return {"detail": f"Request failed: {type(e).__name__}"}, 500


def _delete(path, auth=True, timeout=10):
    try:
        r = requests.delete(f"{API_BASE}{path}", headers=get_auth_headers(), timeout=timeout)
        return _response_payload(r), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to API"}, 503
    except requests.exceptions.Timeout:
        return {"detail": "Request timed out"}, 504
    except requests.exceptions.RequestException as e:
        return {"detail": f"Request failed: {type(e).__name__}"}, 500


def _patch(path, params=None, auth=True, timeout=10):
    try:
        r = requests.patch(
            f"{API_BASE}{path}",
            params=params or {},
            headers=get_auth_headers(),
            timeout=timeout,
        )
        return _response_payload(r), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to API"}, 503
    except requests.exceptions.Timeout:
        return {"detail": "Request timed out"}, 504
    except requests.exceptions.RequestException as e:
        return {"detail": f"Request failed: {type(e).__name__}"}, 500


def _patch_json(path, payload, timeout=10):
    try:
        r = requests.patch(f"{API_BASE}{path}", json=payload, headers=get_auth_headers(), timeout=timeout)
        return _response_payload(r), r.status_code
    except requests.exceptions.RequestException as e:
        return {"detail": f"Request failed: {type(e).__name__}"}, 503


# ── Auth ───────────────────────────────────────────────────────────────────────
def auth_signup(name, email, password):
    return _post("/auth/signup", {"name": name, "email": email, "password": password})


def auth_login(email, password):
    return _post("/auth/login", {"email": email, "password": password})


# ── Generic ────────────────────────────────────────────────────────────────────
def api_get(path, default=None, timeout=5):
    return _get(path, default, timeout)


def api_post(path, payload=None, params=None, timeout=10):
    return _post(path, payload, params, timeout=timeout)


def api_get_auth(path, default=None, timeout=5):
    return _get(path, default, timeout, auth=True)


def api_post_auth(path, payload=None, params=None, timeout=10):
    return _post(path, payload, params, auth=True, timeout=timeout)


def api_delete_auth(path, timeout=10):
    return _delete(path, timeout=timeout)


def api_patch_auth(path, params=None, timeout=10):
    return _patch(path, params, timeout=timeout)


@st.cache_data(ttl=15)
def check_api_health():
    """Check API health with short TTL cache."""
    return _get("/healthz", default=None) is not None


def get_stats():
    return api_get_auth("/stats", default={"total": 0, "fraud": 0, "legit": 0, "fraud_rate": 0})


def get_clicks(limit=200):
    return api_get_auth(f"/clicks?limit={limit}", default=[])


def get_metrics():
    return api_get_auth("/metrics", default={})


# ── Campaigns ──────────────────────────────────────────────────────────────────
def get_campaigns():
    return api_get_auth("/campaigns", default=[])


def create_campaign(name, ad_type, platform, purpose, cpc=0.50, avg_conversion_value=25.0,
                   expected_conversion_rate=0.02):
    return api_post_auth("/campaigns", {"name": name, "ad_type": ad_type, "platform": platform,
        "purpose": purpose, "cpc": cpc, "avg_conversion_value": avg_conversion_value,
        "expected_conversion_rate": expected_conversion_rate})


def get_campaign(cid):
    return api_get_auth(f"/campaigns/{cid}", default=None)


def delete_campaign_api(cid):
    return api_delete_auth(f"/campaigns/{cid}")


def update_campaign_status_api(cid, status):
    return api_patch_auth(f"/campaigns/{cid}/status", {"status": status})


def get_campaign_clicks_api(cid, limit=100):
    return api_get_auth(f"/campaigns/{cid}/clicks?limit={limit}", default=[])


def get_campaign_stats(cid):
    return api_get_auth(f"/campaigns/{cid}/stats", default={})


def get_threshold_analysis(cid, threshold=None):
    suffix = f"?threshold={threshold:.4f}" if threshold is not None else ""
    return api_get_auth(f"/campaigns/{cid}/threshold-analysis{suffix}", default={})


def update_campaign_economics(cid, cpc, avg_conversion_value, expected_conversion_rate):
    return _patch_json(f"/campaigns/{cid}/economics", {"cpc": cpc,
        "avg_conversion_value": avg_conversion_value, "expected_conversion_rate": expected_conversion_rate})


def set_campaign_block_threshold(cid, threshold):
    return _patch_json(f"/campaigns/{cid}/block-threshold", {"block_threshold": threshold})


def get_campaign_alerts(cid):
    return api_get_auth(f"/campaigns/{cid}/alerts", default=[])


# NOTE: simulate_click removed. Click ingest now requires X-API-Key header,
# not accessible from the browser UI. Use the campaign API key via curl/SDK.


# ── NEW v3: IP Lists ───────────────────────────────────────────────────────────
def get_ip_list(list_type=None):
    url = "/ip-lists"
    if list_type:
        url += f"?list_type={list_type}"
    return api_get_auth(url, default=[])


def get_ip_list_counts():
    return api_get_auth("/ip-lists/counts", default={"blocked": 0, "whitelisted": 0, "total": 0})


def add_ip(ip_address, list_type, note=""):
    return api_post_auth("/ip-lists", {"ip_address": ip_address, "list_type": list_type, "note": note})


def remove_ip(ip_address):
    return api_delete_auth(f"/ip-lists/{ip_address}")


# ── NEW v3: IP Datasets ────────────────────────────────────────────────────────
def get_ip_datasets():
    return api_get_auth("/ip-datasets", default=[])


def delete_ip_dataset(dataset_id):
    return api_delete_auth(f"/ip-datasets/{dataset_id}")


def upload_ip_dataset(file_bytes, filename, list_type):
    """Upload a file to /ip-datasets/upload using multipart form."""
    try:
        r = requests.post(
            f"{API_BASE}/ip-datasets/upload",
            files={"file": (filename, file_bytes)},
            data={"list_type": list_type},
            headers=get_auth_headers(),
            timeout=30,
        )
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to API"}, 503
    except requests.exceptions.Timeout:
        return {"detail": "Upload timed out"}, 504
    except requests.exceptions.RequestException as e:
        return {"detail": f"Upload failed: {type(e).__name__}"}, 500


# ── NEW v3: Platform Events ────────────────────────────────────────────────────
def send_platform_event(cid, platform, event_type, ip_address,
                        country="", device="", browser="", cost_usd=0.0):
    return api_post_auth(f"/campaigns/{cid}/platform-event", {
        "platform": platform, "event_type": event_type, "ip_address": ip_address,
        "country": country, "device": device, "browser": browser, "cost_usd": cost_usd,
    })


def get_platform_events_api(cid, limit=200, platform=None):
    url = f"/campaigns/{cid}/platform-events?limit={limit}"
    if platform:
        url += f"&platform={platform}"
    return api_get_auth(url, default=[])


def get_platform_stats(cid):
    return api_get_auth(f"/campaigns/{cid}/platform-stats", default=[])


def get_realtime_feed(cid, limit=30):
    return api_get_auth(f"/campaigns/{cid}/realtime-feed?limit={limit}", default=[])


def get_hourly_breakdown(cid, hours=24):
    return api_get_auth(f"/campaigns/{cid}/hourly-breakdown?hours={hours}", default=[])
