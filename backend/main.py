"""
main.py — AdShield v3
FastAPI backend with:
  - All existing endpoints
  - NEW: IP list management (block/whitelist)
  - NEW: IP dataset upload
  - NEW: Platform events (Google / Facebook simulation + real integration hooks)
  - NEW: Realtime feed endpoint
"""
import os, sys, json, io
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, os.path.dirname(__file__))
from database import (
    init_db, insert_click, insert_prediction, get_recent_predictions, get_prediction_stats,
    insert_user, get_user_by_email,
    insert_campaign, get_campaigns_by_user, get_campaign_by_id, update_campaign_status, delete_campaign,
    insert_campaign_click, get_campaign_clicks, get_campaign_click_stats, check_campaign_alerts,
    # NEW v3
    upsert_ip, delete_ip, get_ip_list, get_ip_list_counts,
    insert_ip_dataset, get_ip_datasets, delete_ip_dataset,
    insert_platform_event, get_platform_events, get_platform_stats,
    get_realtime_feed, get_hourly_platform_breakdown,
)
from model import train_model, predict_single, get_metrics
from auth import hash_password, verify_password, create_access_token, get_current_user

app = FastAPI(title="AdShield API v3", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): init_db()

# ── Schemas (existing) ─────────────────────────────────────────────────────────
class ClickRequest(BaseModel):
    ip_address: str; device_type: str; browser: str; timestamp: str
    click_interval: float = Field(..., ge=0); ip_click_count: int = Field(..., ge=0)
    geo_location: str
    @field_validator("device_type")
    @classmethod
    def val_device(cls,v):
        if v.lower() not in {"mobile","desktop","tablet"}: raise ValueError("bad device")
        return v.lower()
    @field_validator("browser")
    @classmethod
    def val_browser(cls,v):
        if v.lower() not in {"chrome","firefox","safari","edge","opera"}: raise ValueError("bad browser")
        return v.capitalize()

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1); email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)

class LoginRequest(BaseModel):
    email: str; password: str

class CampaignRequest(BaseModel):
    name: str = Field(..., min_length=1); ad_type: str; platform: str; purpose: str
    @field_validator("ad_type")
    @classmethod
    def val_ad(cls,v):
        if v.lower() not in {"display","video","search","social"}: raise ValueError("bad ad_type")
        return v.capitalize()
    @field_validator("platform")
    @classmethod
    def val_plat(cls,v):
        if v.lower() not in {"google","facebook","instagram"}: raise ValueError("bad platform")
        return v.capitalize()
    @field_validator("purpose")
    @classmethod
    def val_purp(cls,v):
        if v.lower() not in {"traffic","sales","awareness"}: raise ValueError("bad purpose")
        return v.capitalize()

class CampaignClickRequest(BaseModel):
    ip_address: str; user_agent: str = ""

# ── NEW v3 Schemas ─────────────────────────────────────────────────────────────
class IPEntryRequest(BaseModel):
    ip_address: str = Field(..., example="203.45.67.89")
    list_type: str = Field(..., example="block")
    note: str = ""
    @field_validator("list_type")
    @classmethod
    def val_lt(cls,v):
        if v not in {"block","whitelist"}: raise ValueError("list_type must be 'block' or 'whitelist'")
        return v

class PlatformEventRequest(BaseModel):
    platform: str; event_type: str = "click"
    ip_address: str; country: str = ""; device: str = ""; browser: str = ""
    cost_usd: float = 0.0
    @field_validator("platform")
    @classmethod
    def val_plat(cls,v):
        if v.lower() not in {"google","facebook"}: raise ValueError("platform must be google or facebook")
        return v.capitalize()

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root(): return {"status":"running","api":"AdShield v3.0"}

# ── Prediction ─────────────────────────────────────────────────────────────────
@app.post("/predict", tags=["Prediction"])
def predict(click: ClickRequest):
    record = click.model_dump()
    try: result = predict_single(record)
    except FileNotFoundError as e: raise HTTPException(503, str(e))
    except Exception as e: raise HTTPException(500, f"Prediction error: {e}")
    try:
        insert_click(click.ip_address,click.device_type,click.browser,click.geo_location,
                     click.timestamp,click.click_interval,click.ip_click_count)
        insert_prediction(click.ip_address,result["prediction"],result["confidence"])
    except Exception as e: print(f"[WARN] DB: {e}")
    return result

@app.post("/train", tags=["Model"])
def train(use_smote: bool = Query(default=False)):
    try: return {"status":"trained","metrics":train_model(use_smote=use_smote)}
    except FileNotFoundError as e: raise HTTPException(404, str(e))
    except Exception as e: raise HTTPException(500, f"Training error: {e}")

@app.get("/metrics", tags=["Model"])
def metrics(): return get_metrics()

@app.get("/clicks", tags=["Data"])
def recent_clicks(limit: int = Query(default=50, le=200)): return get_recent_predictions(limit)

@app.get("/stats", tags=["Data"])
def fraud_stats(): return get_prediction_stats()

# ── Auth ───────────────────────────────────────────────────────────────────────
@app.post("/auth/signup", tags=["Auth"])
def signup(req: SignupRequest):
    hashed = hash_password(req.password)
    uid = insert_user(req.name, req.email, hashed)
    if uid is None: raise HTTPException(409, "Email already registered")
    return {"message":"Account created","user_id":uid}

@app.post("/auth/login", tags=["Auth"])
def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token({"user_id":user["id"],"email":user["email"],"name":user["name"]})
    return {"access_token":token,"token_type":"bearer",
            "user":{"id":user["id"],"name":user["name"],"email":user["email"]}}

@app.get("/auth/me", tags=["Auth"])
def me(user=Depends(get_current_user)): return user

# ── Campaigns ──────────────────────────────────────────────────────────────────
@app.get("/campaigns", tags=["Campaigns"])
def list_campaigns(user=Depends(get_current_user)): return get_campaigns_by_user(user["user_id"])

@app.post("/campaigns", tags=["Campaigns"])
def create_campaign(req: CampaignRequest, user=Depends(get_current_user)):
    cid = insert_campaign(user["user_id"],req.name,req.ad_type,req.platform,req.purpose)
    return {"message":"Campaign created","campaign_id":cid}

@app.get("/campaigns/{campaign_id}", tags=["Campaigns"])
def get_campaign(campaign_id: int, user=Depends(get_current_user)):
    c = get_campaign_by_id(campaign_id, user["user_id"])
    if not c: raise HTTPException(404,"Campaign not found")
    return c

@app.delete("/campaigns/{campaign_id}", tags=["Campaigns"])
def del_campaign(campaign_id: int, user=Depends(get_current_user)):
    delete_campaign(campaign_id, user["user_id"]); return {"message":"Campaign deleted"}

@app.patch("/campaigns/{campaign_id}/status", tags=["Campaigns"])
def upd_status(campaign_id: int, status: str = Query(...), user=Depends(get_current_user)):
    if status not in {"Active","Paused","Completed"}: raise HTTPException(400,"bad status")
    if not get_campaign_by_id(campaign_id, user["user_id"]): raise HTTPException(404,"not found")
    update_campaign_status(campaign_id, status); return {"message":f"Status → {status}"}

@app.post("/campaigns/{campaign_id}/click", tags=["Campaign Clicks"])
def record_click(campaign_id: int, req: CampaignClickRequest):
    if not get_campaign_by_id(campaign_id): raise HTTPException(404,"Campaign not found")
    return insert_campaign_click(campaign_id, req.ip_address, req.user_agent)

@app.get("/campaigns/{campaign_id}/clicks", tags=["Campaign Clicks"])
def get_clicks(campaign_id: int, limit: int = Query(100,le=500), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]): raise HTTPException(404,"not found")
    return get_campaign_clicks(campaign_id, limit)

@app.get("/campaigns/{campaign_id}/stats", tags=["Campaign Clicks"])
def get_stats(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]): raise HTTPException(404,"not found")
    return get_campaign_click_stats(campaign_id)

@app.get("/campaigns/{campaign_id}/alerts", tags=["Campaign Clicks"])
def get_alerts(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]): raise HTTPException(404,"not found")
    return check_campaign_alerts(campaign_id)

# ══════════════════════════════════════════════════════════════════════════════
#  NEW v3 — IP List endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/ip-lists", tags=["IP Lists"])
def list_ips(list_type: Optional[str]=None, user=Depends(get_current_user)):
    """Return all blocked/whitelisted IPs for the current user."""
    return get_ip_list(user["user_id"], list_type)

@app.get("/ip-lists/counts", tags=["IP Lists"])
def ip_counts(user=Depends(get_current_user)):
    return get_ip_list_counts(user["user_id"])

@app.post("/ip-lists", tags=["IP Lists"])
def add_ip(req: IPEntryRequest, user=Depends(get_current_user)):
    rid = upsert_ip(user["user_id"], req.ip_address, req.list_type, req.note)
    return {"message":"IP added","id":rid,"ip":req.ip_address,"list_type":req.list_type}

@app.delete("/ip-lists/{ip_address:path}", tags=["IP Lists"])
def remove_ip(ip_address: str, user=Depends(get_current_user)):
    delete_ip(user["user_id"], ip_address)
    return {"message":f"IP {ip_address} removed"}

# ══════════════════════════════════════════════════════════════════════════════
#  NEW v3 — IP Dataset upload endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/ip-datasets/upload", tags=["IP Datasets"])
async def upload_dataset(
    file: UploadFile = File(...),
    list_type: str = Form(...),
    user=Depends(get_current_user),
):
    """Upload a CSV, JSON, or TXT file of IP addresses."""
    if list_type not in {"block","whitelist","training"}:
        raise HTTPException(400, "list_type must be block, whitelist, or training")

    content = await file.read()
    filename = file.filename or "upload"
    ips = []

    try:
        text = content.decode("utf-8", errors="ignore")
        ext  = filename.rsplit(".",1)[-1].lower()

        if ext == "json":
            data = json.loads(text)
            if isinstance(data, list):
                ips = [str(x).strip() for x in data if x]
            elif isinstance(data, dict):
                ips = [str(v).strip() for v in data.values() if v]
        elif ext == "csv":
            lines = text.splitlines()
            for line in lines:
                # Try first column; skip header rows that don't look like IPs
                cell = line.split(",")[0].strip().strip('"')
                if cell and cell[0].isdigit():
                    ips.append(cell)
        else:
            # Plain text: one IP per line
            ips = [ln.strip() for ln in text.splitlines() if ln.strip()]

    except Exception as e:
        raise HTTPException(400, f"Could not parse file: {e}")

    if not ips:
        raise HTTPException(400, "No valid IPs found in file")

    dataset_id, inserted, skipped = insert_ip_dataset(user["user_id"], filename, list_type, ips)
    return {
        "message": "Dataset uploaded",
        "dataset_id": dataset_id,
        "total_ips": len(ips),
        "inserted_to_list": inserted,
        "skipped": skipped,
    }

@app.get("/ip-datasets", tags=["IP Datasets"])
def list_datasets(user=Depends(get_current_user)):
    return get_ip_datasets(user["user_id"])

@app.delete("/ip-datasets/{dataset_id}", tags=["IP Datasets"])
def del_dataset(dataset_id: int, user=Depends(get_current_user)):
    delete_ip_dataset(dataset_id, user["user_id"])
    return {"message":"Dataset deleted and IPs removed from list"}

# ══════════════════════════════════════════════════════════════════════════════
#  NEW v3 — Platform Events (Google / Facebook)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/campaigns/{campaign_id}/platform-event", tags=["Platform"])
def platform_event(campaign_id: int, req: PlatformEventRequest, user=Depends(get_current_user)):
    """Record a Google / Facebook ad event for a campaign."""
    campaign = get_campaign_by_id(campaign_id, user["user_id"])
    if not campaign: raise HTTPException(404, "Campaign not found")
    return insert_platform_event(
        campaign_id=campaign_id, platform=req.platform, event_type=req.event_type,
        ip_address=req.ip_address, country=req.country, device=req.device,
        browser=req.browser, cost_usd=req.cost_usd, user_id=user["user_id"],
    )

@app.get("/campaigns/{campaign_id}/platform-events", tags=["Platform"])
def list_platform_events(campaign_id: int, limit: int=Query(200,le=500),
                         platform: Optional[str]=None, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]): raise HTTPException(404,"not found")
    return get_platform_events(campaign_id, limit, platform)

@app.get("/campaigns/{campaign_id}/platform-stats", tags=["Platform"])
def plat_stats(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]): raise HTTPException(404,"not found")
    return get_platform_stats(campaign_id)

@app.get("/campaigns/{campaign_id}/realtime-feed", tags=["Platform"])
def realtime(campaign_id: int, limit: int=Query(30,le=100), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]): raise HTTPException(404,"not found")
    return get_realtime_feed(campaign_id, limit)

@app.get("/campaigns/{campaign_id}/hourly-breakdown", tags=["Platform"])
def hourly(campaign_id: int, hours: int=Query(24,le=168), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]): raise HTTPException(404,"not found")
    return get_hourly_platform_breakdown(campaign_id, hours)
