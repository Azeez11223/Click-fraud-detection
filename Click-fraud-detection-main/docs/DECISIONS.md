# Architecture Decision Records

## Phase 0 — Hygiene

### D001: Remove passlib dependency
**Decision**: Removed `passlib[bcrypt]` from requirements.  
**Rationale**: The codebase already uses `bcrypt` directly. `passlib` was unused dead weight and adds supply-chain attack surface.

### D002: Pin all dependencies exactly
**Decision**: Changed from `>=` ranges to exact pins (e.g. `xgboost==2.1.4`).  
**Rationale**: Reproducible builds. Range specifiers can pull in breaking changes silently. Exact pins + Dependabot/pip-audit is safer.

### D003: Add slowapi for rate limiting
**Decision**: Added `slowapi` for in-memory rate limiting (no Redis required).  
**Rationale**: Free tier constraint — must work without Redis. slowapi uses an in-memory store, suitable for a single Render instance. If Redis is added later, swap the storage backend.

## Phase 1 — Security

### D004: JWT_SECRET required at startup (no default)
**Decision**: App exits with code 1 if `JWT_SECRET` is unset or < 32 chars.  
**Rationale**: The original code had `JWT_SECRET = os.environ.get("JWT_SECRET", "adshield-secret-key-change-in-production")`. This means every deployment that forgot to set the env var was running with a publicly known key. Any attacker could forge JWT tokens.

### D005: Minimal JWT claims (user_id only)
**Decision**: JWT payload contains only `user_id`, `iat`, `exp`. Removed `email` and `name`.  
**Rationale**: Tokens are long-lived and cached. Including PII (email, name) in tokens means they persist in browser storage, logs, and third-party services. The user's name/email can be fetched from the DB via `/auth/me` when needed.

### D006: Campaign click ingest uses X-API-Key + server-side IP
**Decision**: `POST /campaigns/{id}/click` requires an `X-API-Key` header. IP is derived from `request.client.host`.  
**Rationale**: The original endpoint was completely unauthenticated and accepted IP from the request body — meaning any attacker could forge IPs and bypass block lists. The API key is generated per-campaign, shown once, and stored as a bcrypt hash.

### D007: Delete campaign verifies ownership first
**Decision**: `delete_campaign()` checks `WHERE id=? AND user_id=?` BEFORE deleting any child rows.  
**Rationale**: Original code deleted `campaign_clicks` and `platform_events` unconditionally, then checked ownership on the `campaigns` delete. If the campaign wasn't owned by the user, the children were already gone — data loss for the real owner.

### D008: Unknown browsers normalized to "Other" instead of 422
**Decision**: Browser validator returns "Other" for unknown browser strings instead of raising a validation error.  
**Rationale**: Bots send arbitrary user-agent strings. Rejecting them with 422 means bots are never scored by the model — they simply get an error. Normalizing to "Other" lets them flow through classification.

### D009: IP validation with ipaddress module
**Decision**: All IP inputs validated using Python's `ipaddress.ip_address()`.  
**Rationale**: The original code accepted any string as an IP (including script tags, SQL fragments, etc). Proper validation prevents injection and ensures clean data.

### D010: Upload size capped at 2 MB, max 50K rows
**Decision**: IP dataset uploads limited to 2 MB and 50,000 rows.  
**Rationale**: Free tier has 512 MB RAM. Unbounded uploads could cause OOM. These limits are generous for IP lists while keeping memory safe.

### D011: CORS origins from environment (no wildcard in production)
**Decision**: `CORS_ORIGINS` read from env var, split on commas. Default is `http://localhost:8501`.  
**Rationale**: Original `allow_origins=["*"]` allows any website to make authenticated requests to the API. In production, only the Streamlit Cloud domain should be allowed.
