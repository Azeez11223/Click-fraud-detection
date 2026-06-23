"""
pages/dashboard.py — Main Dashboard overview page
Enhanced with campaign overview section and fraud alerts.
"""
import streamlit as st
import pandas as pd
from components.api import (
    get_stats, get_clicks, get_metrics,
    get_campaigns, get_campaign_alerts,
)
from components.charts import pie_fraud_legit, line_click_trend, radar_model_metrics


def render():
    # ── Header ─────────────────────────────────────────────────────────────────
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown("""
        <div class="page-header">
            <div class="page-title">Operations Dashboard</div>
            <div class="page-subtitle">Real-time overview of click fraud detection activity</div>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        if st.button("↺ Refresh Data", use_container_width=True):
            st.rerun()

    # ── Global fraud alerts ────────────────────────────────────────────────────
    campaigns = get_campaigns()
    all_alerts = []
    for camp in campaigns:
        camp_alerts = get_campaign_alerts(camp["id"])
        for alert in camp_alerts:
            alert["campaign_name"] = camp["name"]
            all_alerts.append(alert)

    if all_alerts:
        for alert in all_alerts[:3]:  # Show up to 3 alerts
            level = alert.get("level", "high")
            msg = alert.get("message", "")
            cname = alert.get("campaign_name", "")
            if level == "critical":
                st.markdown(f'<div class="alert-critical">📢 <strong>{cname}</strong> — {msg}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-high">📢 <strong>{cname}</strong> — {msg}</div>', unsafe_allow_html=True)

    # ── Fetch data ─────────────────────────────────────────────────────────────
    stats   = get_stats()
    clicks  = get_clicks(limit=200)
    metrics = get_metrics()

    total      = stats.get("total", 0)
    fraud_cnt  = stats.get("fraud", 0)
    legit_cnt  = stats.get("legit", 0)
    fraud_rate = stats.get("fraud_rate", 0.0)

    # ── KPI Cards ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            label="Total Clicks Analyzed",
            value=f"{total:,}",
            delta="All time",
        )
    with c2:
        st.metric(
            label="Fraudulent Clicks",
            value=f"{fraud_cnt:,}",
            delta=f"{fraud_rate:.1f}% of total" if total else "—",
            delta_color="inverse",
        )
    with c3:
        st.metric(
            label="Genuine Clicks",
            value=f"{legit_cnt:,}",
            delta=f"{100-fraud_rate:.1f}% of total" if total else "—",
        )
    with c4:
        risk_level = (
            "🟢 LOW" if fraud_rate < 20
            else "🟡 MEDIUM" if fraud_rate < 50
            else "🔴 HIGH"
        )
        st.metric(
            label="Fraud Rate",
            value=f"{fraud_rate:.1f}%",
            delta=risk_level,
            delta_color="off",
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Campaign Quick Overview ────────────────────────────────────────────────
    if campaigns:
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div class="section-label" style="margin-bottom:0;">Your Campaigns</div>
        </div>
        """, unsafe_allow_html=True)

        # Campaign summary cards (compact)
        cols = st.columns(min(len(campaigns), 4))
        for i, camp in enumerate(campaigns[:4]):
            with cols[i]:
                cname = camp["name"]
                status = camp.get("status", "Active")
                click_ct = camp.get("click_count", 0)
                fraud_ct = camp.get("fraud_count", 0)
                s_color = "#34d399" if status == "Active" else "#fbbf24" if status == "Paused" else "#6b7a99"

                fraud_indicator = ""
                if fraud_ct >= 10:
                    fraud_indicator = '<div style="color:#f87171; font-size:0.68rem; margin-top:4px; font-weight:700;">⚠ FRAUD ALERT</div>'

                st.markdown(f"""
                <div class="card" style="padding:16px 18px; cursor:pointer;">
                    <div style="font-family:'Syne',sans-serif; font-size:0.88rem; font-weight:700; color:#e2e8f5; margin-bottom:6px;
                                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        {cname}
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-family:'IBM Plex Mono',monospace; font-size:1.1rem; font-weight:600; color:#e2e8f5;">{click_ct}</span>
                        <span style="color:{s_color}; font-size:0.68rem; font-weight:700; letter-spacing:1px;">{status.upper()}</span>
                    </div>
                    <div style="font-size:0.68rem; color:#4b5d7a; margin-top:2px;">clicks · {fraud_ct} fraud</div>
                    {fraud_indicator}
                </div>
                """, unsafe_allow_html=True)

                if st.button("View →", key=f"dash_camp_{camp['id']}", use_container_width=True):
                    st.session_state.selected_campaign_id = camp["id"]
                    st.session_state.page = "CampaignDetail"
                    st.rerun()

        # Quick create button
        if len(campaigns) < 4:
            with cols[-1] if len(campaigns) < 4 else st.columns(1)[0]:
                pass  # layout handled above

        qc1, qc2, qc3, qc4 = st.columns([1, 1, 1, 1])
        with qc1:
            if st.button("＋ New Campaign", key="dash_new_camp", use_container_width=True):
                st.session_state.page = "Campaigns"
                st.session_state.show_campaign_form = True
                st.rerun()
        with qc2:
            if st.button("📢 All Campaigns", key="dash_all_camps", use_container_width=True):
                st.session_state.page = "Campaigns"
                st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    else:
        # No campaigns yet — prompt
        st.markdown("""
        <div class="card" style="text-align:center; padding:24px;">
            <div style="font-size:1.5rem; margin-bottom:8px;">📢</div>
            <div style="color:#4b5d7a; font-size:0.85rem;">No campaigns yet — create one to start monitoring clicks.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("＋ Create Your First Campaign", key="dash_first_camp"):
            st.session_state.page = "Campaigns"
            st.session_state.show_campaign_form = True
            st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Charts Row 1 ───────────────────────────────────────────────────────────
    left, right = st.columns([1, 2])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Fraud Distribution</div>', unsafe_allow_html=True)
        if total > 0:
            fig = pie_fraud_legit(fraud_cnt, legit_cnt)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown(
                '<div style="height:260px; display:flex; align-items:center; justify-content:center; color:#2d3a52; font-size:0.85rem;">No data yet</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Click Activity Timeline</div>', unsafe_allow_html=True)
        if clicks:
            df = pd.DataFrame(clicks)
            fig = line_click_trend(df)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown(
                '<div style="height:260px; display:flex; align-items:center; justify-content:center; color:#2d3a52; font-size:0.85rem;">No click data yet. Submit predictions to see trends.</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Charts Row 2 ───────────────────────────────────────────────────────────
    left2, right2 = st.columns([2, 1])

    with left2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Recent Activity Feed</div>', unsafe_allow_html=True)
        if clicks:
            df_recent = pd.DataFrame(clicks[:10])
            df_recent["confidence"] = (df_recent["confidence"] * 100).round(1).astype(str) + "%"
            df_recent["created_at"] = pd.to_datetime(df_recent["created_at"]).dt.strftime("%H:%M:%S")

            # Color style
            def color_result(val):
                if val == "Fraud":
                    return "color: #f87171; font-weight: 700"
                return "color: #34d399; font-weight: 700"

            styled = (
                df_recent[["ip_address", "result", "confidence", "created_at"]]
                .rename(columns={"ip_address": "IP Address", "result": "Verdict",
                                  "confidence": "Score", "created_at": "Time"})
                .style
                .applymap(color_result, subset=["Verdict"])
                .set_table_styles([
                    {"selector": "th", "props": [
                        ("background-color", "#0d1229"),
                        ("color", "#4b5d7a"),
                        ("font-size", "10px"),
                        ("letter-spacing", "1.5px"),
                        ("text-transform", "uppercase"),
                        ("border-bottom", "1px solid rgba(255,255,255,0.06)"),
                    ]},
                    {"selector": "td", "props": [
                        ("background-color", "#07091a"),
                        ("color", "#c9d1e0"),
                        ("font-size", "0.83rem"),
                        ("border-bottom", "1px solid rgba(255,255,255,0.04)"),
                        ("font-family", "IBM Plex Mono, monospace"),
                    ]},
                ])
            )
            st.dataframe(
                df_recent[["ip_address", "result", "confidence", "created_at"]].rename(
                    columns={"ip_address": "IP Address", "result": "Verdict",
                              "confidence": "Score", "created_at": "Time"}
                ),
                use_container_width=True,
                hide_index=True,
                height=280,
            )
        else:
            st.markdown(
                '<div style="height:240px; display:flex; align-items:center; justify-content:center; color:#2d3a52; font-size:0.85rem;">No predictions yet</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with right2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Model Performance</div>', unsafe_allow_html=True)
        if metrics and not metrics.get("note"):
            # Mini metric bars
            for label, key in [("Accuracy", "accuracy"), ("Precision", "precision"),
                                ("Recall", "recall"), ("F1 Score", "f1_score")]:
                val = metrics.get(key, 0)
                pct = val * 100
                bar_color = "#3b82f6" if pct >= 80 else "#fbbf24" if pct >= 60 else "#f87171"
                st.markdown(f"""
                <div style="margin-bottom:14px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="font-size:0.77rem; color:#6b7a99; text-transform:uppercase; letter-spacing:1px;">{label}</span>
                        <span style="font-size:0.77rem; color:#c9d1e0; font-family:'IBM Plex Mono',monospace; font-weight:600;">{pct:.1f}%</span>
                    </div>
                    <div style="background:rgba(255,255,255,0.05); border-radius:4px; height:5px; overflow:hidden;">
                        <div style="background:{bar_color}; width:{pct}%; height:100%; border-radius:4px;
                             transition:width 0.6s ease;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            note = metrics.get("note", "Train the model first.") if metrics else "Train the model first."
            st.markdown(
                f'<div style="color:#4b5d7a; font-size:0.82rem; padding:20px 0;">{note}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)
