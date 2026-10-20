"""
app.py — AdShield v3
Main Streamlit entry point with new pages: Realtime Monitor + IP Manager
"""
import sys, os
from html import escape as html_escape
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from components.styles import GLOBAL_CSS
from components.api import check_api_health, api_post

st.set_page_config(
    page_title="AdShield — Click Fraud Detection",
    page_icon="🛡️", layout="wide", initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Session state defaults
for key, val in {
    "history": [], "page": "Dashboard", "last_prediction": None,
    "token": None, "user": None, "auth_page": "Login",
    "selected_campaign_id": None, "show_campaign_form": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Auth gate ──────────────────────────────────────────────────────────────────
if not st.session_state.token:
    if st.session_state.auth_page == "Signup":
        from pages.signup import render; render()
    else:
        from pages.login import render; render()
else:
    user = st.session_state.user or {}

    with st.sidebar:
        st.markdown("""
        <div style="padding:24px 16px 20px 16px;border-bottom:1px solid rgba(255,255,255,0.05);">
            <div class="logo-text">Ad<span class="logo-accent">Shield</span></div>
            <div class="logo-version">FRAUD DETECTION PLATFORM v3.0</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # User badge — html_escape all user-controlled values to prevent XSS
        raw_name = user.get("name", "U") or "U"
        initials = html_escape("".join(w[0].upper() for w in raw_name.split()[:2]))
        safe_name = html_escape(user.get('name', 'User') or 'User')
        safe_email = html_escape(user.get('email', '') or '')
        st.markdown(f"""
        <div class="user-badge">
            <div class="user-avatar">{initials}</div>
            <div class="user-info">
                <div class="user-name">{safe_name}</div>
                <div class="user-email">{safe_email}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # API status
        api_ok = check_api_health()
        dot_cls = "online-dot" if api_ok else "offline-dot"
        api_label = "API ONLINE" if api_ok else "API OFFLINE"
        api_color = "#34d399" if api_ok else "#f87171"
        st.markdown(f'<div style="padding:0 16px;margin-bottom:6px;"><span class="{dot_cls}"></span>'
                    f'<span style="color:{api_color};font-size:0.78rem;font-weight:600;font-family:IBM Plex Mono,monospace;letter-spacing:1px;">{api_label}</span></div>',
                    unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label" style="padding-left:16px;">Navigation</div>', unsafe_allow_html=True)

        nav_items = {
            "Dashboard":            "📊  Dashboard",
            "RealtimeMonitor":      "📡  Realtime Monitor",
            "Campaigns":            "📢  Campaigns",
            "PlatformIntegrations": "🔗  Platform Integrations",
            "IPManager":            "🛡️  IP Manager",
            "Predict":              "🔍  Predict Fraud",
            "Analytics":            "📈  Analytics",
            "History":              "📋  History",
            "About":                "ℹ️  About",
        }

        current = st.session_state.page
        if current == "CampaignDetail": current = "Campaigns"

        sel = st.radio("nav", list(nav_items.keys()),
                       format_func=lambda x: nav_items[x],
                       label_visibility="collapsed", key="nav_radio",
                       index=list(nav_items.keys()).index(current) if current in nav_items else 0)

        if st.session_state.page != "CampaignDetail" or sel != "Campaigns":
            st.session_state.page = sel
            if sel != "Campaigns": st.session_state.selected_campaign_id = None

        # Model training
        st.markdown('<div style="border-top:1px solid rgba(255,255,255,0.05);margin:20px 0 16px 0;padding-top:16px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label" style="padding-left:16px;">Model Training</div>', unsafe_allow_html=True)
        use_smote = st.checkbox("Use SMOTE balancing", value=False, key="use_smote")
        if st.button("⚡ Train Model", use_container_width=True):
            with st.spinner("Training XGBoost model…"):
                result, code = api_post("/train", params={"use_smote": str(use_smote).lower()})
            if code == 200:
                m = result.get("metrics", {})
                st.success("Model trained!")
                st.markdown(f'<div class="card" style="margin-top:8px;padding:14px;">'
                            f'<div class="stat-row"><span class="stat-label">Accuracy</span><span class="stat-value">{m.get("accuracy",0)*100:.1f}%</span></div>'
                            f'<div class="stat-row"><span class="stat-label">Precision</span><span class="stat-value">{m.get("precision",0)*100:.1f}%</span></div>'
                            f'<div class="stat-row"><span class="stat-label">Recall</span><span class="stat-value">{m.get("recall",0)*100:.1f}%</span></div>'
                            f'<div class="stat-row"><span class="stat-label">F1</span><span class="stat-value">{m.get("f1_score",0)*100:.1f}%</span></div>'
                            f'</div>', unsafe_allow_html=True)
            else:
                st.error(result.get("detail","Training failed"))

        # Logout
        st.markdown('<div style="border-top:1px solid rgba(255,255,255,0.05);margin:20px 0 12px 0;padding-top:12px;"></div>', unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            for k in ["token","user","page","auth_page","selected_campaign_id"]:
                st.session_state[k] = None if k != "page" else "Dashboard"
            st.session_state.auth_page = "Login"
            st.rerun()

        st.markdown('<div style="position:absolute;bottom:20px;left:0;right:0;padding:0 16px;font-size:0.68rem;color:#1e2d45;font-family:IBM Plex Mono,monospace;letter-spacing:0.5px;">XGBoost · FastAPI · Streamlit · 2025</div>', unsafe_allow_html=True)

    # ── Page routing ───────────────────────────────────────────────────────────
    page = st.session_state.page
    if page == "Dashboard":
        from pages.dashboard import render; render()
    elif page == "RealtimeMonitor":
        from pages.realtime_monitor import render; render()
    elif page == "Campaigns":
        from pages.campaigns import render; render()
    elif page == "CampaignDetail":
        from pages.campaign_detail import render; render()
    elif page == "PlatformIntegrations":
        from pages.platform_integrations import render; render()
    elif page == "IPManager":
        from pages.ip_manager import render; render()
    elif page == "Predict":
        from pages.predict import render; render()
    elif page == "Analytics":
        from pages.analytics import render; render()
    elif page == "History":
        from pages.history import render; render()
    elif page == "About":
        from pages.about import render; render()
