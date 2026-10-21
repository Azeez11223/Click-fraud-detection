"""
pages/campaign_detail.py — Single campaign detail page with stats, charts, click log, and alerts
"""
import random
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from components.api import (
    get_campaign, get_campaign_clicks_api,
    get_campaign_stats, get_campaign_alerts,
    simulate_click,
)
from components.styles import apply_chart_theme

FRAUD_COLOR = "#f87171"
LEGIT_COLOR = "#34d399"
WARN_COLOR  = "#fbbf24"
BLUE_COLOR  = "#3b82f6"


def render():
    campaign_id = st.session_state.get("selected_campaign_id")
    if not campaign_id:
        st.warning("No campaign selected.")
        return

    campaign = get_campaign(campaign_id)
    if not campaign:
        st.error("Campaign not found or access denied.")
        return

    # ── Back button ────────────────────────────────────────────────────────────
    if st.button("← Back to Campaigns"):
        st.session_state.selected_campaign_id = None
        st.session_state.page = "Campaigns"
        st.rerun()

    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="page-header">
        <div class="page-title">{campaign['name']}</div>
        <div class="page-subtitle" style="display:flex; gap:16px; margin-top:6px;">
            <span>📣 {campaign.get('platform','—')}</span>
            <span>🎯 {campaign.get('ad_type','—')}</span>
            <span>💡 {campaign.get('purpose','—')}</span>
            <span>Status: <strong>{campaign.get('status','Active')}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Alerts ─────────────────────────────────────────────────────────────────
    alerts = get_campaign_alerts(campaign_id)
    for alert in alerts:
        level = alert.get("level", "high")
        msg   = alert.get("message", "")
        if level == "critical":
            st.markdown(f"""
            <div class="alert-critical">{msg}</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-high">{msg}</div>
            """, unsafe_allow_html=True)

    # ── Fetch data ─────────────────────────────────────────────────────────────
    stats  = get_campaign_stats(campaign_id)
    clicks = get_campaign_clicks_api(campaign_id, limit=200)

    total      = stats.get("total", 0)
    fraud_cnt  = stats.get("fraud", 0)
    sus_cnt    = stats.get("suspicious", 0)
    valid_cnt  = stats.get("valid", 0)
    fraud_rate = stats.get("fraud_rate", 0)

    # ── KPI cards ──────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("Total Clicks",      f"{total:,}")
    with k2: st.metric("Valid Clicks",       f"{valid_cnt:,}")
    with k3: st.metric("Suspicious",         f"{sus_cnt:,}")
    with k4: st.metric("Fraud Clicks",       f"{fraud_cnt:,}")
    with k5: st.metric("Fraud Rate",         f"{fraud_rate:.1f}%")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Simulate click section ─────────────────────────────────────────────────
    with st.expander("🧪 Simulate Clicks (for testing)", expanded=False):
        sim_col1, sim_col2, sim_col3 = st.columns([2, 2, 1])
        with sim_col1:
            sim_ip = st.text_input("IP Address", value=f"192.168.1.{random.randint(1,255)}", key="sim_ip")
        with sim_col2:
            sim_ua = st.text_input("User-Agent", value="Mozilla/5.0 TestBot", key="sim_ua")
        with sim_col3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("⚡ Send Click", use_container_width=True, key="sim_btn"):
                result, code = simulate_click(campaign_id, sim_ip, sim_ua)
                if code == 200:
                    cls = result.get("classification", "?")
                    reason = result.get("reason", "")
                    if cls == "FRAUD":
                        st.error(f"🚨 FRAUD — {reason}")
                    elif cls == "SUSPICIOUS":
                        st.warning(f"⚠ SUSPICIOUS — {reason}")
                    else:
                        st.success("✅ VALID CLICK")
                    st.rerun()
                else:
                    st.error("Failed to record click")

        # Rapid-fire test
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        rf1, rf2, rf3 = st.columns([1, 1, 3])
        with rf1:
            if st.button("🤖 Simulate 10 Rapid Clicks", use_container_width=True, key="rapid_btn"):
                bot_ip = f"10.0.0.{random.randint(1,50)}"
                for _ in range(10):
                    simulate_click(campaign_id, bot_ip, "BotAgent/1.0")
                st.success(f"Sent 10 rapid clicks from {bot_ip}")
                st.rerun()
        with rf2:
            if st.button("✅ Simulate 5 Normal Clicks", use_container_width=True, key="normal_btn"):
                for i in range(5):
                    normal_ip = f"{random.randint(50,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
                    simulate_click(campaign_id, normal_ip, f"Chrome/{random.randint(90,120)}.0")
                st.success("Sent 5 normal clicks from unique IPs")
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Charts row ─────────────────────────────────────────────────────────────
    if total > 0:
        ch_left, ch_right = st.columns([1, 2])

        with ch_left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Click Classification</div>', unsafe_allow_html=True)

            fig = go.Figure(go.Pie(
                labels=["Valid", "Suspicious", "Fraud"],
                values=[valid_cnt, sus_cnt, fraud_cnt],
                hole=0.62,
                marker=dict(
                    colors=[LEGIT_COLOR, WARN_COLOR, FRAUD_COLOR],
                    line=dict(color="#050811", width=3),
                ),
                textfont=dict(color="#ffffff", size=12),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9d1e0", family="Inter, sans-serif"),
                showlegend=True,
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#6b7a99", size=12)),
                margin=dict(t=20, b=20, l=20, r=20),
                height=300,
                annotations=[dict(
                    text=f"<b>{total}</b><br><span style='font-size:11px;color:#4b5d7a'>Total</span>",
                    x=0.5, y=0.5,
                    font=dict(color="#e2e8f5", size=20, family="IBM Plex Mono"),
                    showarrow=False,
                )],
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with ch_right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Click Timeline</div>', unsafe_allow_html=True)

            if clicks:
                df = pd.DataFrame(clicks)
                df["created_at"] = pd.to_datetime(df["created_at"])
                df["minute"] = df["created_at"].dt.floor("min")
                trend = df.groupby(["minute", "classification"]).size().reset_index(name="count")

                fig_line = go.Figure()
                for cls, color in [("VALID", LEGIT_COLOR), ("SUSPICIOUS", WARN_COLOR), ("FRAUD", FRAUD_COLOR)]:
                    sub = trend[trend["classification"] == cls]
                    if not sub.empty:
                        fig_line.add_trace(go.Scatter(
                            x=sub["minute"], y=sub["count"],
                            name=cls, mode="lines+markers",
                            line=dict(color=color, width=2),
                            marker=dict(size=5, color=color),
                            fill="tozeroy",
                            fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.06)",
                        ))

                fig_line = apply_chart_theme(fig_line, height=300)
                fig_line.update_layout(
                    xaxis_title="", yaxis_title="Clicks",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})

            st.markdown('</div>', unsafe_allow_html=True)

    # ── Click log table ────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Click Log</div>', unsafe_allow_html=True)

    if clicks:
        df_log = pd.DataFrame(clicks)
        df_log["created_at"] = pd.to_datetime(df_log["created_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")

        import json
        df_log["Reasons"] = df_log.get("reason_codes", pd.Series([[]] * len(df_log))).apply(
            lambda value: ", ".join(value if isinstance(value, list) else json.loads(value or "[]")))
        display_df = df_log[["id", "ip_address", "user_agent", "classification", "score", "decision", "Reasons", "model_version", "created_at"]].rename(columns={
            "id": "ID",
            "ip_address": "IP Address",
            "user_agent": "User Agent",
            "classification": "Classification",
            "score": "Risk Score", "decision": "Decision", "model_version": "Model",
            "created_at": "Timestamp",
        })

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=min(500, 60 + len(display_df) * 36),
            column_config={
                "ID":             st.column_config.NumberColumn("ID", width="small"),
                "IP Address":     st.column_config.TextColumn("IP Address", width="medium"),
                "User Agent":     st.column_config.TextColumn("User Agent", width="medium"),
                "Classification": st.column_config.TextColumn("Classification", width="small"),
                "Risk Score":     st.column_config.NumberColumn("Risk Score", format="%.3f", width="small"),
                "Decision":       st.column_config.TextColumn("Decision", width="small"),
                "Reasons":        st.column_config.TextColumn("Reasons", width="large"),
                "Model":          st.column_config.TextColumn("Model", width="small"),
                "Timestamp":      st.column_config.TextColumn("Timestamp", width="medium"),
            },
        )
    else:
        st.markdown(
            '<div style="height:120px; display:flex; align-items:center; justify-content:center; color:#2d3a52; font-size:0.85rem;">'
            'No clicks recorded yet. Use the simulate section above to test.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Refresh ────────────────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("↺ Refresh Data", key="refresh_detail"):
        st.rerun()
