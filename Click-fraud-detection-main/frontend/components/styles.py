"""
components/styles.py
Global CSS injection for the AdShield dashboard.
Extended with auth, campaign, and alert styles.
"""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@300;400;500;600&display=swap');

/* ── Reset & Base ─────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #050811;
    color: #c9d1e0;
}

/* ── Hide Streamlit chrome ────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 1.5rem 2.5rem 2rem 2.5rem;
    max-width: 1400px;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #07091a !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    padding-top: 0 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0;
}

/* ── Sidebar radio nav ────────────────────────────────────── */
div[data-testid="stSidebarNav"] { display: none; }
.stRadio > div { gap: 4px; }
.stRadio > div > label {
    background: transparent !important;
    border: none !important;
    padding: 10px 16px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    font-size: 0.88rem !important;
    color: #6b7a99 !important;
    font-weight: 500 !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    width: 100% !important;
}
.stRadio > div > label:hover {
    background: rgba(96, 165, 250, 0.08) !important;
    color: #93c5fd !important;
}
.stRadio > div > label[data-checked="true"],
.stRadio > div > label[aria-checked="true"] {
    background: rgba(96, 165, 250, 0.12) !important;
    color: #60a5fa !important;
    border-left: 2px solid #60a5fa !important;
}
/* hide radio circles */
.stRadio > div > label > div:first-child { display: none !important; }

/* ── Metric Cards ─────────────────────────────────────────── */
div[data-testid="metric-container"] {
    background: linear-gradient(145deg, #0d1229 0%, #0a0f1e 100%) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
    padding: 20px 24px !important;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s ease;
}
div[data-testid="metric-container"]:hover {
    border-color: rgba(96,165,250,0.25) !important;
}
div[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
    border-radius: 14px 14px 0 0;
}
div[data-testid="metric-container"] label {
    color: #4b5d7a !important;
    font-size: 11px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e2e8f5 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 2rem !important;
    font-weight: 600 !important;
    line-height: 1.1 !important;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%) !important;
    color: #eff6ff !important;
    border: 1px solid rgba(96,165,250,0.3) !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.3px !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(29,78,216,0.3) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;
    border-color: rgba(147,197,253,0.5) !important;
    box-shadow: 0 4px 20px rgba(59,130,246,0.4) !important;
    transform: translateY(-1px) !important;
}

/* ── Inputs ───────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    background: #0d1229 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #c9d1e0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: rgba(96,165,250,0.5) !important;
    box-shadow: 0 0 0 2px rgba(96,165,250,0.1) !important;
}
.stTextInput label, .stNumberInput label, .stSelectbox label {
    color: #4b5d7a !important;
    font-size: 0.78rem !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
}

/* ── DataFrames ───────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] iframe {
    border-radius: 12px !important;
}

/* ── Alerts ───────────────────────────────────────────────── */
.stSuccess, .stError, .stWarning, .stInfo {
    border-radius: 10px !important;
    border: none !important;
}

/* ── Dividers ─────────────────────────────────────────────── */
hr {
    border-color: rgba(255,255,255,0.06) !important;
    margin: 1.5rem 0 !important;
}

/* ── Spinner ──────────────────────────────────────────────── */
.stSpinner > div { border-top-color: #3b82f6 !important; }

/* ── Expander ─────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: #0d1229 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
    color: #c9d1e0 !important;
}
.streamlit-expanderContent {
    background: #07091a !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-top: none !important;
}

/* ── Checkbox ─────────────────────────────────────────────── */
.stCheckbox label { color: #6b7a99 !important; }

/* ── Custom components ────────────────────────────────────── */
.page-header {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.page-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.9rem;
    font-weight: 800;
    color: #e2e8f5;
    line-height: 1.15;
    margin: 0;
    letter-spacing: -0.5px;
}
.page-subtitle {
    font-size: 0.85rem;
    color: #4b5d7a;
    margin-top: 4px;
    font-weight: 400;
}

.card {
    background: linear-gradient(145deg, #0d1229 0%, #0a0f1e 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 16px;
}
.card-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    color: #93c5fd;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
}

.badge-fraud {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(220,38,38,0.1));
    color: #f87171;
    border: 1px solid rgba(239,68,68,0.3);
    padding: 10px 22px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 1.1rem;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.5px;
}
.badge-legit {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(5,150,105,0.1));
    color: #34d399;
    border: 1px solid rgba(16,185,129,0.3);
    padding: 10px 22px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 1.1rem;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.5px;
}

.risk-low {
    color: #34d399;
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.8rem;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 1px;
}
.risk-medium {
    color: #fbbf24;
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.3);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.8rem;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 1px;
}
.risk-high {
    color: #f87171;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.8rem;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 1px;
}

.stat-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.85rem;
}
.stat-row:last-child { border-bottom: none; }
.stat-label { color: #4b5d7a; }
.stat-value {
    color: #c9d1e0;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
}

.section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #2d3a52;
    margin-bottom: 8px;
    padding-left: 2px;
}

.online-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    background: #34d399;
    border-radius: 50%;
    box-shadow: 0 0 6px #34d399;
    margin-right: 6px;
}
.offline-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    background: #f87171;
    border-radius: 50%;
    margin-right: 6px;
}

.logo-text {
    font-family: 'Syne', sans-serif;
    font-size: 1.3rem;
    font-weight: 800;
    color: #e2e8f5;
    letter-spacing: -0.5px;
}
.logo-accent { color: #3b82f6; }
.logo-version {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #2d3a52;
    letter-spacing: 1px;
    margin-top: 2px;
}

/* ═══════════════════════════════════════════════════════════
   NEW — Auth card styles
   ═══════════════════════════════════════════════════════════ */
.auth-card {
    background: linear-gradient(145deg, #0d1229 0%, #0a0f1e 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 32px 28px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.4);
    position: relative;
    overflow: hidden;
}
.auth-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #3b82f6, #06b6d4, #3b82f6);
    background-size: 200% 100%;
    animation: shimmer 3s linear infinite;
}
@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ═══════════════════════════════════════════════════════════
   NEW — Campaign card styles
   ═══════════════════════════════════════════════════════════ */
.campaign-card {
    background: linear-gradient(145deg, #0d1229 0%, #0a0f1e 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 8px;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.campaign-card:hover {
    border-color: rgba(96,165,250,0.25);
    box-shadow: 0 4px 20px rgba(59,130,246,0.08);
}
.campaign-stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.campaign-stat-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.3rem;
    font-weight: 700;
    color: #e2e8f5;
}
.campaign-stat-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: #4b5d7a;
    text-transform: uppercase;
}

/* ═══════════════════════════════════════════════════════════
   NEW — Fraud alert banners
   ═══════════════════════════════════════════════════════════ */
.alert-high {
    background: linear-gradient(135deg, rgba(251,191,36,0.08), rgba(245,158,11,0.04));
    border: 1px solid rgba(251,191,36,0.3);
    border-left: 4px solid #fbbf24;
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 12px;
    color: #fbbf24;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    font-weight: 600;
}
.alert-critical {
    background: linear-gradient(135deg, rgba(239,68,68,0.1), rgba(220,38,38,0.05));
    border: 1px solid rgba(239,68,68,0.35);
    border-left: 4px solid #ef4444;
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 12px;
    color: #f87171;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    font-weight: 600;
    animation: pulse-alert 2s ease-in-out infinite;
}
@keyframes pulse-alert {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.75; }
}

/* ═══════════════════════════════════════════════════════════
   NEW — Classification badges
   ═══════════════════════════════════════════════════════════ */
.badge-valid {
    background: rgba(16,185,129,0.12);
    color: #34d399;
    border: 1px solid rgba(16,185,129,0.3);
    padding: 3px 10px;
    border-radius: 5px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.5px;
}
.badge-suspicious {
    background: rgba(251,191,36,0.12);
    color: #fbbf24;
    border: 1px solid rgba(251,191,36,0.3);
    padding: 3px 10px;
    border-radius: 5px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.5px;
}
.badge-fraud-sm {
    background: rgba(239,68,68,0.12);
    color: #f87171;
    border: 1px solid rgba(239,68,68,0.3);
    padding: 3px 10px;
    border-radius: 5px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.5px;
}

/* ═══════════════════════════════════════════════════════════
   NEW — User badge (sidebar)
   ═══════════════════════════════════════════════════════════ */
.user-badge {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: rgba(59,130,246,0.06);
    border: 1px solid rgba(59,130,246,0.15);
    border-radius: 10px;
    margin: 0 8px 12px 8px;
}
.user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #06b6d4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 0.85rem;
    color: #fff;
}
.user-info {
    flex: 1;
    overflow: hidden;
}
.user-name {
    font-size: 0.82rem;
    font-weight: 600;
    color: #e2e8f5;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.user-email {
    font-size: 0.68rem;
    color: #4b5d7a;
    font-family: 'IBM Plex Mono', monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ── Pulse animation for alerts ─────────────────────────── */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
</style>
"""


CHART_THEME = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "#0a0f1e",
    "font": {"color": "#c9d1e0", "family": "Inter, sans-serif"},
    "title_font": {"color": "#e2e8f5", "family": "Syne, sans-serif", "size": 15},
    "xaxis": {
        "gridcolor": "rgba(255,255,255,0.05)",
        "linecolor": "rgba(255,255,255,0.08)",
        "tickcolor": "rgba(255,255,255,0.08)",
        "tickfont": {"color": "#4b5d7a", "size": 11},
        "title_font": {"color": "#6b7a99"},
    },
    "yaxis": {
        "gridcolor": "rgba(255,255,255,0.05)",
        "linecolor": "rgba(255,255,255,0.08)",
        "tickcolor": "rgba(255,255,255,0.08)",
        "tickfont": {"color": "#4b5d7a", "size": 11},
        "title_font": {"color": "#6b7a99"},
    },
    "legend": {
        "bgcolor": "rgba(13,18,41,0.7)",
        "bordercolor": "rgba(255,255,255,0.08)",
        "borderwidth": 1,
        "font": {"color": "#6b7a99", "size": 12},
    },
    "colorway": ["#3b82f6", "#f87171", "#34d399", "#fbbf24", "#a78bfa", "#06b6d4"],
    "margin": {"t": 50, "b": 20, "l": 20, "r": 20},
}


def apply_chart_theme(fig, height=360, title=None):
    """Apply the global dark chart theme to a plotly figure."""
    updates = dict(CHART_THEME)
    updates["height"] = height
    if title:
        updates["title"] = {"text": title, **updates.get("title", {})}
    fig.update_layout(**updates)
    return fig
