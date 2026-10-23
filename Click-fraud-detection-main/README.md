# AdShield v3 — Click Fraud Detection Platform

> A click fraud detection prototype with synthetic data, simulated platform events, IP lists, and bulk dataset uploads. It is not production-ready.

**Positioning:** AdShield is explainable, cost-aware, open-source click-fraud detection for small advertisers. It is an assistive prototype, not a replacement for commercial fraud-detection tools or ad-platform enforcement.

The recommended block threshold is `C_fp / (C_fp + C_fn)`, where `C_fp = avg_conversion_value × expected_conversion_rate` estimates the cost of blocking a legitimate click, and `C_fn = CPC` estimates the cost of allowing a fraudulent click. These are assumptions, and historical what-if amounts are estimates from stored scores and classifications, not confirmed conversions or recovered spend.

## MVP feature status

| Capability | Status | Scope |
|---|---|---|
| Authenticated campaigns, click scoring, reason codes, model version | Implemented | Rules and an optional locally trained XGBoost model; synthetic data is for demonstration only. |
| Per-campaign cost assumptions and block threshold | Implemented | Estimates use each campaign's entered assumptions and existing stored event labels. |
| IP block/allow lists, uploaded IP lists, supplied platform events | Implemented | Platform events are manually supplied or simulated; there are no direct ad-platform connections. |
| Cloud/Tor IP intelligence, JS collection, automated ad-platform exclusions, outbound notifications | Not implemented | These require separate signal-ingest, privacy, and service work. |
| Validation on real advertiser traffic | Not established | No real campaign dataset or independently verified ground truth is bundled. |

## What's New in v3

| Feature | Description |
|---------|-------------|
| 📡 **Realtime Monitor** | Event feed and per-platform charts for simulated Google and Facebook events |
| 🛡️ **IP Manager** | Block/whitelist individual IPs manually. All blocked IPs are enforced across ALL campaign click checks |
| 📂 **Dataset Upload** | Upload CSV, JSON, or TXT files of IPs to bulk-populate block or whitelist. Supports training datasets too |
| 🔌 **Platform Events API** | `POST /campaigns/{id}/platform-event` — record supplied Google/Facebook event data; no provider integration is implemented |
| 🗄️ **3 new DB tables** | `ip_lists`, `ip_datasets`, `ip_dataset_rows`, `platform_events` |

---

## Project Structure

```
backend/       FastAPI, auth, persistence, scoring services
web/           React, TypeScript, and Vite dashboard
data/          Synthetic sample data and generator
ml/            Offline training, monitoring, retention
migrations/    Alembic PostgreSQL schema history
docs/          Architecture, model card, deployment, runbook
docker/        API image; Compose starts local PostgreSQL and API
```

---

## Quick Start

The dashboard uses React/Vite and the API uses FastAPI. Start them in separate terminals.

### 1. Install API dependencies and start FastAPI

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-api.txt
```

Set a JWT secret and the local web origin before starting the API:

```bash
# macOS/Linux
export JWT_SECRET="replace-with-a-random-value-of-at-least-32-characters"
export CORS_ORIGINS="http://localhost:5173"
uvicorn backend.main:app --reload
```

In PowerShell, use `$env:JWT_SECRET='...'` and `$env:CORS_ORIGINS='http://localhost:5173'`. API docs: `http://localhost:8000/docs`. Local mode uses SQLite.

### 2. Start the web app

```bash
cd web
npm ci
npm run dev
```

Open `http://localhost:5173` and create an account. See [web/README.md](web/README.md) for Vercel deployment, environment variables, and frontend checks.

For the repeatable synthetic campaign walkthrough, create an account first, then run `python -m data.seed_demo --user-id <local-user-id>`. The seed data uses reserved documentation IP ranges and synthetic user-agent strings; its labels are not independently verified ground truth.

---

## New API Endpoints (v3)

### IP Lists
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/ip-lists` | List all blocked/whitelisted IPs |
| `GET`  | `/ip-lists/counts` | Count of blocked vs whitelisted |
| `POST` | `/ip-lists` | Add single IP to block or whitelist |
| `DELETE` | `/ip-lists/{ip}` | Remove an IP |

### IP Datasets
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ip-datasets/upload` | Upload CSV/JSON/TXT file of IPs |
| `GET`  | `/ip-datasets` | List uploaded datasets |
| `DELETE` | `/ip-datasets/{id}` | Delete dataset and remove its IPs |

### Platform Events
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/campaigns/{id}/platform-event` | Record Google/Facebook event |
| `GET`  | `/campaigns/{id}/platform-events` | List platform events |
| `GET`  | `/campaigns/{id}/platform-stats` | Stats per platform (spend, fraud) |
| `GET`  | `/campaigns/{id}/realtime-feed` | Latest events (all sources merged) |
| `GET`  | `/campaigns/{id}/hourly-breakdown` | Hourly chart data (24h default) |

---

## IP File Upload Formats

**TXT** — one IP per line:
```
203.45.67.89
10.0.0.1
192.168.1.100
```

**CSV** — IP in first column (header optional):
```csv
ip_address,note
203.45.67.89,bot network
10.0.0.1,competitor
```

**JSON** — array or object:
```json
["203.45.67.89", "10.0.0.1", "192.168.1.100"]
```

---

## Tech Stack

- **ML**: XGBoost + sklearn fallback + SMOTE
- **API**: FastAPI + Uvicorn + Pydantic v2 + python-multipart
- **Auth**: JWT (PyJWT) + bcrypt
- **Frontend**: React + TypeScript + Vite + Tailwind + TanStack Query + Recharts
- **Database**: SQLite (9 tables)
- **Fonts**: Syne · IBM Plex Mono · Inter
