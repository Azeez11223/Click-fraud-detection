"""
pages/campaign_detail.py — Single campaign detail page with stats, charts, click log, and alerts
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from components.api import (
    get_campaign, get_campaign_clicks_api,
    get_campaign_stats, get_campaign_alerts,
    get_threshold_analysis, set_campaign_block_threshold, update_campaign_economics,
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

    economics = get_threshold_analysis(campaign_id)
    if economics:
        with st.expander("Campaign cost assumptions", expanded=False):
            with st.form(f"economics_{campaign_id}"):
                cost_a, cost_b, cost_c = st.columns(3)
                with cost_a:
                    cpc = st.number_input("Cost per click", min_value=0.0,
                        value=float(campaign.get("cpc", 0.5)), step=0.05)
                with cost_b:
                    conversion_value = st.number_input("Average conversion value", min_value=0.0,
                        value=float(campaign.get("avg_conversion_value", 25.0)), step=1.0)
                with cost_c:
                    conversion_rate = st.number_input("Expected conversion rate", min_value=0.0,
                        max_value=1.0, value=float(campaign.get("expected_conversion_rate", 0.02)), step=0.01,
                        format="%.3f")
                if st.form_submit_button("Save cost assumptions"):
                    result, status = update_campaign_economics(
                        campaign_id, cpc, conversion_value, conversion_rate)
                    if status == 200:
                        st.rerun()
                    st.error(result.get("detail", "Could not save cost assumptions"))
        recommended = float(economics.get("recommended_block_threshold", 0.75))
        active_threshold = float(economics.get("active_block_threshold", recommended))
        selected_threshold = st.slider("Block sensitivity (risk score)", 0.01, 1.0,
            min(1.0, max(0.01, active_threshold)), 0.01, key=f"threshold_{campaign_id}")
        if abs(selected_threshold - active_threshold) > 0.0001:
            result, status = set_campaign_block_threshold(campaign_id, selected_threshold)
            if status == 200:
                active_threshold = selected_threshold
            else:
                st.error(result.get("detail", "Could not save campaign threshold"))
        estimate = get_threshold_analysis(campaign_id, selected_threshold).get("analysis", {})
        st.caption(f"Recommended: {recommended:.2f} · Active for future decisions: {active_threshold:.2f}. What-if uses up to 500 historical clicks; estimates are not realized savings.")
        e1, e2, e3 = st.columns(3)
        e1.metric("Estimated wasted spend saved", f"${estimate.get('estimated_wasted_spend_saved', 0):,.2f}")
        e2.metric("Estimated legitimate conversions lost", f"{estimate.get('estimated_legitimate_conversions_lost', 0):.2f}")
        e3.metric("Estimated conversion value lost", f"${estimate.get('estimated_conversion_value_lost', 0):,.2f}")

    # ── KPI cards ──────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("Total Clicks",      f"{total:,}")
    with k2: st.metric("Valid Clicks",       f"{valid_cnt:,}")
    with k3: st.metric("Suspicious",         f"{sus_cnt:,}")
    with k4: st.metric("Fraud Clicks",       f"{fraud_cnt:,}")
    with k5: st.metric("Fraud Rate",         f"{fraud_rate:.1f}%")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    st.info("Click events use the campaign authenticated API key. For sample data, run `python -m data.seed_demo --user-id <your-user-id>` to create an explicitly synthetic demo campaign.")

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
