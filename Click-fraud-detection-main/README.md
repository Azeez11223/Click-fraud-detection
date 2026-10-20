# AdShield v3 — Click Fraud Detection Platform

> Production-grade fraud detection with **Realtime Google & Facebook monitoring**, **IP Block/Whitelist management**, and **bulk dataset uploads**.

---

## What's New in v3

| Feature | Description |
|---------|-------------|
| 📡 **Realtime Monitor** | Live Google & Facebook ad event feed with per-platform fraud charts, hourly breakdown, wasted spend tracking |
| 🛡️ **IP Manager** | Block/whitelist individual IPs manually. All blocked IPs are enforced across ALL campaign click checks |
| 📂 **Dataset Upload** | Upload CSV, JSON, or TXT files of IPs to bulk-populate block or whitelist. Supports training datasets too |
| 🔌 **Platform Events API** | `POST /campaigns/{id}/platform-event` — record real or simulated Google/Facebook ad events |
| 🗄️ **3 new DB tables** | `ip_lists`, `ip_datasets`, `ip_dataset_rows`, `platform_events` |

---

## Project Structure

```
adshield-v3/
├── backend/
│   ├── main.py           # FastAPI — 30+ endpoints
│   ├── model.py          # XGBoost training & inference
│   ├── database.py       # SQLite — 9 tables
│   ├── auth.py           # JWT + bcrypt
│   └── preprocess.py     # Feature engineering
│
├── frontend/
│   ├── app.py            # Streamlit entry (8 pages)
│   ├── pages/
│   │   ├── dashboard.py
│   │   ├── realtime_monitor.py   ← NEW
│   │   ├── campaigns.py
│   │   ├── campaign_detail.py
│   │   ├── ip_manager.py         ← NEW
│   │   ├── predict.py
│   │   ├── analytics.py
│   │   ├── history.py
│   │   ├── login.py
│   │   ├── signup.py
│   │   └── about.py
│   └── components/
│       ├── api.py        # All API helpers (v3 extended)
│       ├── charts.py
│       └── styles.py
│
├── models/
│   ├── model.pkl
│   └── encoder.pkl
│
├── data/
│   ├── dataset.csv
│   └── generate_dataset.py
│
└── requirements.txt
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the FastAPI backend
```bash
uvicorn backend.main:app --reload
```
API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

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
