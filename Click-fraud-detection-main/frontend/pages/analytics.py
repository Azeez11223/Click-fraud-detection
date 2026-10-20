"""
pages/analytics.py — Analytics & Insights page
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from components.api import get_stats, get_clicks, get_metrics
from components.charts import (
    bar_hourly_activity,
    bar_confidence_distribution,
    radar_model_metrics,
    pie_fraud_legit,
    apply_chart_theme,
    FRAUD_COLOR, LEGIT_COLOR, BLUE_COLOR,
)


def render():
    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Analytics & Insights</div>
        <div class="page-subtitle">Deep-dive into fraud patterns, model performance, and click behaviour</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Fetch data ─────────────────────────────────────────────────────────────
    stats   = get_stats()
    clicks  = get_clicks(limit=500)
    metrics = get_metrics()

    if not clicks:
        st.markdown("""
        <div class="card" style="text-align:center; padding:60px 24px;">
            <div style="font-size:2.5rem; margin-bottom:12px;">📊</div>
            <div style="color:#4b5d7a; font-size:0.9rem;">No prediction data available yet.</div>
            <div style="color:#2d3a52; font-size:0.82rem; margin-top:6px;">Submit predictions on the Predict page to populate analytics.</div>
        </div>
        """, unsafe_allow_html=True)
        # Still show model metrics if available
        if metrics and not metrics.get("note"):
            _render_model_section(metrics)
        return

    df = pd.DataFrame(clicks)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["confidence"] = df["confidence"].astype(float)

    # ── Summary bar ────────────────────────────────────────────────────────────
    total = stats.get("total", 0)
    fraud = stats.get("fraud", 0)
    legit = stats.get("legit", 0)
    rate  = stats.get("fraud_rate", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("Total Records",  f"{total:,}")
    with c2: st.metric("Fraud",          f"{fraud:,}")
    with c3: st.metric("Legitimate",     f"{legit:,}")
    with c4: st.metric("Fraud Rate",     f"{rate:.1f}%")
    with c5:
        avg_conf = df[df["result"] == "Fraud"]["confidence"].mean() if fraud > 0 else 0
        st.metric("Avg Fraud Score", f"{avg_conf*100:.1f}%" if fraud > 0 else "—")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Row 1: Distribution + Hourly ───────────────────────────────────────────
    col_a, col_b = st.columns([1, 2])

    with col_a:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Fraud Breakdown</div>', unsafe_allow_html=True)
        if total > 0:
            fig = pie_fraud_legit(fraud, legit)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Activity by Hour of Day</div>', unsafe_allow_html=True)
        fig = bar_hourly_activity(df)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Row 2: Confidence distribution + IP heatmap ────────────────────────────
    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Confidence Score Distribution</div>', unsafe_allow_html=True)
        fig = bar_confidence_distribution(df)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_d:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Top IPs by Activity</div>', unsafe_allow_html=True)

        ip_counts = (
            df.groupby(["ip_address", "result"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(10)
        )

        if not ip_counts.empty:
            colors = [FRAUD_COLOR if r == "Fraud" else LEGIT_COLOR for r in ip_counts["result"]]
            fig_ip = go.Figure(go.Bar(
                x=ip_counts["count"],
                y=ip_counts["ip_address"],
                orientation="h",
                marker=dict(color=colors),
                hovertemplate="<b>%{y}</b><br>Clicks: %{x}<extra></extra>",
            ))
            fig_ip = apply_chart_theme(fig_ip, height=280)
            fig_ip.update_layout(
                yaxis=dict(autorange="reversed"),
                xaxis_title="Prediction Count",
                showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_ip, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<div style="color:#2d3a52; font-size:0.85rem; padding:20px 0;">No IP data</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Row 3: Cumulative trend ─────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Cumulative Fraud Detection Over Time</div>', unsafe_allow_html=True)

    df_sorted = df.sort_values("created_at")
    df_sorted["cum_total"] = range(1, len(df_sorted) + 1)
    df_sorted["is_fraud_bin"] = (df_sorted["result"] == "Fraud").astype(int)
    df_sorted["cum_fraud"] = df_sorted["is_fraud_bin"].cumsum()
    df_sorted["cum_legit"] = df_sorted["cum_total"] - df_sorted["cum_fraud"]

    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(
        x=df_sorted["created_at"], y=df_sorted["cum_legit"],
        name="Legitimate", line=dict(color=LEGIT_COLOR, width=2),
        fill="tozeroy", fillcolor="rgba(52,211,153,0.05)",
    ))
    fig_cum.add_trace(go.Scatter(
        x=df_sorted["created_at"], y=df_sorted["cum_fraud"],
        name="Fraud", line=dict(color=FRAUD_COLOR, width=2),
        fill="tozeroy", fillcolor="rgba(248,113,113,0.05)",
    ))
    fig_cum = apply_chart_theme(fig_cum, height=280)
    fig_cum.update_layout(
        hovermode="x unified",
        xaxis_title="",
        yaxis_title="Cumulative Count",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_cum, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Model metrics section ───────────────────────────────────────────────────
    _render_model_section(metrics)


def _render_model_section(metrics):
    """Render the model performance section."""
    st.markdown("""
    <div style="margin-top:8px;">
        <div class="page-header" style="margin-bottom:12px; padding-bottom:8px;">
            <div style="font-family:'Syne',sans-serif; font-size:1.2rem; font-weight:700; color:#e2e8f5;">
                Model Performance
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if metrics and not metrics.get("note"):
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        for col, label, key in [
            (col_m1, "Accuracy",  "accuracy"),
            (col_m2, "Precision", "precision"),
            (col_m3, "Recall",    "recall"),
            (col_m4, "F1 Score",  "f1_score"),
        ]:
            with col:
                col.metric(label, f"{metrics.get(key,0)*100:.1f}%")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        col_r, col_info = st.columns([1, 1])
        with col_r:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Performance Radar</div>', unsafe_allow_html=True)
            fig = radar_model_metrics(metrics)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with col_info:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Metric Definitions</div>', unsafe_allow_html=True)
            defs = [
                ("Accuracy",  "Overall % of correct predictions (Fraud + Legit)"),
                ("Precision", "Of all Fraud predictions, how many were actually Fraud"),
                ("Recall",    "Of all actual Fraud cases, how many were caught"),
                ("F1 Score",  "Harmonic mean of Precision and Recall — balanced measure"),
            ]
            for term, definition in defs:
                st.markdown(f"""
                <div style="margin-bottom:16px;">
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.78rem; color:#3b82f6; font-weight:600; margin-bottom:3px;">{term}</div>
                    <div style="font-size:0.82rem; color:#6b7a99; line-height:1.5;">{definition}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        note = metrics.get("note", "Train the model first.") if metrics else "Train the model first."
        st.markdown(f"""
        <div class="card" style="text-align:center; padding:40px;">
            <div style="font-size:2rem; margin-bottom:8px;">🎯</div>
            <div style="color:#4b5d7a; font-size:0.85rem;">{note}</div>
        </div>
        """, unsafe_allow_html=True)
