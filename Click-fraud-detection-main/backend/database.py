"""
database.py  — AdShield v3
SQLite database layer (will be replaced with SQLAlchemy + Postgres in Phase 2).
Security fixes applied:
  - delete_campaign verifies ownership FIRST
  - insert_ip_dataset: no bare except, uses executemany
  - IP validation with ipaddress module
  - api_key_hash column on campaigns
  - user_id column on clicks_data and predictions
"""
import sqlite3
import os
import ipaddress as _ipaddress

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "click_fraud.db")


def validate_ip(ip_str: str) -> str:
    """Validate and normalize an IP address. Raises ValueError if invalid."""
    return str(_ipaddress.ip_address(ip_str.strip()))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS clicks_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ip_address TEXT NOT NULL, device TEXT,
        browser TEXT, geo_location TEXT, timestamp TEXT, click_interval REAL,
        ip_click_count INTEGER, user_id INTEGER,
        created_at TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ip_address TEXT NOT NULL,
        result TEXT, confidence REAL, user_id INTEGER,
        created_at TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        name TEXT NOT NULL, ad_type TEXT NOT NULL, platform TEXT NOT NULL,
        purpose TEXT NOT NULL, status TEXT DEFAULT 'Active',
        api_key_hash TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS campaign_clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL,
        ip_address TEXT NOT NULL, user_agent TEXT DEFAULT '',
        classification TEXT DEFAULT 'VALID' CHECK(classification IN ('VALID','FRAUD','SUSPICIOUS')),
        fraud_reason TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE)""")
    # NEW v3
    c.execute("""CREATE TABLE IF NOT EXISTS ip_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        ip_address TEXT NOT NULL,
        list_type TEXT NOT NULL CHECK(list_type IN ('block','whitelist')),
        note TEXT DEFAULT '', source TEXT DEFAULT 'manual',
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, ip_address),
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS ip_datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        filename TEXT NOT NULL, row_count INTEGER DEFAULT 0,
        list_type TEXT NOT NULL CHECK(list_type IN ('block','whitelist','training')),
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS ip_dataset_rows (
        id INTEGER PRIMARY KEY AUTOINCREMENT, dataset_id INTEGER NOT NULL,
        ip_address TEXT NOT NULL,
        FOREIGN KEY (dataset_id) REFERENCES ip_datasets(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS platform_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL,
        platform TEXT NOT NULL, event_type TEXT NOT NULL,
        ip_address TEXT NOT NULL, country TEXT DEFAULT '', device TEXT DEFAULT '',
        browser TEXT DEFAULT '', cost_usd REAL DEFAULT 0.0,
        classification TEXT DEFAULT 'VALID' CHECK(classification IN ('VALID','FRAUD','SUSPICIOUS')),
        fraud_reason TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE)""")

    # Indexes for query performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_cc_campaign_ip_time ON campaign_clicks(campaign_id, ip_address, created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cc_campaign_desc ON campaign_clicks(campaign_id, id DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pe_campaign_ip_time ON platform_events(campaign_id, ip_address, created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_idr_dataset ON ip_dataset_rows(dataset_id)")

    conn.commit()
    conn.close()
    print("[OK] DB v3 initialised.")


# ── existing helpers ───────────────────────────────────────────────────────────
def insert_click(ip_address, device, browser, geo_location, timestamp, click_interval, ip_click_count, user_id=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO clicks_data (ip_address,device,browser,geo_location,timestamp,click_interval,ip_click_count,user_id) VALUES (?,?,?,?,?,?,?,?)",
        (ip_address, device, browser, geo_location, timestamp, click_interval, ip_click_count, user_id),
    )
    conn.commit()
    conn.close()


def insert_prediction(ip_address, result, confidence, user_id=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO predictions (ip_address,result,confidence,user_id) VALUES (?,?,?,?)",
        (ip_address, result, confidence, user_id),
    )
    conn.commit()
    conn.close()


def get_recent_predictions(limit=50, user_id=None):
    conn = get_connection()
    if user_id:
        rows = conn.execute(
            "SELECT id,ip_address,result,confidence,created_at FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id,ip_address,result,confidence,created_at FROM predictions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_prediction_stats(user_id=None):
    conn = get_connection()
    if user_id:
        total = conn.execute("SELECT COUNT(*) FROM predictions WHERE user_id=?", (user_id,)).fetchone()[0]
        fraud = conn.execute("SELECT COUNT(*) FROM predictions WHERE user_id=? AND result='Fraud'", (user_id,)).fetchone()[0]
    else:
        total = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        fraud = conn.execute("SELECT COUNT(*) FROM predictions WHERE result='Fraud'").fetchone()[0]
    conn.close()
    legit = total - fraud
    return {"total": total, "fraud": fraud, "legit": legit, "fraud_rate": round(fraud / total * 100, 2) if total else 0}


def insert_user(name, email, password_hash):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO users (name,email,password_hash) VALUES (?,?,?)", (name, email, password_hash))
        conn.commit()
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        conn.close()
        return None


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute("SELECT id,name,email,password_hash FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    """Look up a user by ID. Returns dict with id, name, email or None."""
    conn = get_connection()
    row = conn.execute("SELECT id,name,email FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_campaign(user_id, name, ad_type, platform, purpose, api_key_hash=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO campaigns (user_id,name,ad_type,platform,purpose,api_key_hash) VALUES (?,?,?,?,?,?)",
        (user_id, name, ad_type, platform, purpose, api_key_hash),
    )
    conn.commit()
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return cid


def _camp_q(extra=""):
    """Campaign query with aggregated click counts using a single LEFT JOIN + GROUP BY."""
    return f"""SELECT c.id, c.user_id, c.name, c.ad_type, c.platform, c.purpose,
        c.status, c.api_key_hash, c.created_at,
        COALESCE(SUM(1), 0) AS click_count,
        COALESCE(SUM(CASE WHEN cc.classification='FRAUD' THEN 1 ELSE 0 END), 0) AS fraud_count,
        COALESCE(SUM(CASE WHEN cc.classification='VALID' THEN 1 ELSE 0 END), 0) AS valid_count,
        COALESCE(SUM(CASE WHEN cc.classification='SUSPICIOUS' THEN 1 ELSE 0 END), 0) AS suspicious_count
        FROM campaigns c
        LEFT JOIN campaign_clicks cc ON cc.campaign_id = c.id
        {extra}
        GROUP BY c.id"""


def get_campaigns_by_user(user_id):
    conn = get_connection()
    rows = conn.execute(_camp_q("WHERE c.user_id=?") + " ORDER BY c.id DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_campaign_by_id(campaign_id, user_id=None):
    conn = get_connection()
    if user_id:
        row = conn.execute(_camp_q("WHERE c.id=? AND c.user_id=?"), (campaign_id, user_id)).fetchone()
    else:
        row = conn.execute(_camp_q("WHERE c.id=?"), (campaign_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_campaign_owner_id(campaign_id):
    """Return the user_id that owns this campaign, or None if not found."""
    conn = get_connection()
    row = conn.execute("SELECT user_id, api_key_hash FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    conn.close()
    if row:
        return {"user_id": row["user_id"], "api_key_hash": row["api_key_hash"]}
    return None


def update_campaign_status(campaign_id, status):
    conn = get_connection()
    conn.execute("UPDATE campaigns SET status=? WHERE id=?", (status, campaign_id))
    conn.commit()
    conn.close()


def delete_campaign(campaign_id, user_id):
    """Delete a campaign ONLY if owned by user_id. Returns True if deleted, False if not found/not owned."""
    conn = get_connection()
    try:
        # Verify ownership FIRST
        row = conn.execute("SELECT id FROM campaigns WHERE id=? AND user_id=?", (campaign_id, user_id)).fetchone()
        if not row:
            conn.close()
            return False
        # Delete in correct order (children first, then parent) — all in one transaction
        conn.execute("DELETE FROM platform_events WHERE campaign_id=?", (campaign_id,))
        conn.execute("DELETE FROM campaign_clicks WHERE campaign_id=?", (campaign_id,))
        conn.execute("DELETE FROM campaigns WHERE id=? AND user_id=?", (campaign_id, user_id))
        conn.commit()
        return True
    finally:
        conn.close()


def classify_click(campaign_id, ip_address, user_agent, user_id=None):
    conn = get_connection()
    try:
        if user_id:
            if conn.execute(
                "SELECT 1 FROM ip_lists WHERE user_id=? AND ip_address=? AND list_type='block'",
                (user_id, ip_address),
            ).fetchone():
                return "FRAUD", "IP on block list"
            if conn.execute(
                "SELECT 1 FROM ip_lists WHERE user_id=? AND ip_address=? AND list_type='whitelist'",
                (user_id, ip_address),
            ).fetchone():
                return "VALID", "IP on whitelist"

        c1 = conn.execute(
            "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND ip_address=? AND created_at>=datetime('now','-1 minute')",
            (campaign_id, ip_address),
        ).fetchone()[0]
        if c1 >= 5:
            return "FRAUD", "Same IP >=5 clicks in 60 seconds"

        c2 = conn.execute(
            "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND ip_address=? AND created_at>=datetime('now','-30 seconds')",
            (campaign_id, ip_address),
        ).fetchone()[0]
        if c2 >= 3:
            return "FRAUD", "Same IP >=3 clicks in 30 seconds"

        c3 = conn.execute(
            "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND ip_address=? AND created_at>=datetime('now','-5 minutes')",
            (campaign_id, ip_address),
        ).fetchone()[0]
        if c3 >= 10:
            return "SUSPICIOUS", "Same IP >=10 clicks in 5 minutes"

        if user_agent:
            cu = conn.execute(
                "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND user_agent=? AND created_at>=datetime('now','-10 minutes')",
                (campaign_id, user_agent),
            ).fetchone()[0]
            if cu >= 15:
                return "SUSPICIOUS", "Same device >=15 clicks in 10 minutes"

        return "VALID", ""
    finally:
        conn.close()


def insert_campaign_click(campaign_id, ip_address, user_agent="", user_id=None):
    classification, reason = classify_click(campaign_id, ip_address, user_agent, user_id)
    conn = get_connection()
    conn.execute(
        "INSERT INTO campaign_clicks (campaign_id,ip_address,user_agent,classification,fraud_reason) VALUES (?,?,?,?,?)",
        (campaign_id, ip_address, user_agent, classification, reason),
    )
    conn.commit()
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"id": cid, "classification": classification, "reason": reason}


def get_campaign_clicks(campaign_id, limit=100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM campaign_clicks WHERE campaign_id=? ORDER BY id DESC LIMIT ?",
        (campaign_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_campaign_click_stats(campaign_id):
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=?", (campaign_id,)).fetchone()[0]
    fraud = conn.execute("SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND classification='FRAUD'", (campaign_id,)).fetchone()[0]
    sus = conn.execute("SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND classification='SUSPICIOUS'", (campaign_id,)).fetchone()[0]
    valid = conn.execute("SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND classification='VALID'", (campaign_id,)).fetchone()[0]
    conn.close()
    return {
        "total": total, "fraud": fraud, "suspicious": sus, "valid": valid,
        "fraud_rate": round(fraud / total * 100, 2) if total else 0,
    }


def check_campaign_alerts(campaign_id, threshold=10):
    conn = get_connection()
    ft = conn.execute("SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND classification='FRAUD'", (campaign_id,)).fetchone()[0]
    rf = conn.execute(
        "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND classification='FRAUD' AND created_at>=datetime('now','-1 hour')",
        (campaign_id,),
    ).fetchone()[0]
    conn.close()
    alerts = []
    if ft >= threshold:
        alerts.append({"level": "high", "message": f"[WARNING] {ft} fraud clicks total"})
    if rf >= 5:
        alerts.append({"level": "critical", "message": f"[CRITICAL] {rf} fraud clicks in last hour!"})
    return alerts


# ── NEW v3: IP List helpers ───────────────────────────────────────────────────
def upsert_ip(user_id, ip_address, list_type, note="", source="manual"):
    # Validate IP before storing
    ip_address = validate_ip(ip_address)
    conn = get_connection()
    conn.execute(
        """INSERT INTO ip_lists (user_id,ip_address,list_type,note,source) VALUES (?,?,?,?,?)
        ON CONFLICT(user_id,ip_address) DO UPDATE SET list_type=excluded.list_type,note=excluded.note,source=excluded.source,created_at=datetime('now')""",
        (user_id, ip_address, list_type, note, source),
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return rid


def delete_ip(user_id, ip_address):
    conn = get_connection()
    conn.execute("DELETE FROM ip_lists WHERE user_id=? AND ip_address=?", (user_id, ip_address))
    conn.commit()
    conn.close()


def get_ip_list(user_id, list_type=None):
    conn = get_connection()
    if list_type:
        rows = conn.execute(
            "SELECT * FROM ip_lists WHERE user_id=? AND list_type=? ORDER BY id DESC",
            (user_id, list_type),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM ip_lists WHERE user_id=? ORDER BY list_type,id DESC",
            (user_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ip_list_counts(user_id):
    conn = get_connection()
    blocked = conn.execute("SELECT COUNT(*) FROM ip_lists WHERE user_id=? AND list_type='block'", (user_id,)).fetchone()[0]
    white = conn.execute("SELECT COUNT(*) FROM ip_lists WHERE user_id=? AND list_type='whitelist'", (user_id,)).fetchone()[0]
    conn.close()
    return {"blocked": blocked, "whitelisted": white, "total": blocked + white}


# ── NEW v3: IP Dataset helpers ────────────────────────────────────────────────
def insert_ip_dataset(user_id, filename, list_type, ips: list):
    """Insert IP dataset with proper validation. Returns (dataset_id, inserted, skipped, invalid)."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO ip_datasets (user_id,filename,list_type,row_count) VALUES (?,?,?,?)",
        (user_id, filename, list_type, len(ips)),
    )
    conn.commit()
    dataset_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    inserted = 0
    skipped = 0
    invalid = 0
    valid_rows = []

    for raw_ip in ips:
        raw_ip = raw_ip.strip()
        if not raw_ip:
            continue
        try:
            ip = validate_ip(raw_ip)
        except ValueError:
            invalid += 1
            continue
        valid_rows.append((dataset_id, ip))

    # Bulk insert validated rows
    if valid_rows:
        conn.executemany("INSERT INTO ip_dataset_rows (dataset_id,ip_address) VALUES (?,?)", valid_rows)

    # Bulk upsert into ip_lists if applicable
    if list_type in ("block", "whitelist"):
        for _, ip in valid_rows:
            try:
                conn.execute(
                    """INSERT INTO ip_lists (user_id,ip_address,list_type,source) VALUES (?,?,?,'dataset')
                    ON CONFLICT(user_id,ip_address) DO UPDATE SET list_type=excluded.list_type,source='dataset',created_at=datetime('now')""",
                    (user_id, ip, list_type),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
    else:
        inserted = len(valid_rows)

    # Update actual row count
    conn.execute("UPDATE ip_datasets SET row_count=? WHERE id=?", (len(valid_rows), dataset_id))
    conn.commit()
    conn.close()
    return dataset_id, inserted, skipped, invalid


def get_ip_datasets(user_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ip_datasets WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_ip_dataset(dataset_id, user_id):
    """Delete a dataset. Only removes IPs from ip_lists that:
    1. Were added by this specific dataset (source='dataset')
    2. Are not claimed by another dataset owned by the same user
    """
    conn = get_connection()
    try:
        # Verify ownership
        ds = conn.execute("SELECT id FROM ip_datasets WHERE id=? AND user_id=?", (dataset_id, user_id)).fetchone()
        if not ds:
            return False

        # Get IPs from this dataset
        ips = conn.execute("SELECT ip_address FROM ip_dataset_rows WHERE dataset_id=?", (dataset_id,)).fetchall()

        for r in ips:
            ip = r[0]
            # Check if any OTHER dataset owned by the same user also contains this IP
            other = conn.execute(
                """SELECT 1 FROM ip_dataset_rows idr
                JOIN ip_datasets ids ON ids.id = idr.dataset_id
                WHERE ids.user_id=? AND idr.dataset_id!=? AND idr.ip_address=?""",
                (user_id, dataset_id, ip),
            ).fetchone()
            if not other:
                # Only delete from ip_lists if source='dataset' and no other dataset claims it
                conn.execute(
                    "DELETE FROM ip_lists WHERE user_id=? AND ip_address=? AND source='dataset'",
                    (user_id, ip),
                )

        conn.execute("DELETE FROM ip_dataset_rows WHERE dataset_id=?", (dataset_id,))
        conn.execute("DELETE FROM ip_datasets WHERE id=? AND user_id=?", (dataset_id, user_id))
        conn.commit()
        return True
    finally:
        conn.close()


# ── NEW v3: Platform Events ───────────────────────────────────────────────────
def insert_platform_event(campaign_id, platform, event_type, ip_address,
                          country="", device="", browser="", cost_usd=0.0, user_id=None):
    conn = get_connection()
    cls = "VALID"
    reason = ""
    if user_id:
        if conn.execute(
            "SELECT 1 FROM ip_lists WHERE user_id=? AND ip_address=? AND list_type='block'",
            (user_id, ip_address),
        ).fetchone():
            cls = "FRAUD"
            reason = "IP on block list"
        elif conn.execute(
            "SELECT 1 FROM ip_lists WHERE user_id=? AND ip_address=? AND list_type='whitelist'",
            (user_id, ip_address),
        ).fetchone():
            cls = "VALID"
    if cls == "VALID":
        cnt = conn.execute(
            "SELECT COUNT(*) FROM platform_events WHERE campaign_id=? AND ip_address=? AND created_at>=datetime('now','-1 minute')",
            (campaign_id, ip_address),
        ).fetchone()[0]
        if cnt >= 5:
            cls = "FRAUD"
            reason = "Same IP >=5 platform events in 60s"
        elif cnt >= 3:
            cls = "SUSPICIOUS"
            reason = "Repeated platform events same IP"

    conn.execute(
        "INSERT INTO platform_events (campaign_id,platform,event_type,ip_address,country,device,browser,cost_usd,classification,fraud_reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (campaign_id, platform, event_type, ip_address, country, device, browser, cost_usd, cls, reason),
    )
    conn.commit()
    eid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"id": eid, "classification": cls, "reason": reason}


def get_platform_events(campaign_id, limit=200, platform=None):
    conn = get_connection()
    if platform:
        rows = conn.execute(
            "SELECT * FROM platform_events WHERE campaign_id=? AND platform=? ORDER BY id DESC LIMIT ?",
            (campaign_id, platform, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM platform_events WHERE campaign_id=? ORDER BY id DESC LIMIT ?",
            (campaign_id, limit),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_platform_stats(campaign_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT platform,COUNT(*) AS total,
        SUM(CASE WHEN classification='FRAUD' THEN 1 ELSE 0 END) AS fraud,
        SUM(CASE WHEN classification='SUSPICIOUS' THEN 1 ELSE 0 END) AS suspicious,
        SUM(CASE WHEN classification='VALID' THEN 1 ELSE 0 END) AS valid,
        ROUND(SUM(cost_usd),2) AS total_spend,
        ROUND(SUM(CASE WHEN classification='FRAUD' THEN cost_usd ELSE 0 END),2) AS wasted_spend
        FROM platform_events WHERE campaign_id=? GROUP BY platform""",
        (campaign_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_realtime_feed(campaign_id, limit=30):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT 'platform' AS source, platform, event_type, ip_address, country, device, browser, cost_usd, classification, fraud_reason, created_at
        FROM platform_events WHERE campaign_id=?
        UNION ALL
        SELECT 'click', '', 'click', ip_address, '', '', user_agent, 0.0, classification, fraud_reason, created_at
        FROM campaign_clicks WHERE campaign_id=?
        ORDER BY created_at DESC LIMIT ?
        """,
        (campaign_id, campaign_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_hourly_platform_breakdown(campaign_id, hours=24):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m-%d %H:00', created_at) AS hour,
               platform, classification, COUNT(*) AS cnt
        FROM platform_events WHERE campaign_id=?
          AND created_at>=datetime('now',? || ' hours')
        GROUP BY hour,platform,classification ORDER BY hour
        """,
        (campaign_id, f"-{hours}"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
