"""
auth.py
JWT authentication and password hashing utilities for AdShield.
Uses bcrypt directly (not passlib) for Python 3.13+ compatibility.
"""
import os
import sys
import secrets
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── Config ─────────────────────────────────────────────────────────────────────
JWT_SECRET: str | None = os.environ.get("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))
ADMIN_EMAILS: set[str] = set(
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
)


def validate_jwt_config() -> None:
    """Called at startup. Refuses to start without a strong JWT_SECRET."""
    if not JWT_SECRET:
        print("[FATAL] JWT_SECRET environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if len(JWT_SECRET) < 32:
        print("[FATAL] JWT_SECRET must be at least 32 characters.", file=sys.stderr)
        sys.exit(1)


# ── Password hashing ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── JWT tokens ─────────────────────────────────────────────────────────────────
def create_access_token(user_id: int) -> str:
    """Create a JWT access token with minimal claims: user_id, iat, exp."""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── API key utilities ──────────────────────────────────────────────────────────
def generate_api_key() -> str:
    """Generate a random API key for campaign click ingestion."""
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """Hash an API key using bcrypt for storage."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(key.encode("utf-8"), salt).decode("utf-8")


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Constant-time comparison of API key against stored hash."""
    try:
        return bcrypt.checkpw(plain_key.encode("utf-8"), hashed_key.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── FastAPI dependencies ───────────────────────────────────────────────────────
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency — extracts and validates user from JWT Bearer token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return {"user_id": user_id}


def get_admin_user(user=Depends(get_current_user)):
    """FastAPI dependency — requires the user to be in ADMIN_EMAILS.
    Looks up email from DB and checks against ADMIN_EMAILS env var."""
    from database import get_user_by_id

    db_user = get_user_by_id(user["user_id"])
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")
    if db_user["email"].lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
