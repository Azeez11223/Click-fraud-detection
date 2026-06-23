"""
components/api.py — AdShield v3
All API helpers including new IP lists, datasets, and platform events.
"""
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

def get_auth_headers():
    t = st.session_state.get("token")
    return {"Authorization": f"Bearer {t}"} if t else {}

def _get(path, default=None, timeout=5, auth=False):
    try:
        headers = get_auth_headers() if auth else {}
        r = requests.get(f"{API_BASE}{path}", headers=headers, timeout=timeout)
        if auth and r.status_code == 401:
            st.session_state.token = None; st.session_state.user = None; return default
        r.raise_for_status(); return r.json()
    except: return default

def _post(path, payload=None, params=None, auth=False, timeout=10):
    try:
        headers = get_auth_headers() if auth else {}
        r = requests.post(f"{API_BASE}{path}", json=payload or {}, params=params or {},
                          headers=headers, timeout=timeout)
        return r.json(), r.status_code
    except Exception as e: return {"detail": str(e)}, 500

def _delete(path, auth=True, timeout=10):
    try:
        r = requests.delete(f"{API_BASE}{path}", headers=get_auth_headers(), timeout=timeout)
        return r.json(), r.status_code
    except Exception as e: return {"detail": str(e)}, 500

def _patch(path, params=None, auth=True, timeout=10):
    try:
        r = requests.patch(f"{API_BASE}{path}", params=params or {}, headers=get_auth_headers(), timeout=timeout)
        return r.json(), r.status_code
    except Exception as e: return {"detail": str(e)}, 500

# ── Auth ───────────────────────────────────────────────────────────────────────
def auth_signup(name, email, password): return _post("/auth/signup", {"name":name,"email":email,"password":password})
def auth_login(email, password): return _post("/auth/login", {"email":email,"password":password})

# ── Generic ────────────────────────────────────────────────────────────────────
def api_get(path, default=None, timeout=5): return _get(path, default, timeout)
def api_post(path, payload=None, params=None, timeout=10): return _post(path, payload, params, timeout=timeout)
def api_get_auth(path, default=None, timeout=5): return _get(path, default, timeout, auth=True)
def api_post_auth(path, payload=None, params=None, timeout=10): return _post(path, payload, params, auth=True, timeout=timeout)
def api_delete_auth(path, timeout=10): return _delete(path, timeout=timeout)
def api_patch_auth(path, params=None, timeout=10): return _patch(path, params, timeout=timeout)

def check_api_health(): return _get("/", default=None) is not None
def get_stats(): return _get("/stats", default={"total":0,"fraud":0,"legit":0,"fraud_rate":0})
def get_clicks(limit=200): return _get(f"/clicks?limit={limit}", default=[])
def get_metrics(): return _get("/metrics", default={})

# ── Campaigns ──────────────────────────────────────────────────────────────────
def get_campaigns(): return api_get_auth("/campaigns", default=[])
def create_campaign(name, ad_type, platform, purpose):
    return api_post_auth("/campaigns", {"name":name,"ad_type":ad_type,"platform":platform,"purpose":purpose})
def get_campaign(cid): return api_get_auth(f"/campaigns/{cid}", default=None)
def delete_campaign_api(cid): return api_delete_auth(f"/campaigns/{cid}")
def update_campaign_status_api(cid, status): return api_patch_auth(f"/campaigns/{cid}/status", {"status":status})
def get_campaign_clicks_api(cid, limit=100): return api_get_auth(f"/campaigns/{cid}/clicks?limit={limit}", default=[])
def get_campaign_stats(cid): return api_get_auth(f"/campaigns/{cid}/stats", default={})
def get_campaign_alerts(cid): return api_get_auth(f"/campaigns/{cid}/alerts", default=[])
def simulate_click(cid, ip_address, user_agent=""): return api_post(f"/campaigns/{cid}/click", {"ip_address":ip_address,"user_agent":user_agent})

# ── NEW v3: IP Lists ───────────────────────────────────────────────────────────
def get_ip_list(list_type=None):
    url = "/ip-lists"
    if list_type: url += f"?list_type={list_type}"
    return api_get_auth(url, default=[])

def get_ip_list_counts(): return api_get_auth("/ip-lists/counts", default={"blocked":0,"whitelisted":0,"total":0})

def add_ip(ip_address, list_type, note=""):
    return api_post_auth("/ip-lists", {"ip_address":ip_address,"list_type":list_type,"note":note})

def remove_ip(ip_address): return api_delete_auth(f"/ip-lists/{ip_address}")

# ── NEW v3: IP Datasets ────────────────────────────────────────────────────────
def get_ip_datasets(): return api_get_auth("/ip-datasets", default=[])

def delete_ip_dataset(dataset_id): return api_delete_auth(f"/ip-datasets/{dataset_id}")

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
    except Exception as e:
        return {"detail": str(e)}, 500

# ── NEW v3: Platform Events ────────────────────────────────────────────────────
def send_platform_event(cid, platform, event_type, ip_address,
                        country="", device="", browser="", cost_usd=0.0):
    return api_post_auth(f"/campaigns/{cid}/platform-event", {
        "platform":platform,"event_type":event_type,"ip_address":ip_address,
        "country":country,"device":device,"browser":browser,"cost_usd":cost_usd,
    })

def get_platform_events_api(cid, limit=200, platform=None):
    url = f"/campaigns/{cid}/platform-events?limit={limit}"
    if platform: url += f"&platform={platform}"
    return api_get_auth(url, default=[])

def get_platform_stats(cid): return api_get_auth(f"/campaigns/{cid}/platform-stats", default=[])

def get_realtime_feed(cid, limit=30):
    return api_get_auth(f"/campaigns/{cid}/realtime-feed?limit={limit}", default=[])

def get_hourly_breakdown(cid, hours=24):
    return api_get_auth(f"/campaigns/{cid}/hourly-breakdown?hours={hours}", default=[])
