"""Database helpers with a PostgreSQL runtime adapter and SQLite test backend."""
import ipaddress as _ipaddress
import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "click_fraud.db")
DATABASE_URL = os.environ.get("DATABASE_URL")
_pg_engine = None


class _CompatRow:
    """Expose SQLAlchemy rows as sqlite-style index and mapping rows."""
    def __init__(self, row):
        self._mapping = row._mapping
        self._values = tuple(row)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[key]

    def __iter__(self):
        return iter(self._mapping.items())


class _CompatResult:
    def __init__(self, result):
        self._result = result

    def fetchone(self):
        row = self._result.fetchone()
        return _CompatRow(row) if row is not None else None

    def fetchall(self):
        return [_CompatRow(row) for row in self._result.fetchall()]

    @property
    def rowcount(self):
        return self._result.rowcount


class _PostgresConnection:
    """Temporary compatibility wrapper while the legacy helpers migrate to SQLAlchemy."""
    def __init__(self, connection):
        self._connection = connection
        self._transaction = connection.begin()

    def _query(self, sql):
        sql = sql.replace("SELECT last_insert_rowid()", "SELECT LASTVAL()")
        replacements = {
            "datetime('now')": "CURRENT_TIMESTAMP",
            "datetime('now','-10 minutes')": "CURRENT_TIMESTAMP - INTERVAL '10 minutes'",
            "datetime('now','-5 minutes')": "CURRENT_TIMESTAMP - INTERVAL '5 minutes'",
            "datetime('now','-1 minute')": "CURRENT_TIMESTAMP - INTERVAL '1 minute'",
            "datetime('now','-1 hour')": "CURRENT_TIMESTAMP - INTERVAL '1 hour'",
            "MAX(0, (julianday('now')-julianday(?))*86400)": "GREATEST(0, EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ?::timestamptz)))",
            "strftime('%Y-%m-%d %H:00', created_at)": "TO_CHAR(DATE_TRUNC('hour', created_at), 'YYYY-MM-DD HH24:00')",
            "datetime('now',? || ' hours')": "CURRENT_TIMESTAMP + (? || ' hours')::interval",
        }
        for old, new in replacements.items():
            sql = sql.replace(old, new)
        return sql.replace("?", "%s")

    def execute(self, sql, params=()):
        if "PRAGMA" in sql.upper():
            return _CompatResult(self._connection.exec_driver_sql("SELECT 1"))
        try:
            if "CREATE TABLE IF NOT EXISTS" in sql.upper() or "CREATE INDEX IF NOT EXISTS" in sql.upper():
                result = self._connection.exec_driver_sql(sql)
            else:
                result = self._connection.exec_driver_sql(self._query(sql), tuple(params or ()))
            return _CompatResult(result)
        except Exception:
            self.rollback()
            raise

    def executemany(self, sql, params):
        try:
            return _CompatResult(self._connection.exec_driver_sql(self._query(sql), list(params)))
        except Exception:
            self.rollback()
            raise

    def commit(self):
        if self._transaction.is_active:
            self._transaction.commit()
        self._transaction = self._connection.begin()

    def rollback(self):
        if self._transaction.is_active:
            self._transaction.rollback()
        self._transaction = self._connection.begin()

    def close(self):
        if self._transaction.is_active:
            self._transaction.rollback()
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self._transaction.is_active:
            self._transaction.rollback() if exc_type else self._transaction.commit()
        self._connection.close()


def validate_ip(ip_str: str) -> str:
    """Validate and normalize an IP address. Raises ValueError if invalid."""
    return str(_ipaddress.ip_address(ip_str.strip()))


def get_connection():
    if DATABASE_URL:
        global _pg_engine
        if _pg_engine is None:
            from sqlalchemy import create_engine
            url = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            if os.getenv("ENV", "development").lower() == "production" and "sslmode=" not in url:
                url += "&sslmode=require" if "?" in url else "?sslmode=require"
            _pg_engine = create_engine(url, pool_size=3, max_overflow=2,
                pool_pre_ping=True, pool_recycle=300)
        return _PostgresConnection(_pg_engine.connect())
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    if DATABASE_URL:
        # Production schema is provisioned only by Alembic migrations.
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS clicks_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ip_address TEXT NOT NULL, device TEXT,
        browser TEXT, geo_location TEXT, timestamp TEXT, click_interval REAL,
        ip_click_count INTEGER, user_id INTEGER, event_id TEXT,
        created_at TEXT DEFAULT (datetime('now')), UNIQUE(user_id,event_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ip_address TEXT NOT NULL,
        result TEXT, confidence REAL, user_id INTEGER, decision TEXT,
        reason_codes TEXT DEFAULT '[]', model_version TEXT, event_id TEXT,
        created_at TEXT DEFAULT (datetime('now')), UNIQUE(user_id,event_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""")
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
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS campaign_clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL,
        ip_address TEXT NOT NULL, user_agent TEXT DEFAULT '',
        classification TEXT DEFAULT 'VALID' CHECK(classification IN ('VALID','FRAUD','SUSPICIOUS')),
        fraud_reason TEXT DEFAULT '', score REAL, decision TEXT, reason_codes TEXT DEFAULT '[]',
        model_version TEXT, event_id TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(campaign_id,event_id),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE)""")
    # NEW v3
    c.execute("""CREATE TABLE IF NOT EXISTS ip_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        ip_address TEXT NOT NULL,
        list_type TEXT NOT NULL CHECK(list_type IN ('block','whitelist')),
        note TEXT DEFAULT '', source TEXT DEFAULT 'manual',
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, ip_address),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS ip_datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        filename TEXT NOT NULL, row_count INTEGER DEFAULT 0,
        list_type TEXT NOT NULL CHECK(list_type IN ('block','whitelist','training')),
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""")
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
        fraud_reason TEXT DEFAULT '', score REAL, decision TEXT, reason_codes TEXT DEFAULT '[]',
        model_version TEXT, event_id TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(campaign_id,event_id),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_user_id INTEGER,
        action TEXT NOT NULL,
        target_type TEXT NOT NULL,
        target_id TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL)""")

    # Indexes for query performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_cc_campaign_ip_time ON campaign_clicks(campaign_id, ip_address, created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cc_campaign_desc ON campaign_clicks(campaign_id, id DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pe_campaign_ip_time ON platform_events(campaign_id, ip_address, created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_idr_dataset ON ip_dataset_rows(dataset_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor_time ON audit_events(actor_user_id,created_at DESC)")

    # Additive local SQLite upgrade for databases created before score metadata/idempotency.
    for table, additions in {
        "campaign_clicks": {"score": "REAL", "decision": "TEXT", "reason_codes": "TEXT DEFAULT '[]'", "model_version": "TEXT", "event_id": "TEXT"},
        "platform_events": {"score": "REAL", "decision": "TEXT", "reason_codes": "TEXT DEFAULT '[]'", "model_version": "TEXT", "event_id": "TEXT"},
    }.items():
        existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()}
        for column, declaration in additions.items():
            if column not in existing:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cc_event_id ON campaign_clicks(campaign_id,event_id)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pe_event_id ON platform_events(campaign_id,event_id)")
    prediction_columns = {row[1] for row in c.execute("PRAGMA table_info(predictions)").fetchall()}
    for column, declaration in {"decision": "TEXT", "reason_codes": "TEXT DEFAULT '[]'", "model_version": "TEXT", "event_id": "TEXT", "user_id": "INTEGER REFERENCES users(id) ON DELETE CASCADE"}.items():
        if column not in prediction_columns:
            c.execute(f"ALTER TABLE predictions ADD COLUMN {column} {declaration}")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_prediction_event_id ON predictions(user_id,event_id)")
    clicks_columns = {row[1] for row in c.execute("PRAGMA table_info(clicks_data)").fetchall()}
    if "user_id" not in clicks_columns:
        c.execute("ALTER TABLE clicks_data ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
    if "event_id" not in clicks_columns:
        c.execute("ALTER TABLE clicks_data ADD COLUMN event_id TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS idx_clicks_data_user_ip_time ON clicks_data(user_id,ip_address,created_at)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clicks_data_event_id ON clicks_data(user_id,event_id)")

    conn.commit()
    conn.close()
    print("[OK] DB v3 initialised.")


# ── existing helpers ───────────────────────────────────────────────────────────
def insert_click(ip_address, device, browser, geo_location, timestamp, click_interval, ip_click_count, user_id=None, event_id=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO clicks_data (ip_address,device,browser,geo_location,timestamp,click_interval,ip_click_count,user_id,event_id) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,event_id) DO NOTHING",
        (ip_address, device, browser, geo_location, timestamp, click_interval, ip_click_count, user_id, event_id),
    )
    conn.commit()
    conn.close()


def get_click_features(ip_address, user_id):
    """Compute click count in the trailing ten minutes and interval server-side."""
    conn = get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM clicks_data WHERE user_id=? AND ip_address=? AND created_at>=datetime('now','-10 minutes')",
            (user_id, ip_address),
        ).fetchone()[0]
        previous = conn.execute(
            "SELECT created_at FROM clicks_data WHERE user_id=? AND ip_address=? ORDER BY id DESC LIMIT 1",
            (user_id, ip_address),
        ).fetchone()
        interval = 0.0
        if previous:
            interval = float(conn.execute(
                "SELECT MAX(0, (julianday('now')-julianday(?))*86400)", (previous[0],)
            ).fetchone()[0] or 0.0)
        return count, interval
    finally:
        conn.close()


def insert_prediction(ip_address, result, confidence, user_id=None, decision=None, reason_codes=None, model_version=None, event_id=None):
    conn = get_connection()
    if event_id:
        existing = conn.execute("SELECT id FROM predictions WHERE user_id=? AND event_id=?", (user_id, event_id)).fetchone()
        if existing:
            conn.close()
            return existing[0]
    conn.execute(
        "INSERT INTO predictions (ip_address,result,confidence,user_id,decision,reason_codes,model_version,event_id) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(user_id,event_id) DO NOTHING",
        (ip_address, result, confidence, user_id, decision, json.dumps(reason_codes or []), model_version, event_id),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM predictions WHERE user_id=? AND event_id=?", (user_id, event_id)).fetchone() if event_id else None
    prediction_id = row[0] if row else conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return prediction_id


def get_recent_predictions(limit=50, user_id=None):
    conn = get_connection()
    if user_id:
        rows = conn.execute(
            "SELECT id,ip_address,result,confidence,decision,reason_codes,model_version,created_at FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id,ip_address,result,confidence,decision,reason_codes,model_version,created_at FROM predictions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [{**dict(r), "reason_codes": json.loads(r["reason_codes"] or "[]")} for r in rows]


def get_prediction_stats(user_id=None):
    conn = get_connection()
    if user_id:
        total = conn.execute("SELECT COUNT(*) FROM predictions WHERE user_id=?", (user_id,)).fetchone()[0]
        fraud = conn.execute("SELECT COUNT(*) FROM predictions WHERE user_id=? AND (decision='BLOCK' OR (decision IS NULL AND result='Fraud'))", (user_id,)).fetchone()[0]
        review = conn.execute("SELECT COUNT(*) FROM predictions WHERE user_id=? AND decision='REVIEW'", (user_id,)).fetchone()[0]
    else:
        total = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        fraud = conn.execute("SELECT COUNT(*) FROM predictions WHERE decision='BLOCK' OR (decision IS NULL AND result='Fraud')").fetchone()[0]
        review = conn.execute("SELECT COUNT(*) FROM predictions WHERE decision='REVIEW'").fetchone()[0]
    conn.close()
    legit = total - fraud - review
    return {"total": total, "fraud": fraud, "review": review, "legit": legit,
        "fraud_rate": round(fraud / total * 100, 2) if total else 0}


def insert_user(name, email, password_hash):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO users (name,email,password_hash) VALUES (?,?,?)", (name, email, password_hash))
        conn.commit()
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return uid
    except Exception as exc:
        if not isinstance(exc, sqlite3.IntegrityError) and exc.__class__.__name__ != "IntegrityError":
            conn.close()
            raise
        if hasattr(conn, "rollback"):
            conn.rollback()
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


def delete_user_data(user_id):
    """Delete a user's account and associated rows in one transaction."""
    conn = get_connection()
    try:
        deleted = conn.execute("DELETE FROM users WHERE id=?", (user_id,)).rowcount > 0
        conn.commit()
        return deleted
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        conn.close()


def record_audit_event(actor_user_id, action, target_type, target_id=None, metadata=None):
    """Record a privacy-conscious audit event without storing raw IP addresses."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_events (actor_user_id,action,target_type,target_id,metadata) VALUES (?,?,?,?,?)",
            (actor_user_id, action, target_type, str(target_id) if target_id is not None else None,
             json.dumps(metadata or {}, separators=(",", ":"))),
        )
        conn.commit()
    finally:
        conn.close()


def get_audit_events(limit=100, offset=0):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id,actor_user_id,action,target_type,target_id,metadata,created_at "
            "FROM audit_events ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


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
        COUNT(cc.id) AS click_count,
        COALESCE(SUM(CASE WHEN cc.classification='FRAUD' THEN 1 ELSE 0 END), 0) AS fraud_count,
        COALESCE(SUM(CASE WHEN cc.classification='VALID' THEN 1 ELSE 0 END), 0) AS valid_count,
        COALESCE(SUM(CASE WHEN cc.classification='SUSPICIOUS' THEN 1 ELSE 0 END), 0) AS suspicious_count
        FROM campaigns c
        LEFT JOIN campaign_clicks cc ON cc.campaign_id = c.id
        {extra}
        GROUP BY c.id"""


def get_campaigns_by_user(user_id, limit=100, offset=0):
    conn = get_connection()
    rows = conn.execute(_camp_q("WHERE c.user_id=?") + " ORDER BY c.id DESC LIMIT ? OFFSET ?",
                         (user_id, limit, offset)).fetchall()
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


def classify_click(campaign_id, ip_address, user_agent, user_id=None, include_details=False):
    conn = get_connection()
    try:
        if user_id:
            if conn.execute(
                "SELECT 1 FROM ip_lists WHERE user_id=? AND ip_address=? AND list_type='block'",
                (user_id, ip_address),
            ).fetchone():
                details = ("FRAUD", "IP on block list", 1.0, ["ip_blocklisted"], "rules-v1")
                return details if include_details else details[:2]
            if conn.execute(
                "SELECT 1 FROM ip_lists WHERE user_id=? AND ip_address=? AND list_type='whitelist'",
                (user_id, ip_address),
            ).fetchone():
                details = ("VALID", "IP on whitelist", 0.0, ["ip_allowlisted"], "rules-v1")
                return details if include_details else details[:2]

        c1 = conn.execute(
            "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND ip_address=? AND created_at>=datetime('now','-1 minute')",
            (campaign_id, ip_address),
        ).fetchone()[0]
        c3 = conn.execute(
            "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND ip_address=? AND created_at>=datetime('now','-5 minutes')",
            (campaign_id, ip_address),
        ).fetchone()[0]
        if user_agent:
            cu = conn.execute(
                "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND user_agent=? AND created_at>=datetime('now','-10 minutes')",
                (campaign_id, user_agent),
            ).fetchone()[0]
        else:
            cu = 0

        previous = conn.execute(
            "SELECT created_at FROM campaign_clicks WHERE campaign_id=? AND ip_address=? ORDER BY id DESC LIMIT 1",
            (campaign_id, ip_address),
        ).fetchone()
        interval = 0.0
        if previous:
            interval = max(0.0, conn.execute(
                "SELECT MAX(0, (julianday('now')-julianday(?))*86400)", (previous[0],)
            ).fetchone()[0] or 0.0)
        parts = ip_address.split(".")
        subnet_count = conn.execute(
            "SELECT COUNT(*) FROM campaign_clicks WHERE campaign_id=? AND ip_address LIKE ?",
            (campaign_id, ".".join(parts[:3]) + ".%"),
        ).fetchone()[0] if len(parts) == 4 else 0
        # Shared risk scorer combines server-observed click activity with optional native ML.
        from app.services.decision import decide
        from app.services.features import build_features
        from app.services.rules import rule_decision
        from app.services.scoring import score
        features = build_features(ip_click_count=c1, click_interval=interval,
            user_agent=user_agent, subnet_click_count=subnet_count, ua_click_count=cu)
        scored = score(features)
        action, rule_reasons = rule_decision(ip_click_count=c1 + 1, ua_bot=bool(features["ua_bot"]),
            click_interval=interval, ua_click_count=cu + 1)
        action = action or decide(scored["score"])
        reason_codes = rule_reasons or scored["reason_codes"]
        review_burst = max(1, int(os.getenv("IP_REVIEW_5MIN_THRESHOLD", "10")))
        review_ua = max(1, int(os.getenv("UA_REVIEW_10MIN_THRESHOLD", "15")))
        block_ip = max(1, int(os.getenv("IP_BLOCK_CLICK_THRESHOLD", "5")))
        if c3 >= review_burst - 1 or cu >= review_ua - 1:
            action = "REVIEW"
            reason = "Repeated IP or user-agent activity"
            reason_codes = ["RAPID_REPEAT" if interval < 2 else "UA_FLOOD"]
        elif c1 >= block_ip - 1:
            action = "BLOCK"
            reason = f"Same IP >={block_ip} clicks in 60 seconds"
            reason_codes = ["HIGH_FREQUENCY_IP"]
        else:
            reason = ", ".join(reason_codes) or "Model risk score"
        classification = {"BLOCK": "FRAUD", "REVIEW": "SUSPICIOUS", "ALLOW": "VALID"}[action]
        details = (classification, reason, float(scored["score"]), reason_codes, scored["model_version"])
        return details if include_details else details[:2]
    finally:
        conn.close()


def insert_campaign_click(campaign_id, ip_address, user_agent="", user_id=None, event_id=None):
    if event_id:
        check = get_connection()
        existing = check.execute("SELECT id,classification,fraud_reason,score,decision,reason_codes,model_version FROM campaign_clicks WHERE campaign_id=? AND event_id=?", (campaign_id, event_id)).fetchone()
        check.close()
        if existing:
            replay_reasons = json.loads(existing["reason_codes"] or "[]")
            if "REPLAYED_EVENT" not in replay_reasons:
                replay_reasons.append("REPLAYED_EVENT")
            return {"id": existing["id"], "classification": existing["classification"],
                "reason": existing["fraud_reason"], "score": existing["score"],
                "decision": existing["decision"], "reason_codes": replay_reasons,
                "model_version": existing["model_version"], "replayed": True}
    classification, reason, risk, reason_codes, model_version = classify_click(
        campaign_id, ip_address, user_agent, user_id, include_details=True
    )
    decision = {"FRAUD": "BLOCK", "SUSPICIOUS": "REVIEW", "VALID": "ALLOW"}[classification]
    conn = get_connection()
    conn.execute(
        "INSERT INTO campaign_clicks (campaign_id,ip_address,user_agent,classification,fraud_reason,score,decision,reason_codes,model_version,event_id) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(campaign_id,event_id) DO NOTHING",
        (campaign_id, ip_address, user_agent, classification, reason, risk, decision, json.dumps(reason_codes), model_version, event_id),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM campaign_clicks WHERE campaign_id=? AND event_id=?", (campaign_id, event_id)).fetchone() if event_id else None
    cid = row[0] if row else conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"id": cid, "classification": classification, "reason": reason, "score": risk,
        "decision": decision, "reason_codes": reason_codes, "model_version": model_version, "replayed": False}


def get_campaign_clicks(campaign_id, limit=100, offset=0):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM campaign_clicks WHERE campaign_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
        (campaign_id, limit, offset),
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
    rid = conn.execute("SELECT id FROM ip_lists WHERE user_id=? AND ip_address=?", (user_id, ip_address)).fetchone()[0]
    conn.close()
    return rid


def delete_ip(user_id, ip_address):
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM ip_lists WHERE user_id=? AND ip_address=?",
                           (user_id, ip_address)).fetchone()
        conn.execute("DELETE FROM ip_lists WHERE user_id=? AND ip_address=?", (user_id, ip_address))
        conn.commit()
        return row[0] if row else None
    finally:
        conn.close()


def get_ip_list(user_id, list_type=None, limit=100, offset=0):
    conn = get_connection()
    if list_type:
        rows = conn.execute(
            "SELECT * FROM ip_lists WHERE user_id=? AND list_type=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user_id, list_type, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM ip_lists WHERE user_id=? ORDER BY list_type,id DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
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
            existing = conn.execute(
                "SELECT 1 FROM ip_lists WHERE user_id=? AND ip_address=?", (user_id, ip)
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO ip_lists (user_id,ip_address,list_type,source) VALUES (?,?,?,'dataset')",
                (user_id, ip, list_type),
            )
            inserted += 1
    else:
        inserted = len(valid_rows)

    # Update actual row count
    conn.execute("UPDATE ip_datasets SET row_count=? WHERE id=?", (len(valid_rows), dataset_id))
    conn.commit()
    conn.close()
    return dataset_id, inserted, skipped, invalid


def get_ip_datasets(user_id, limit=100, offset=0):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ip_datasets WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                        (user_id, limit, offset)).fetchall()
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
                          country="", device="", browser="", cost_usd=0.0, user_id=None, event_id=None):
    conn = get_connection()
    if event_id:
        existing = conn.execute("SELECT id,classification,fraud_reason,score,decision,reason_codes,model_version FROM platform_events WHERE campaign_id=? AND event_id=?", (campaign_id, event_id)).fetchone()
        if existing:
            conn.close()
            return {"id": existing["id"], "classification": existing["classification"], "reason": existing["fraud_reason"],
                "score": existing["score"], "decision": existing["decision"],
                "reason_codes": json.loads(existing["reason_codes"] or "[]"), "model_version": existing["model_version"], "replayed": True}
    cls = "VALID"
    reason = ""
    risk, reason_codes, model_version = 0.0, [], "rules-v1"
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
        if cnt >= max(1, int(os.getenv("IP_BLOCK_CLICK_THRESHOLD", "5"))) - 1:
            cls = "FRAUD"
            reason = f"Same IP >={os.getenv('IP_BLOCK_CLICK_THRESHOLD', '5')} platform events in 60s"
        elif cnt >= max(1, int(os.getenv("IP_REVIEW_CLICK_THRESHOLD", "3"))) - 1:
            cls = "SUSPICIOUS"
            reason = "Repeated platform events same IP"

    if cls == "VALID":
        # Use the same feature and decision services used by direct predictions/clicks.
        from app.services.decision import decide
        from app.services.features import build_features
        from app.services.scoring import score
        recent = conn.execute(
            "SELECT COUNT(*) FROM platform_events WHERE campaign_id=? AND ip_address=? AND created_at>=datetime('now','-10 minutes')",
            (campaign_id, ip_address),
        ).fetchone()[0]
        ua_count = conn.execute(
            "SELECT COUNT(*) FROM platform_events WHERE campaign_id=? AND browser=? AND created_at>=datetime('now','-10 minutes')",
            (campaign_id, browser),
        ).fetchone()[0] if browser else 0
        features = build_features(ip_click_count=recent, click_interval=0,
            user_agent=browser, subnet_click_count=0, ua_click_count=ua_count)
        scored = score(features)
        action = decide(scored["score"])
        if action != "ALLOW":
            cls = {"BLOCK": "FRAUD", "REVIEW": "SUSPICIOUS"}[action]
            reason = ", ".join(scored["reason_codes"]) or "Risk score threshold"
        risk, reason_codes, model_version = scored["score"], scored["reason_codes"], scored["model_version"]

    decision = {"FRAUD": "BLOCK", "SUSPICIOUS": "REVIEW", "VALID": "ALLOW"}[cls]

    conn.execute(
        "INSERT INTO platform_events (campaign_id,platform,event_type,ip_address,country,device,browser,cost_usd,classification,fraud_reason,score,decision,reason_codes,model_version,event_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(campaign_id,event_id) DO NOTHING",
        (campaign_id, platform, event_type, ip_address, country, device, browser, cost_usd, cls, reason,
         risk, decision, json.dumps(reason_codes), model_version, event_id),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM platform_events WHERE campaign_id=? AND event_id=?", (campaign_id, event_id)).fetchone() if event_id else None
    eid = row[0] if row else conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"id": eid, "classification": cls, "reason": reason, "score": risk,
        "decision": decision, "reason_codes": reason_codes, "model_version": model_version, "replayed": False}


def get_platform_events(campaign_id, limit=200, platform=None, offset=0):
    conn = get_connection()
    if platform:
        rows = conn.execute(
            "SELECT * FROM platform_events WHERE campaign_id=? AND platform=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (campaign_id, platform, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM platform_events WHERE campaign_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (campaign_id, limit, offset),
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
        ROUND(SUM(cost_usd)::numeric,2) AS total_spend,
        ROUND(SUM(CASE WHEN classification='FRAUD' THEN cost_usd ELSE 0 END)::numeric,2) AS wasted_spend
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
