"""
pages/history.py — Prediction History page
"""
import streamlit as st
import pandas as pd
from components.api import get_clicks


def render():
    # ── Header ─────────────────────────────────────────────────────────────────
    col_h, col_btn = st.columns([4, 1])
    with col_h:
        st.markdown("""
        <div class="page-header">
            <div class="page-title">Prediction History</div>
            <div class="page-subtitle">Complete log of all analyzed click events with filter controls</div>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        if st.button("↺ Refresh", use_container_width=True):
            st.rerun()

    # ── Fetch data ─────────────────────────────────────────────────────────────
    clicks = get_clicks(limit=200)

    if not clicks:
        st.markdown("""
        <div class="card" style="text-align:center; padding:60px 24px;">
            <div style="font-size:2.5rem; margin-bottom:12px;">📋</div>
            <div style="color:#4b5d7a; font-size:0.9rem;">No prediction history found.</div>
            <div style="color:#2d3a52; font-size:0.82rem; margin-top:6px;">Predictions will appear here after you submit clicks on the Predict page.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    df = pd.DataFrame(clicks)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["confidence_pct"] = (df["confidence"] * 100).round(2)

    # ── Filters ────────────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Filters</div>', unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])

    with f1:
        ip_filter = st.text_input("Filter by IP Address", placeholder="e.g. 192.168.", label_visibility="visible")
    with f2:
        verdict_filter = st.selectbox("Verdict", ["All", "Fraud", "Legit"])
    with f3:
        min_conf = st.number_input("Min Confidence %", min_value=0, max_value=100, value=0, step=5)
    with f4:
        max_conf = st.number_input("Max Confidence %", min_value=0, max_value=100, value=100, step=5)

    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    filtered = df.copy()
    if ip_filter:
        filtered = filtered[filtered["ip_address"].str.contains(ip_filter, na=False)]
    if verdict_filter != "All":
        filtered = filtered[filtered["result"] == verdict_filter]
    filtered = filtered[
        (filtered["confidence_pct"] >= min_conf) &
        (filtered["confidence_pct"] <= max_conf)
    ]

    # ── Summary strip ───────────────────────────────────────────────────────────
    fraud_cnt = (filtered["result"] == "Fraud").sum()
    legit_cnt = (filtered["result"] == "Legit").sum()
    rate      = fraud_cnt / len(filtered) * 100 if len(filtered) > 0 else 0

    s1, s2, s3, s4 = st.columns(4)
    with s1: st.metric("Showing",    f"{len(filtered):,} records")
    with s2: st.metric("Fraud",      f"{fraud_cnt:,}")
    with s3: st.metric("Legitimate", f"{legit_cnt:,}")
    with s4: st.metric("Fraud Rate", f"{rate:.1f}%")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Table ──────────────────────────────────────────────────────────────────
    if filtered.empty:
        st.markdown("""
        <div class="card" style="text-align:center; padding:40px;">
            <div style="color:#4b5d7a; font-size:0.85rem;">No records match the current filters.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Prepare display dataframe
    display_df = filtered[["id", "ip_address", "result", "confidence_pct", "created_at"]].copy()
    display_df["created_at"] = display_df["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    display_df["risk_level"] = display_df.apply(
        lambda row: _risk_label(row["confidence_pct"] / 100, row["result"]), axis=1
    )
    display_df = display_df.rename(columns={
        "id":             "ID",
        "ip_address":     "IP Address",
        "result":         "Verdict",
        "confidence_pct": "Score (%)",
        "created_at":     "Timestamp",
        "risk_level":     "Risk Level",
    })
    display_df = display_df.sort_values("ID", ascending=False)

    st.markdown('<div class="card" style="padding:0; overflow:hidden;">', unsafe_allow_html=True)

    def color_verdict(val):
        if val == "Fraud":
            return "color: #f87171; font-weight: 700; font-family: 'IBM Plex Mono', monospace;"
        return "color: #34d399; font-weight: 700; font-family: 'IBM Plex Mono', monospace;"

    def color_risk(val):
        if "HIGH" in str(val):
            return "color: #f87171;"
        elif "MEDIUM" in str(val):
            return "color: #fbbf24;"
        return "color: #34d399;"

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=min(600, 60 + len(display_df) * 36),
        column_config={
            "ID":         st.column_config.NumberColumn("ID", width="small"),
            "IP Address": st.column_config.TextColumn("IP Address", width="medium"),
            "Verdict":    st.column_config.TextColumn("Verdict", width="small"),
            "Score (%)":  st.column_config.NumberColumn("Score (%)", format="%.2f", width="small"),
            "Timestamp":  st.column_config.TextColumn("Timestamp", width="medium"),
            "Risk Level": st.column_config.TextColumn("Risk Level", width="small"),
        },
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Export hint ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-top:12px; text-align:right;">
        <span style="font-size:0.75rem; color:#2d3a52; font-family:'IBM Plex Mono',monospace;">
            Showing up to 200 most recent records · Use the Streamlit table download button to export CSV
        </span>
    </div>
    """, unsafe_allow_html=True)


def _risk_label(confidence: float, verdict: str) -> str:
    prob = confidence if verdict == "Fraud" else 1 - confidence
    if prob < 0.35:
        return "LOW"
    elif prob < 0.65:
        return "MEDIUM"
    return "HIGH"
