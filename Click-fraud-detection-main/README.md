# AdShield v3 — Click Fraud Detection Platform

> A click fraud detection prototype with synthetic data, simulated platform events, IP lists, and bulk dataset uploads. It is not production-ready.

**Positioning:** AdShield is explainable, cost-aware, open-source click-fraud detection for small advertisers. It is an assistive prototype, not a replacement for commercial fraud-detection tools or ad-platform enforcement.

---

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
frontend/      Streamlit pages and API client
data/          Synthetic sample data and generator
ml/            Offline training, monitoring, retention
migrations/    Alembic PostgreSQL schema history
docs/          Architecture, model card, deployment, runbook
docker/        API image; Compose starts local PostgreSQL and UI
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the FastAPI backend
```bash
export JWT_SECRET="replace-with-a-random-value-of-at-least-32-characters"
uvicorn backend.main:app --reload
```
API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`. Local mode uses SQLite. To run PostgreSQL, set `DATABASE_URL` and apply `alembic upgrade head` first.

### 3. Launch Streamlit dashboard
```bash
streamlit run frontend/app.py
```
Dashboard: `http://localhost:8501`

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
- **Frontend**: Streamlit 1.32+ + Plotly
- **Database**: SQLite (9 tables)
- **Fonts**: Syne · IBM Plex Mono · Inter
