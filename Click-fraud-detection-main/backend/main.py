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
import ipaddress as _ipaddress
import json
import logging
import os
import re
import sys
import time
import uuid
from collections import Counter, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

sys.path.insert(0, os.path.dirname(__file__))
from auth import (
    create_access_token,
    generate_api_key,
    get_admin_user,
    get_current_user,
    hash_api_key,
    hash_password,
    validate_jwt_config,
    verify_api_key,
    verify_password,
)
from database import (
    check_campaign_alerts,
    delete_campaign,
    delete_ip,
    delete_ip_dataset,
    delete_user_data,
    get_campaign_by_id,
    get_campaign_click_stats,
    get_campaign_clicks,
    get_campaign_owner_id,
    get_campaigns_by_user,
    get_connection,
    get_click_features,
    get_hourly_platform_breakdown,
    get_ip_datasets,
    get_ip_list,
    get_ip_list_counts,
    get_platform_events,
    get_platform_stats,
    get_prediction_stats,
    get_realtime_feed,
    get_recent_predictions,
    get_user_by_email,
    get_user_by_id,
    get_audit_events,
    init_db,
    insert_campaign,
    insert_campaign_click,
    insert_click,
    insert_ip_dataset,
    insert_platform_event,
    insert_prediction,
    insert_user,
    record_audit_event,
    update_campaign_status,
    # NEW v3
    upsert_ip,
    validate_ip,
)
from model import get_metrics, predict_single

# ── Environment ────────────────────────────────────────────────────────────────
ENV = os.environ.get("ENV", "development")
IS_PRODUCTION = ENV.lower() == "production"
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,https://adshield.vercel.app").split(",")
    if o.strip()
]

# Max upload size for IP datasets (bytes)
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_UPLOAD_ROWS = 50_000
AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "5/minute")
INGEST_RATE_LIMIT = os.getenv("INGEST_RATE_LIMIT", "60/minute")
UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "5/minute")
_LOGIN_FAILURES: dict[str, list[float]] = {}

# ── App setup ──────────────────────────────────────────────────────────────────
app_kwargs = {"title": "AdShield API v3", "version": "3.0.0"}
if IS_PRODUCTION:
    # Disable interactive docs in production
    app_kwargs.update({"docs_url": None, "redoc_url": None, "openapi_url": None})

logger = logging.getLogger("adshield.api")
_request_counts = Counter()
_request_latencies = deque(maxlen=5000)


class _JsonFormatter(logging.Formatter):
    def format(self, record):
        details = getattr(record, "details", {})
        return json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(), "message": record.getMessage(), **details})


if not logger.handlers:
    _log_handler = logging.StreamHandler(sys.stdout)
    _log_handler.setFormatter(_JsonFormatter())
    logger.addHandler(_log_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


@asynccontextmanager
async def lifespan(application):
    validate_jwt_config()
    if IS_PRODUCTION and not os.environ.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL must point to PostgreSQL in production")
    if IS_PRODUCTION and "*" in CORS_ORIGINS:
        raise RuntimeError("Wildcard CORS origins are not allowed in production")
    init_db()
    if os.getenv("SENTRY_DSN"):
        import sentry_sdk
        sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], send_default_pii=False, traces_sample_rate=0.0)
    try:
        from app.services.scoring import _load_model
        if _load_model() is None:
            logger.warning("model artifact unavailable; serving in rules-only mode")
    except Exception:
        logger.warning("model artifact unavailable; serving in rules-only mode")
    yield


app = FastAPI(lifespan=lifespan, **app_kwargs)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    candidate_id = request.headers.get("X-Request-ID", "")
    request_id = candidate_id if len(candidate_id) <= 128 and re.fullmatch(r"[A-Za-z0-9._-]+", candidate_id) else str(uuid.uuid4())
    started = time.perf_counter()
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    latency_ms = round((time.perf_counter()-started)*1000, 2)
    route = request.scope.get("route")
    endpoint = getattr(route, "path", "unknown")
    _request_counts[f"{request.method} {endpoint} {response.status_code}"] += 1
    _request_latencies.append(latency_ms)
    user_id = None
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        try:
            from auth import decode_access_token
            user_id = decode_access_token(authorization[7:]).get("user_id")
        except Exception:
            user_id = None
    logger.info("request complete", extra={"details": {"request_id": request_id,
        "endpoint": endpoint, "user_id": user_id, "status": response.status_code,
        "latency_ms": latency_ms, "model_version": getattr(request.state, "model_version", None),
        "score": getattr(request.state, "score", None), "decision": getattr(request.state, "decision", None)}})
    return response

# Rate limiter (in-memory, single instance — works without Redis)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "rate_limited", "message": "Too many requests. Please slow down.",
            "request_id": getattr(request.state, "request_id", None)}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, headers=exc.headers, content={
        "error": {"code": f"http_{exc.status_code}", "message": message,
            "request_id": getattr(request.state, "request_id", None)}})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {
        "code": "validation_error", "message": "Request validation failed",
        "request_id": getattr(request.state, "request_id", None)}})


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    allow_credentials=True,
)


# ── Schemas ────────────────────────────────────────────────────────────────────
class ClickRequest(BaseModel):
    ip_address: str
    device_type: str
    browser: str
    timestamp: str
    geo_location: str
    user_agent: str = Field(default="", max_length=512)
    event_id: str | None = Field(default=None, min_length=1, max_length=128)

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
        known = {"chrome", "firefox", "safari", "edge", "opera"}
        if v.lower() not in known:
            return "Other"
        return v.capitalize()


class FlexibleResponse(BaseModel):
    """Typed known fields while preserving additional database columns in responses."""
    model_config = {"extra": "allow"}


class AuthUserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthUserResponse


class UserResponse(AuthUserResponse):
    pass


class StatsResponse(BaseModel):
    total: int
    fraud: int
    review: int
    legit: int
    fraud_rate: float


class CampaignResponse(FlexibleResponse):
    id: int
    user_id: int
    name: str
    ad_type: str
    platform: str
    purpose: str
    status: str
    created_at: str | None = None
    cpc: float | None = None
    avg_conversion_value: float | None = None
    expected_conversion_rate: float | None = None
    block_threshold: float | None = None
    click_count: int | None = None
    fraud_count: int | None = None
    valid_count: int | None = None
    suspicious_count: int | None = None


class CampaignCreateResponse(BaseModel):
    message: str
    campaign_id: int
    api_key: str
    note: str


class CampaignClickResponse(FlexibleResponse):
    id: int
    campaign_id: int
    ip_address: str
    classification: str
    fraud_reason: str | None = None
    score: float | None = None
    decision: str | None = None
    reason_codes: str | list[str] | None = None
    model_version: str | None = None
    created_at: str | None = None


class CampaignStatsResponse(BaseModel):
    total: int
    fraud: int
    suspicious: int
    valid: int
    fraud_rate: float


class ThresholdAnalysisResponse(BaseModel):
    recommended_block_threshold: float
    active_block_threshold: float
    analysis: dict
    estimate_notice: str


class AlertResponse(BaseModel):
    level: str
    message: str
    campaign_id: int | None = None
    campaign_name: str | None = None


class IPListResponse(FlexibleResponse):
    id: int
    user_id: int
    ip_address: str
    list_type: str
    note: str | None = None
    source: str | None = None
    created_at: str | None = None


class IPListCountsResponse(BaseModel):
    blocked: int
    whitelisted: int
    total: int


class IPDatasetResponse(FlexibleResponse):
    id: int
    user_id: int
    filename: str
    list_type: str
    row_count: int
    created_at: str | None = None


class RealtimeFeedResponse(BaseModel):
    source: str
    platform: str
    event_type: str
    ip_address: str
    country: str
    device: str
    browser: str
    cost_usd: float
    classification: str
    fraud_reason: str | None = None
    created_at: str


class HourlyBreakdownResponse(BaseModel):
    hour: str
    platform: str
    classification: str
    cnt: int


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
    cpc: float = Field(default=0.50, ge=0, le=100000)
    avg_conversion_value: float = Field(default=25.0, ge=0, le=10000000)
    expected_conversion_rate: float = Field(default=0.02, ge=0, le=1)

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
    user_agent: str = Field(default="", max_length=512)
    event_id: str | None = Field(default=None, min_length=1, max_length=128)


# ── NEW v3 Schemas ─────────────────────────────────────────────────────────────
class IPEntryRequest(BaseModel):
    ip_address: str = Field(..., examples=["203.45.67.89"])
    list_type: str = Field(..., examples=["block"])
    note: str = Field(default="", max_length=500)

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
    event_id: str | None = Field(default=None, min_length=1, max_length=128)

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
@app.get("/healthz", tags=["Health"])
def healthz():
    """Liveness probe — no DB call."""
    return {"status": "ok"}


@app.get("/readyz", tags=["Health"])
def readyz():
    """Readiness probe reports database and model availability."""
    db_ok = False
    try:
        conn = __import__("database").get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        db_ok = True
    except Exception:
        logger.warning("database readiness check failed")
    try:
        from app.services.scoring import _load_model
        model_ok = _load_model() is not None
    except Exception:
        model_ok = False
    status = "ready" if db_ok and model_ok else "degraded"
    return JSONResponse(status_code=503 if not db_ok else 200, content={
        "status": status, "database": db_ok,
        "model": "available" if model_ok else "rules-only"})


# ── Prediction ─────────────────────────────────────────────────────────────────
@app.post("/predict", tags=["Prediction"])
@limiter.limit(INGEST_RATE_LIMIT)
def predict(click: ClickRequest, request: Request, user=Depends(get_current_user)):
    ip_count, click_interval = get_click_features(click.ip_address, user["user_id"])
    record = click.model_dump()
    record.update({"ip_click_count": ip_count, "click_interval": click_interval})
    try:
        result = predict_single(record)
    except FileNotFoundError:
        raise HTTPException(503, "Model not available")
    except Exception:
        raise HTTPException(500, "Prediction error")
    request.state.model_version = result.get("model_version")
    request.state.score = result.get("confidence")
    request.state.decision = result.get("decision")

    try:
        insert_click(
            click.ip_address, click.device_type, click.browser, click.geo_location,
            click.timestamp, click_interval, ip_count, user_id=user["user_id"], event_id=click.event_id,
        )
        insert_prediction(click.ip_address, result["prediction"], result["confidence"], user_id=user["user_id"],
            decision=result.get("decision"), reason_codes=result.get("reason_codes"),
            model_version=result.get("model_version"), event_id=click.event_id)
    except Exception:
        logger.error("prediction persistence failed", extra={"details": {"request_id": request.state.request_id}})
        raise HTTPException(503, "Prediction could not be stored")

    return result


@app.get("/metrics", tags=["Model"])
def metrics(user=Depends(get_current_user)):
    return get_metrics()


@app.get("/clicks", tags=["Data"])
def recent_clicks(limit: int = Query(default=50, ge=1, le=500), user=Depends(get_current_user)):
    return get_recent_predictions(limit, user_id=user["user_id"])


@app.get("/history", tags=["Data"])
def prediction_history(
    limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0),
    date_from: str | None = None, date_to: str | None = None,
    verdict: str | None = None, campaign_id: int | None = None,
    sort_by: str = Query(default="id", pattern="^(id|ip_address|result|confidence|created_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    user=Depends(get_current_user),
):
    """Paginated prediction history with account-scoped filters."""
    clauses = ["user_id=?"]
    params: list[object] = [user["user_id"]]
    if date_from:
        clauses.append("date(created_at) >= date(?)"); params.append(date_from)
    if date_to:
        clauses.append("date(created_at) <= date(?)"); params.append(date_to)
    if verdict:
        if verdict not in {"Fraud", "Legit"}:
            raise HTTPException(400, "verdict must be Fraud or Legit")
        clauses.append("result=?"); params.append(verdict)
    if campaign_id is not None:
        if get_campaign_owner_id(campaign_id) != user["user_id"]:
            raise HTTPException(404, "Campaign not found")
        campaign_clauses = ["campaign_id=?"]
        campaign_params: list[object] = [campaign_id]
        if date_from:
            campaign_clauses.append("date(created_at) >= date(?)"); campaign_params.append(date_from)
        if date_to:
            campaign_clauses.append("date(created_at) <= date(?)"); campaign_params.append(date_to)
        if verdict:
            campaign_clauses.append("classification=?"); campaign_params.append("FRAUD" if verdict == "Fraud" else "VALID")
        where_campaign = " AND ".join(campaign_clauses)
        conn = get_connection()
        total = conn.execute(f"SELECT COUNT(*) FROM campaign_clicks WHERE {where_campaign}", campaign_params).fetchone()[0]
        campaign_sort = {"id": "id", "ip_address": "ip_address", "result": "classification", "confidence": "score", "created_at": "created_at"}[sort_by]
        campaign_rows = conn.execute(
            f"SELECT id,ip_address,classification AS result,score AS confidence,decision,reason_codes,model_version,created_at FROM campaign_clicks WHERE {where_campaign} ORDER BY {campaign_sort} {sort_order.upper()} LIMIT ? OFFSET ?",
            [*campaign_params, limit, offset],
        ).fetchall()
        conn.close()
        items = []
        for row in campaign_rows:
            item = {**dict(row), "result": "Fraud" if row["result"] == "FRAUD" else "Legit" if row["result"] == "VALID" else "Suspicious"}
            item["reason_codes"] = json.loads(row["reason_codes"] or "[]")
            items.append(item)
        return {"items": items, "total": total}
    where = " AND ".join(clauses)
    conn = get_connection()
    total = conn.execute(f"SELECT COUNT(*) FROM predictions WHERE {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT id,ip_address,result,confidence,decision,reason_codes,model_version,created_at FROM predictions WHERE {where} ORDER BY {sort_by} {sort_order.upper()} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    conn.close()
    return {"items": [{**dict(row), "reason_codes": json.loads(row["reason_codes"] or "[]")} for row in rows], "total": total}


@app.get("/stats", tags=["Data"], response_model=StatsResponse)
def fraud_stats(user=Depends(get_current_user)):
    return get_prediction_stats(user_id=user["user_id"])


# ── Train (admin-only, disabled in production) ────────────────────────────────
@app.post("/train", tags=["Model"])
def train(user=Depends(get_admin_user)):
    raise HTTPException(410, "Model training runs offline with `python -m ml.train`.")


# ── Auth ───────────────────────────────────────────────────────────────────────
@app.post("/auth/signup", tags=["Auth"])
@limiter.limit(AUTH_RATE_LIMIT)
def signup(req: SignupRequest, request: Request):
    hashed = hash_password(req.password)
    uid = insert_user(req.name, req.email, hashed)
    if uid is None:
        raise HTTPException(409, "Email already registered")
    return {"message": "Account created", "user_id": uid}


@app.post("/auth/login", tags=["Auth"], response_model=LoginResponse)
@limiter.limit(AUTH_RATE_LIMIT)
def login(req: LoginRequest, request: Request):
    if len(_LOGIN_FAILURES) > 10_000:
        cutoff = time.time() - 900
        for key in [key for key, values in _LOGIN_FAILURES.items() if not values or max(values) < cutoff]:
            _LOGIN_FAILURES.pop(key, None)
    key = f"{get_remote_address(request)}:{req.email.lower()}"
    now = time.time()
    failures = [moment for moment in _LOGIN_FAILURES.get(key, []) if now - moment < 900]
    if len(failures) >= 5:
        raise HTTPException(429, "Too many failed sign-in attempts. Try again later.")
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        failures.append(now)
        _LOGIN_FAILURES[key] = failures
        raise HTTPException(401, "Invalid email or password")
    _LOGIN_FAILURES.pop(key, None)
    token = create_access_token(user["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
    }


@app.get("/auth/me", tags=["Auth"], response_model=UserResponse)
def me(user=Depends(get_current_user)):
    db_user = get_user_by_id(user["user_id"])
    if not db_user:
        raise HTTPException(404, "User not found")
    return db_user


@app.delete("/account", tags=["Privacy"])
def delete_account(user=Depends(get_current_user)):
    if not delete_user_data(user["user_id"]):
        raise HTTPException(404, "Account not found")
    return {"message": "Account and associated data deleted"}


# ── Campaigns ──────────────────────────────────────────────────────────────────
@app.get("/campaigns", tags=["Campaigns"], response_model=list[CampaignResponse])
def list_campaigns(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                   user=Depends(get_current_user)):
    return get_campaigns_by_user(user["user_id"], limit, offset)


@app.post("/campaigns", tags=["Campaigns"], response_model=CampaignCreateResponse)
def create_campaign(req: CampaignRequest, user=Depends(get_current_user)):
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    cid = insert_campaign(user["user_id"], req.name, req.ad_type, req.platform, req.purpose,
        api_key_hash=key_hash, cpc=req.cpc, avg_conversion_value=req.avg_conversion_value,
        expected_conversion_rate=req.expected_conversion_rate)
    return {
        "message": "Campaign created",
        "campaign_id": cid,
        "api_key": raw_key,
        "note": "Save this API key — it will not be shown again.",
    }


class CampaignEconomicsRequest(BaseModel):
    cpc: float = Field(ge=0, le=100000)
    avg_conversion_value: float = Field(ge=0, le=10000000)
    expected_conversion_rate: float = Field(ge=0, le=1)


@app.patch("/campaigns/{campaign_id}/economics", tags=["Campaigns"])
def update_campaign_economics(campaign_id: int, req: CampaignEconomicsRequest,
                              user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "Campaign not found")
    conn = get_connection()
    conn.execute("UPDATE campaigns SET cpc=?,avg_conversion_value=?,expected_conversion_rate=? WHERE id=? AND user_id=?",
        (req.cpc, req.avg_conversion_value, req.expected_conversion_rate, campaign_id, user["user_id"]))
    conn.commit()
    conn.close()
    return {"message": "Campaign economics updated"}


@app.get("/campaigns/{campaign_id}/threshold-analysis", tags=["Campaigns"], response_model=ThresholdAnalysisResponse)
def campaign_threshold_analysis(campaign_id: int, threshold: float | None = Query(None, ge=0, le=1),
                                user=Depends(get_current_user)):
    campaign = get_campaign_by_id(campaign_id, user["user_id"])
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    from app.services.economics import recommended_block_threshold, threshold_what_if
    recommended = recommended_block_threshold(campaign["cpc"], campaign["avg_conversion_value"],
                                               campaign["expected_conversion_rate"])
    clicks = get_campaign_clicks(campaign_id, limit=500)
    analysis = threshold_what_if(clicks, cpc=campaign["cpc"],
        avg_conversion_value=campaign["avg_conversion_value"],
        expected_conversion_rate=campaign["expected_conversion_rate"],
        threshold=recommended if threshold is None else threshold)
    return {"recommended_block_threshold": round(recommended, 4),
            "active_block_threshold": campaign.get("block_threshold") or recommended, "analysis": analysis,
            "estimate_notice": "Historical classification labels and scores are proxies, not verified outcomes."}


class BlockThresholdRequest(BaseModel):
    block_threshold: float = Field(ge=0.01, le=1.0)


@app.patch("/campaigns/{campaign_id}/block-threshold", tags=["Campaigns"])
def set_campaign_block_threshold(campaign_id: int, req: BlockThresholdRequest,
                                 user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "Campaign not found")
    conn = get_connection()
    conn.execute("UPDATE campaigns SET block_threshold=? WHERE id=? AND user_id=?",
        (req.block_threshold, campaign_id, user["user_id"]))
    conn.commit()
    conn.close()
    return {"block_threshold": req.block_threshold}


@app.get("/campaigns/{campaign_id}", tags=["Campaigns"], response_model=CampaignResponse)
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
@limiter.limit(INGEST_RATE_LIMIT)
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
    try:
        client_ip = validate_ip(client_ip)
    except ValueError:
        raise HTTPException(400, "Client IP address is invalid")
    owner_user_id = campaign_info["user_id"]

    result = insert_campaign_click(campaign_id, client_ip, req.user_agent, user_id=owner_user_id, event_id=req.event_id)
    request.state.model_version = result.get("model_version")
    request.state.score = result.get("score")
    request.state.decision = result.get("decision")
    return result


@app.get("/campaigns/{campaign_id}/clicks", tags=["Campaign Clicks"], response_model=list[CampaignClickResponse])
def get_clicks(campaign_id: int, limit: int = Query(100, ge=1, le=500),
               offset: int = Query(0, ge=0), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_campaign_clicks(campaign_id, limit, offset)


@app.get("/campaigns/{campaign_id}/stats", tags=["Campaign Clicks"], response_model=CampaignStatsResponse)
def get_stats(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_campaign_click_stats(campaign_id)


@app.get("/campaigns/{campaign_id}/alerts", tags=["Campaign Clicks"])
def get_alerts(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return check_campaign_alerts(campaign_id)


@app.get("/alerts", tags=["Campaign Clicks"], response_model=list[AlertResponse])
def all_alerts(user=Depends(get_current_user)):
    alerts = []
    for campaign in get_campaigns_by_user(user["user_id"], limit=500):
        for alert in check_campaign_alerts(campaign["id"]):
            alerts.append({**alert, "campaign_id": campaign["id"], "campaign_name": campaign["name"]})
    return alerts


# ══════════════════════════════════════════════════════════════════════════════
#  NEW v3 — IP List endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/ip-lists", tags=["IP Lists"], response_model=list[IPListResponse])
def list_ips(list_type: str | None = None, limit: int = Query(100, ge=1, le=500),
             offset: int = Query(0, ge=0), user=Depends(get_current_user)):
    """Return all blocked/whitelisted IPs for the current user."""
    return get_ip_list(user["user_id"], list_type, limit, offset)


@app.get("/ip-lists/counts", tags=["IP Lists"], response_model=IPListCountsResponse)
def ip_counts(user=Depends(get_current_user)):
    return get_ip_list_counts(user["user_id"])


@app.post("/ip-lists", tags=["IP Lists"])
def add_ip_entry(req: IPEntryRequest, user=Depends(get_current_user)):
    rid = upsert_ip(user["user_id"], req.ip_address, req.list_type, req.note)
    record_audit_event(user["user_id"], "ip_list.upsert", "ip_list_entry", rid,
                       {"list_type": req.list_type})
    return {"message": "IP added", "id": rid, "ip": req.ip_address, "list_type": req.list_type}


@app.delete("/ip-lists/{ip_address:path}", tags=["IP Lists"])
def remove_ip_entry(ip_address: str, user=Depends(get_current_user)):
    try:
        ip_address = validate_ip(ip_address)
    except ValueError:
        raise HTTPException(400, "Invalid IP address")
    deleted_id = delete_ip(user["user_id"], ip_address)
    if deleted_id is not None:
        record_audit_event(user["user_id"], "ip_list.delete", "ip_list_entry", deleted_id)
    return {"message": f"IP {ip_address} removed"}


# ══════════════════════════════════════════════════════════════════════════════
#  NEW v3 — IP Dataset upload endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/ip-datasets/upload", tags=["IP Datasets"])
@limiter.limit(UPLOAD_RATE_LIMIT)
async def upload_dataset(
    request: Request,
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
    record_audit_event(user["user_id"], "ip_dataset.upload", "ip_dataset", dataset_id,
                       {"list_type": list_type, "rows": len(ips)})
    return {
        "message": "Dataset uploaded",
        "dataset_id": dataset_id,
        "total_ips": len(ips),
        "inserted_to_list": inserted,
        "skipped": skipped,
        "invalid": invalid,
    }


@app.get("/ip-datasets", tags=["IP Datasets"], response_model=list[IPDatasetResponse])
def list_datasets(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                  user=Depends(get_current_user)):
    return get_ip_datasets(user["user_id"], limit, offset)


@app.delete("/ip-datasets/{dataset_id}", tags=["IP Datasets"])
def del_dataset(dataset_id: int, user=Depends(get_current_user)):
    deleted = delete_ip_dataset(dataset_id, user["user_id"])
    if not deleted:
        raise HTTPException(404, "Dataset not found or not owned by you")
    record_audit_event(user["user_id"], "ip_dataset.delete", "ip_dataset", dataset_id)
    return {"message": "Dataset deleted and IPs removed from list"}


# ══════════════════════════════════════════════════════════════════════════════
#  NEW v3 — Platform Events (Google / Facebook)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/campaigns/{campaign_id}/platform-event", tags=["Platform"])
@limiter.limit(INGEST_RATE_LIMIT)
def platform_event(campaign_id: int, req: PlatformEventRequest, request: Request, user=Depends(get_current_user)):
    """Record a Google / Facebook ad event for a campaign."""
    campaign = get_campaign_by_id(campaign_id, user["user_id"])
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    result = insert_platform_event(
        campaign_id=campaign_id, platform=req.platform, event_type=req.event_type,
        ip_address=req.ip_address, country=req.country, device=req.device,
        browser=req.browser, cost_usd=req.cost_usd, user_id=user["user_id"], event_id=req.event_id,
    )
    request.state.model_version = result.get("model_version")
    request.state.score = result.get("score")
    request.state.decision = result.get("decision")
    return result


@app.get("/campaigns/{campaign_id}/platform-events", tags=["Platform"])
def list_platform_events(campaign_id: int, limit: int = Query(200, ge=1, le=500),
                         offset: int = Query(0, ge=0),
                         platform: str | None = None, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_platform_events(campaign_id, limit, platform, offset)


@app.get("/campaigns/{campaign_id}/platform-stats", tags=["Platform"])
def plat_stats(campaign_id: int, user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_platform_stats(campaign_id)


@app.get("/campaigns/{campaign_id}/realtime-feed", tags=["Platform"], response_model=list[RealtimeFeedResponse])
def realtime(campaign_id: int, limit: int = Query(30, le=100), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_realtime_feed(campaign_id, limit)


@app.get("/campaigns/{campaign_id}/hourly-breakdown", tags=["Platform"], response_model=list[HourlyBreakdownResponse])
def hourly(campaign_id: int, hours: int = Query(24, le=168), user=Depends(get_current_user)):
    if not get_campaign_by_id(campaign_id, user["user_id"]):
        raise HTTPException(404, "not found")
    return get_hourly_platform_breakdown(campaign_id, hours)


@app.get("/api/v1/admin/stats", tags=["Admin"])
def admin_stats(user=Depends(get_admin_user)):
    latencies = sorted(_request_latencies)
    def percentile(fraction):
        return latencies[min(len(latencies) - 1, int((len(latencies) - 1) * fraction))] if latencies else 0.0
    return {"request_counts": dict(_request_counts), "latency_ms": {
        "samples": len(latencies), "p50": percentile(.50), "p95": percentile(.95),
        "max": latencies[-1] if latencies else 0.0}}


@app.get("/api/v1/admin/audit-events", tags=["Admin"])
def admin_audit_events(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(get_admin_user),
):
    """Return paginated audit records without raw IP addresses."""
    return get_audit_events(limit=limit, offset=offset)


# Versioned aliases are introduced without breaking the existing Streamlit client.
# Existing routes remain available as compatibility paths during migration.
from fastapi.routing import APIRoute

for _route in list(app.routes):
    if isinstance(_route, APIRoute) and _route.path.startswith("/") and not _route.path.startswith("/api/v1/"):
        if _route.path not in {"/", "/openapi.json", "/docs", "/redoc"}:
            app.add_api_route("/api/v1" + _route.path, _route.endpoint,
                methods=list(_route.methods or []), name="v1_" + _route.name,
                response_model=_route.response_model, include_in_schema=True)
