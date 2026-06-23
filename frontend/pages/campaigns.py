"""
pages/campaigns.py — Campaign list & creation page
"""
import streamlit as st
from components.api import (
    get_campaigns, create_campaign,
    delete_campaign_api, update_campaign_status_api,
)


# ── Platform / type icons ─────────────────────────────────────────────────────
PLATFORM_ICON = {"Google": "🔵", "Facebook": "🟦", "Instagram": "🟣"}
ADTYPE_ICON   = {"Display": "🖼️", "Video": "🎬", "Search": "🔍", "Social": "💬"}
STATUS_COLORS = {
    "Active":    ("#34d399", "rgba(16,185,129,0.12)"),
    "Paused":    ("#fbbf24", "rgba(251,191,36,0.12)"),
    "Completed": ("#6b7a99", "rgba(107,122,153,0.12)"),
}


def render():
    # ── Header with + button ───────────────────────────────────────────────────
    col_h, col_btn = st.columns([4, 1])
    with col_h:
        st.markdown("""
        <div class="page-header">
            <div class="page-title">Campaigns</div>
            <div class="page-subtitle">Manage your ad campaigns and monitor click activity</div>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        show_form = st.button("＋ New Campaign", use_container_width=True)

    # ── Campaign creation form ─────────────────────────────────────────────────
    if show_form or st.session_state.get("show_campaign_form"):
        st.session_state.show_campaign_form = True
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Create New Campaign</div>', unsafe_allow_html=True)

        with st.form("create_campaign_form", clear_on_submit=True):
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                name = st.text_input("Campaign Name", placeholder="e.g. Summer Sale Ads")
            with r1c2:
                ad_type = st.selectbox("Ad Type", ["Display", "Video", "Search", "Social"])

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                platform = st.selectbox("Platform", ["Google", "Facebook", "Instagram"])
            with r2c2:
                purpose = st.selectbox("Purpose", ["Traffic", "Sales", "Awareness"])

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            sub_col1, sub_col2, sub_col3 = st.columns([1, 1, 3])
            with sub_col1:
                submitted = st.form_submit_button("🚀 Create", use_container_width=True)
            with sub_col2:
                cancelled = st.form_submit_button("✕ Cancel", use_container_width=True)

        if submitted:
            if not name:
                st.error("Campaign name is required")
            else:
                result, code = create_campaign(name, ad_type, platform, purpose)
                if code == 200:
                    st.success(f"Campaign '{name}' created!")
                    st.session_state.show_campaign_form = False
                    st.rerun()
                else:
                    st.error(result.get("detail", "Failed to create campaign"))

        if cancelled:
            st.session_state.show_campaign_form = False
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Campaign list ──────────────────────────────────────────────────────────
    campaigns = get_campaigns()

    if not campaigns:
        st.markdown("""
        <div class="card" style="text-align:center; padding:60px 24px;">
            <div style="font-size:3rem; margin-bottom:16px;">📢</div>
            <div style="color:#4b5d7a; font-size:1rem; font-weight:600;">No campaigns yet</div>
            <div style="color:#2d3a52; font-size:0.82rem; margin-top:8px;">
                Click the <strong>＋ New Campaign</strong> button above to create your first campaign.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Stats bar ──────────────────────────────────────────────────────────────
    total_campaigns = len(campaigns)
    active_count  = sum(1 for c in campaigns if c.get("status") == "Active")
    total_clicks  = sum(c.get("click_count", 0) for c in campaigns)
    total_fraud   = sum(c.get("fraud_count", 0) for c in campaigns)

    s1, s2, s3, s4 = st.columns(4)
    with s1: st.metric("Total Campaigns", total_campaigns)
    with s2: st.metric("Active", active_count)
    with s3: st.metric("Total Clicks", f"{total_clicks:,}")
    with s4: st.metric("Fraud Clicks", f"{total_fraud:,}")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Campaign cards ─────────────────────────────────────────────────────────
    for camp in campaigns:
        cid          = camp["id"]
        cname        = camp["name"]
        platform     = camp.get("platform", "—")
        ad_type      = camp.get("ad_type", "—")
        status       = camp.get("status", "Active")
        click_count  = camp.get("click_count", 0)
        fraud_count  = camp.get("fraud_count", 0)
        valid_count  = camp.get("valid_count", 0)
        created      = camp.get("created_at", "")[:10]

        # Status styling
        s_color, s_bg = STATUS_COLORS.get(status, ("#6b7a99", "rgba(107,122,153,0.12)"))
        p_icon = PLATFORM_ICON.get(platform, "📣")
        t_icon = ADTYPE_ICON.get(ad_type, "📄")

        # Fraud alert indicator
        alert_html = ""
        if fraud_count >= 10:
            alert_html = '<span style="color:#f87171; font-size:0.7rem; font-weight:700; letter-spacing:1px; margin-left:10px; animation:pulse 2s infinite;">⚠ FRAUD ALERT</span>'

        st.markdown(f"""
        <div class="campaign-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:700; color:#e2e8f5; margin-bottom:6px;">
                        {cname} {alert_html}
                    </div>
                    <div style="display:flex; gap:16px; flex-wrap:wrap; font-size:0.8rem; color:#4b5d7a;">
                        <span>{p_icon} {platform}</span>
                        <span>{t_icon} {ad_type}</span>
                        <span>📅 {created}</span>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="background:{s_bg}; color:{s_color}; padding:4px 14px; border-radius:6px;
                                 font-size:0.75rem; font-weight:700; font-family:'IBM Plex Mono',monospace; letter-spacing:1px;">
                        {status.upper()}
                    </span>
                </div>
            </div>
            <div style="display:flex; gap:24px; margin-top:14px; flex-wrap:wrap;">
                <div class="campaign-stat">
                    <span class="campaign-stat-value">{click_count}</span>
                    <span class="campaign-stat-label">TOTAL</span>
                </div>
                <div class="campaign-stat">
                    <span class="campaign-stat-value" style="color:#34d399;">{valid_count}</span>
                    <span class="campaign-stat-label">VALID</span>
                </div>
                <div class="campaign-stat">
                    <span class="campaign-stat-value" style="color:#f87171;">{fraud_count}</span>
                    <span class="campaign-stat-label">FRAUD</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Action buttons row
        bc1, bc2, bc3, bc4 = st.columns([1, 1, 1, 3])
        with bc1:
            if st.button("📊 Details", key=f"detail_{cid}", use_container_width=True):
                st.session_state.selected_campaign_id = cid
                st.session_state.page = "CampaignDetail"
                st.rerun()
        with bc2:
            new_status = "Paused" if status == "Active" else "Active"
            label = "⏸ Pause" if status == "Active" else "▶ Resume"
            if st.button(label, key=f"toggle_{cid}", use_container_width=True):
                update_campaign_status_api(cid, new_status)
                st.rerun()
        with bc3:
            if st.button("🗑 Delete", key=f"del_{cid}", use_container_width=True):
                delete_campaign_api(cid)
                st.rerun()

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
