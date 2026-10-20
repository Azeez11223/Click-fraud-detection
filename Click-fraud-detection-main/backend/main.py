"""
main.py — AdShield v3
FastAPI backend with security hardening:
  - JWT required on all data endpoints
  - /train is admin-only and disabled in production
  - /campaigns/{id}/click requires X-API-Key, derives IP from request.client.host
  - Rate limiting on auth endpoints via slowapi
  - IP validation on all inputs
  - CORS origins from env (no wildcard in production)
  - /docs disabled in production
"""
import os
import sys
import json
import ipaddress as _ipaddress
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

sys.path.insert(0, os.path.dirname(__file__))
from database import (
    init_db, insert_click, insert_prediction, get_recent_predictions, get_prediction_stats,
    insert_user, get_user_by_email, get_user_by_id,
    insert_campaign, get_campaigns_by_user, get_campaign_by_id, update_campaign_status, delete_campaign,
    insert_campaign_click, get_campaign_clicks, get_campaign_click_stats, check_campaign_alerts,
    get_campaign_owner_id, validate_ip,
    # NEW v3
    upsert_ip, delete_ip, get_ip_list, get_ip_list_counts,
    insert_ip_dataset, get_ip_datasets, delete_ip_dataset,
    insert_platform_event, get_platform_events, get_platform_stats,
    get_realtime_feed, get_hourly_platform_breakdown,
)
from model import predict_single, get_metrics
from auth import (
    hash_password, verify_password, create_access_token, get_current_user,
    get_admin_user, validate_jwt_config,
    generate_api_key, hash_api_key, verify_api_key,
)

# ── Environment ────────────────────────────────────────────────────────────────
ENV = os.environ.get("ENV", "development")
IS_PRODUCTION = ENV.lower() == "production"
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:8501").split(",")
    if o.strip()
]

# Max upload size for IP datasets (bytes)
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_UPLOAD_ROWS = 50_000

# ── App setup ──────────────────────────────────────────────────────────────────
app_kwargs = {"title": "AdShield API v3", "version": "3.0.0"}
if IS_PRODUCTION:
    # Disable interactive docs in production
    app_kwargs.update({"docs_url": None, "redoc_url": None, "openapi_url": None})

app = FastAPI(**app_kwargs)

# Rate limiter (in-memory, single instance — works without Redis)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    allow_credentials=True,
)


@app.on_event("startup")
def startup():
    validate_jwt_config()
    init_db()


# ── Schemas ────────────────────────────────────────────────────────────────────
class ClickRequest(BaseModel):
    ip_address: str
    device_type: str
    browser: str
    timestamp: str
    click_interval: float = Field(..., ge=0)
    ip_click_count: int = Field(..., ge=0)
    geo_location: str

    @field_validator("ip_address")
    @classmethod
    def val_ip(cls, v):
        try:
            _ipaddress.ip_address(v.strip())
        except ValueError:
            raise ValueError("Invalid IP address")
        return v.strip()

    @field_validator("device_type")
    @classmethod
    def val_device(cls, v):
        if v.lower() not in {"mobile", "desktop", "tablet"}:
            raise ValueError("bad device")
        return v.lower()

    @field_validator("browser")
    @classmethod
    def val_browser(cls, v):
        # Normalize unknown browsers to "Other" instead of rejecting with 422
        known = {"chrome", "firefox", "safari", "edge", "opera"}
        if v.lower() not in known:
            return "Other"
        return v.capitalize()


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CampaignRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    ad_type: str
    platform: str
    purpose: str

    @field_validator("ad_type")
    @classmethod
    def val_ad(cls, v):
        if v.lower() not in {"display", "video", "search", "social"}:
            raise ValueError("bad ad_type")
        return v.capitalize()

    @field_validator("platform")
    @classmethod
    def val_plat(cls, v):
        if v.lower() not in {"google", "facebook", "instagram"}:
            raise ValueError("bad platform")
        return v.capitalize()

    @field_validator("purpose")
    @classmethod
    def val_purp(cls, v):
        if v.lower() not in {"traffic", "sales", "awareness"}:
            raise ValueError("bad purpose")
        return v.capitalize()


class CampaignClickRequest(BaseModel):
    """Click ingest schema — IP is derived from request.client.host, not from body."""
    user_agent: str = ""


# ── NEW v3 Schemas ─────────────────────────────────────────────────────────────
class IPEntryRequest(BaseModel):
    ip_address: str = Field(..., examples=["203.45.67.89"])
    list_type: str = Field(..., examples=["block"])
    note: str = ""

    @field_validator("ip_address")
    @classmethod
    def val_ip(cls, v):
        try:
            _ipaddress.ip_address(v.strip())
        except ValueError:
            raise ValueError("Invalid IP address")
        return v.strip()

    @field_validator("list_type")
    @classmethod
    def val_lt(cls, v):
        if v not in {"block", "whitelist"}:
            raise ValueError("list_type must be 'block' or 'whitelist'")
        return v


class PlatformEventRequest(BaseModel):
    platform: str
    event_type: str = "click"
    ip_address: str
    country: str = ""
    device: str = ""
    browser: str = ""
    cost_usd: float = 0.0

    @field_validator("ip_address")
    @classmethod
    def val_ip(cls, v):
        try:
            _ipaddress.ip_address(v.strip())
        except ValueError:
            raise ValueError("Invalid IP address")
        return v.strip()

    @field_validator("platform")
    @classmethod
    def val_plat(cls, v):
        if v.lower() not in {"google", "facebook"}:
            raise ValueError("platform must be google or facebook")
        return v.capitalize()


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "running", "api": "AdShield v3.0"}


@app.get("/healthz", tags=["Health"])
def healthz():
    """Liveness probe — no DB call."""
    return {"status": "ok"}


# ── Prediction ─────────────────────────────────────────────────────────────────
@app.post("/predict", tags=["Prediction"])
def predict(click: ClickRequest, user=Depends(get_current_user)):
    record = click.model_dump()
    try:
        result = predict_single(record)
    except FileNotFoundError as e:
        raise HTTPException(503, "Model not available")
    except Exception:
        raise HTTPException(500, "Prediction error")

    try:
        insert_click(
            click.ip_address, click.device_type, click.browser, click.geo_location,
            click.timestamp, click.click_interval, click.ip_click_count, user_id=user["user_id"],
        )
        insert_prediction(click.ip_address, result["prediction"], result["confidence"], user_id=user["user_id"])
    except Exception as e:
        # Log but don't swallow — return the prediction but note the DB error
        print(f"[ERROR] DB write failed in /predict: {e}")

    return result


@app.get("/metrics", tags=["Model"])
def metrics(user=Depends(get_current_user)):
    return get_metrics()


@app.get("/clicks", tags=["Data"])
def recent_clicks(limit: int = Query(default=50, le=200), user=Depends(get_current_user)):
    return get_recent_predictions(limit, user_id=user["user_id"])


@app.get("/stats", tags=["Data"])
def fraud_stats(user=Depends(get_current_user)):
    return get_prediction_stats(user_id=user["user_id"])


# ── Train (admin-only, disabled in production) ────────────────────────────────
@app.post("/train", tags=["Model"])
def train(use_smote: bool = Query(default=False), user=Depends(get_admin_user)):
    if IS_PRODUCTION:
        raise HTTPException(403, "Training is disabled in production. Use offline training pipeline.")
    # Import here to avoid loading training deps in production
    from model import train_model
    try:
        return {"status": "trained", "metrics": train_model(use_smote=use_smote)}
    except FileNotFoundError as e:
        raise HTTPException(404, "Dataset not found")
    except Exception:
        raise HTTPException(500, "Training error")


# ── Auth ───────────────────────────────────────────────────────────────────────
@app.post("/auth/signup", tags=["Auth"])
@limiter.limit("5/minute")
def signup(req: SignupRequest, request: Request):
    hashed = hash_password(req.password)
    uid = insert_user(req.name, req.email, hashed)
    if uid is None:
        raise HTTPException(409, "Email already registered")
    return {"message": "Account created", "user_id": uid}


@app.post("/auth/login", tags=["Auth"])
@limiter.limit("5/minute")
def login(req: LoginRequest, request: Request):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token(user["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
    }


@app.get("/auth/me", tags=["Auth"])
def me(user=Depends(get_current_user)):
    db_user = get_user_by_id(user["user_id"])
    if not db_user:
        raise HTTPException(404, "User not found")
    return db_user


# ── Campaigns ──────────────────────────────────────────────────────────────────
@app.get("/campaigns", tags=["Campaigns"])
def list_campaigns(user=Depends(get_current_user)):
    return get_campaigns_by_user(user["user_id"])


@app.post("/campaigns", tags=["Campaigns"])
def create_campaign(req: CampaignRequest, user=Depends(get_current_user)):
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    cid = insert_campaign(user["user_id"], req.name, req.ad_type, req.platform, req.purpose, api_key_hash=key_hash)
    return {
        "message": "Campaign created",
        "campaign_id": cid,
        "api_key": raw_key,
        "note": "Save this API key — it will not be shown again.",
    }


@app.get("/campaigns/{campaign_id}", tags=["Campaigns"])
def get_campaign_detail(campaign_id: int, user=Depends(get_current_user)):
    c = get_campaign_by_id(campaign_id, user["user_id"])
    if not c:
        raise HTTPException(404, "Campaign not found")
    return c


@app.delete("/campaigns/{campaign_id}", tags=["Campaigns"])
def del_campaign(campaign_id: int, user=Depends(get_current_user)):
    deleted = delete_campaign(campaign_id, user["user_id"])
    if not deleted:
        raise HTTPException(404, "Campaign not found or not owned by you")
    return {"message": "Campaign deleted"}


@app.patch("/campaigns/{campaign_id}/status", tags=["Campaigns"])
def upd_status(campaign_id: int, status: str = Query(...), user=Depends(get_current_user)):
    if status not in {"Active", "Paused", "Completed"}:
        raise HTTPException(400, "bad status")
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    update_campaign_status(campaign_id, status)
    return {"message": f"Status → {status}"}


# ── Campaign Click Ingest (API-key authenticated) ─────────────────────────────
def _get_campaign_api_key(request: Request) -> str:
    """Extract X-API-Key header."""
    key = request.headers.get("X-API-Key")
    if not key:
        raise HTTPException(401, "X-API-Key header required")
    return key


@app.post("/campaigns/{campaign_id}/click", tags=["Campaign Clicks"])
@limiter.limit("60/minute")
def record_click(campaign_id: int, req: CampaignClickRequest, request: Request):
    """Record a campaign click.
    - Requires X-API-Key header matching the campaign's API key.
    - IP is derived from request.client.host (not from the request body).
    - Block/whitelist enforcement uses the campaign owner's user_id.
    """
    api_key = _get_campaign_api_key(request)
    campaign_info = get_campaign_owner_id(campaign_id)
    if not campaign_info:
        raise HTTPException(404, "Campaign not found")

    stored_hash = campaign_info.get("api_key_hash")
    if not stored_hash or not verify_api_key(api_key, stored_hash):
        raise HTTPException(401, "Invalid API key")

    # Derive IP from the actual network connection
    client_ip = request.client.host if request.client else "0.0.0.0"
    owner_user_id = campaign_info["user_id"]

    return insert_campaign_click(campaign_id, client_ip, req.user_agent, user_id=owner_user_id)


@app.get("/campaigns/{campaign_id}/clicks", tags=["Campaign Clicks"])
def get_clicks(campaign_id: int, limit: int = Query(100, le=500), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_campaign_clicks(campaign_id, limit)


@app.get("/campaigns/{campaign_id}/stats", tags=["Campaign Clicks"])
def get_stats(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_campaign_click_stats(campaign_id)


@app.get("/campaigns/{campaign_id}/alerts", tags=["Campaign Clicks"])
def get_alerts(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return check_campaign_alerts(campaign_id)


# ══════════════════════════════════════════════════════════════════════════════
#  NEW v3 — IP List endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/ip-lists", tags=["IP Lists"])
def list_ips(list_type: Optional[str] = None, user=Depends(get_current_user)):
    """Return all blocked/whitelisted IPs for the current user."""
    return get_ip_list(user["user_id"], list_type)


@app.get("/ip-lists/counts", tags=["IP Lists"])
def ip_counts(user=Depends(get_current_user)):
    return get_ip_list_counts(user["user_id"])


@app.post("/ip-lists", tags=["IP Lists"])
def add_ip_entry(req: IPEntryRequest, user=Depends(get_current_user)):
    rid = upsert_ip(user["user_id"], req.ip_address, req.list_type, req.note)
    return {"message": "IP added", "id": rid, "ip": req.ip_address, "list_type": req.list_type}


@app.delete("/ip-lists/{ip_address:path}", tags=["IP Lists"])
def remove_ip_entry(ip_address: str, user=Depends(get_current_user)):
    delete_ip(user["user_id"], ip_address)
    return {"message": f"IP {ip_address} removed"}


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
    if list_type not in {"block", "whitelist", "training"}:
        raise HTTPException(400, "list_type must be block, whitelist, or training")

    # Validate content type (reject binary files)
    content_type = file.content_type or ""
    if content_type and not any(t in content_type for t in ["text", "json", "csv", "octet-stream"]):
        raise HTTPException(400, "Unsupported file type. Use CSV, JSON, or TXT.")

    content = await file.read()

    # Enforce size limit
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, f"File too large. Maximum {MAX_UPLOAD_BYTES // (1024*1024)} MB.")

    filename = file.filename or "upload"
    ips = []

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be valid UTF-8 text")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    try:
        if ext == "json":
            data = json.loads(text)
            if isinstance(data, list):
                ips = [str(x).strip() for x in data if x]
            elif isinstance(data, dict):
                ips = [str(v).strip() for v in data.values() if v]
            else:
                raise HTTPException(400, "JSON must be an array or object")
        elif ext == "csv":
            lines = text.splitlines()
            for line in lines:
                cell = line.split(",")[0].strip().strip('"')
                if cell and cell[0].isdigit():
                    ips.append(cell)
        else:
            # Plain text: one IP per line
            ips = [ln.strip() for ln in text.splitlines() if ln.strip()]
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON file")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Could not parse file")

    if not ips:
        raise HTTPException(400, "No valid IPs found in file")

    # Enforce row limit
    if len(ips) > MAX_UPLOAD_ROWS:
        raise HTTPException(400, f"Too many IPs. Maximum {MAX_UPLOAD_ROWS:,} rows per upload.")

    dataset_id, inserted, skipped, invalid = insert_ip_dataset(user["user_id"], filename, list_type, ips)
    return {
        "message": "Dataset uploaded",
        "dataset_id": dataset_id,
        "total_ips": len(ips),
        "inserted_to_list": inserted,
        "skipped": skipped,
        "invalid": invalid,
    }


@app.get("/ip-datasets", tags=["IP Datasets"])
def list_datasets(user=Depends(get_current_user)):
    return get_ip_datasets(user["user_id"])


@app.delete("/ip-datasets/{dataset_id}", tags=["IP Datasets"])
def del_dataset(dataset_id: int, user=Depends(get_current_user)):
    deleted = delete_ip_dataset(dataset_id, user["user_id"])
    if not deleted:
        raise HTTPException(404, "Dataset not found or not owned by you")
    return {"message": "Dataset deleted and IPs removed from list"}


# ══════════════════════════════════════════════════════════════════════════════
#  NEW v3 — Platform Events (Google / Facebook)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/campaigns/{campaign_id}/platform-event", tags=["Platform"])
def platform_event(campaign_id: int, req: PlatformEventRequest, user=Depends(get_current_user)):
    """Record a Google / Facebook ad event for a campaign."""
    campaign = get_campaign_by_id(campaign_id, user["user_id"])
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    return insert_platform_event(
        campaign_id=campaign_id, platform=req.platform, event_type=req.event_type,
        ip_address=req.ip_address, country=req.country, device=req.device,
        browser=req.browser, cost_usd=req.cost_usd, user_id=user["user_id"],
    )


@app.get("/campaigns/{campaign_id}/platform-events", tags=["Platform"])
def list_platform_events(campaign_id: int, limit: int = Query(200, le=500),
                         platform: Optional[str] = None, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_platform_events(campaign_id, limit, platform)


@app.get("/campaigns/{campaign_id}/platform-stats", tags=["Platform"])
def plat_stats(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_platform_stats(campaign_id)


@app.get("/campaigns/{campaign_id}/realtime-feed", tags=["Platform"])
def realtime(campaign_id: int, limit: int = Query(30, le=100), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_realtime_feed(campaign_id, limit)


@app.get("/campaigns/{campaign_id}/hourly-breakdown", tags=["Platform"])
def hourly(campaign_id: int, hours: int = Query(24, le=168), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_hourly_platform_breakdown(campaign_id, hours)
