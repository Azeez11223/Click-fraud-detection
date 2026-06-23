"""
pages/predict.py — Predict Fraud page
"""
import random
import streamlit as st
from datetime import datetime
from components.api import api_post
from components.charts import gauge_confidence


# ── Risk level helper ──────────────────────────────────────────────────────────
def get_risk_level(prob: float) -> tuple[str, str]:
    """Returns (label, css_class) for risk level."""
    if prob < 0.35:
        return "LOW RISK", "risk-low"
    elif prob < 0.65:
        return "MEDIUM RISK", "risk-medium"
    else:
        return "HIGH RISK", "risk-high"


# ── Sample data generator ──────────────────────────────────────────────────────
def generate_sample(suspicious: bool = False):
    """Generate a random click record, optionally suspicious."""
    ips_sus = ["45.33.32.156", "192.241.235.180", "10.0.0.99", "198.51.100.5"]
    ips_legit = ["72.14.204.99", "142.250.64.14", "17.172.224.47", "203.0.113.42"]

    if suspicious:
        return {
            "ip_address":     random.choice(ips_sus),
            "device_type":    "mobile",
            "browser":        random.choice(["Chrome", "Firefox"]),
            "timestamp":      datetime.now().replace(hour=random.randint(0, 5)).strftime("%Y-%m-%d %H:%M:%S"),
            "geo_location":   random.choice(["CN", "RU", "BR"]),
            "click_interval": round(random.uniform(0.1, 1.5), 2),
            "ip_click_count": random.randint(80, 300),
        }
    else:
        return {
            "ip_address":     random.choice(ips_legit),
            "device_type":    random.choice(["desktop", "mobile"]),
            "browser":        random.choice(["Chrome", "Safari", "Firefox"]),
            "timestamp":      datetime.now().replace(hour=random.randint(9, 17)).strftime("%Y-%m-%d %H:%M:%S"),
            "geo_location":   random.choice(["US", "GB", "AU", "DE"]),
            "click_interval": round(random.uniform(3.0, 30.0), 2),
            "ip_click_count": random.randint(1, 30),
        }


def render():
    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Fraud Prediction</div>
        <div class="page-subtitle">Submit click attributes to analyze for fraudulent behaviour in real-time</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sample input buttons ───────────────────────────────────────────────────
    st.markdown('<div class="section-label">Quick Fill</div>', unsafe_allow_html=True)
    btn1, btn2, _, _ = st.columns([1, 1, 2, 2])
    sample = None
    with btn1:
        if st.button("🤖 Suspicious Sample", use_container_width=True):
            sample = generate_sample(suspicious=True)
            st.session_state["_sample"] = sample
    with btn2:
        if st.button("✅ Legitimate Sample", use_container_width=True):
            sample = generate_sample(suspicious=False)
            st.session_state["_sample"] = sample

    # Read from session state
    pre = st.session_state.get("_sample", {})

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Prediction Form ────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Click Attributes</div>', unsafe_allow_html=True)

    with st.form("predict_form", clear_on_submit=False):
        row1_col1, row1_col2, row1_col3 = st.columns(3)

        with row1_col1:
            ip_address = st.text_input(
                "IP Address",
                value=pre.get("ip_address", "192.168.1.5"),
                placeholder="e.g. 203.45.67.89",
            )
            device_type = st.selectbox(
                "Device Type",
                ["mobile", "desktop", "tablet"],
                index=["mobile", "desktop", "tablet"].index(
                    pre.get("device_type", "mobile")
                ) if pre.get("device_type") in ["mobile", "desktop", "tablet"] else 0,
            )

        with row1_col2:
            browser = st.selectbox(
                "Browser",
                ["Chrome", "Firefox", "Safari", "Edge", "Opera"],
                index=["Chrome", "Firefox", "Safari", "Edge", "Opera"].index(
                    pre.get("browser", "Chrome")
                ) if pre.get("browser") in ["Chrome", "Firefox", "Safari", "Edge", "Opera"] else 0,
            )
            geo_location = st.selectbox(
                "Geo Location",
                ["US", "IN", "CN", "BR", "RU", "DE", "GB", "FR", "JP", "AU"],
                index=["US", "IN", "CN", "BR", "RU", "DE", "GB", "FR", "JP", "AU"].index(
                    pre.get("geo_location", "US")
                ) if pre.get("geo_location") in ["US", "IN", "CN", "BR", "RU", "DE", "GB", "FR", "JP", "AU"] else 0,
            )

        with row1_col3:
            timestamp = st.text_input(
                "Timestamp",
                value=pre.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                placeholder="YYYY-MM-DD HH:MM:SS",
            )

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        row2_col1, row2_col2, row2_col3 = st.columns(3)
        with row2_col1:
            click_interval = st.number_input(
                "Click Interval (seconds)",
                min_value=0.0,
                value=float(pre.get("click_interval", 1.2)),
                step=0.1,
                help="Time since last click from this IP address",
            )
        with row2_col2:
            ip_click_count = st.number_input(
                "IP Click Count",
                min_value=0,
                value=int(pre.get("ip_click_count", 150)),
                step=1,
                help="Total number of clicks recorded from this IP",
            )
        with row2_col3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "⚡ Analyze for Fraud",
                use_container_width=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Result ─────────────────────────────────────────────────────────────────
    if submitted:
        payload = {
            "ip_address":     ip_address,
            "device_type":    device_type,
            "browser":        browser,
            "timestamp":      timestamp,
            "click_interval": click_interval,
            "ip_click_count": ip_click_count,
            "geo_location":   geo_location,
        }

        with st.spinner("Analyzing click patterns…"):
            result, code = api_post("/predict", payload)

        if code == 200:
            pred = result["prediction"]
            conf = result["confidence"]
            is_fraud = pred == "Fraud"
            risk_label, risk_class = get_risk_level(conf if is_fraud else 1 - conf)

            # Save to session history
            st.session_state.history.append({
                "IP": ip_address,
                "Timestamp": timestamp,
                "Verdict": pred,
                "Score": f"{conf*100:.1f}%",
                "Risk": risk_label,
            })
            st.session_state.last_prediction = result

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # Result layout
            res_left, res_right = st.columns([1.8, 1])

            with res_left:
                if is_fraud:
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(239,68,68,0.08), rgba(220,38,38,0.04));
                        border: 1px solid rgba(239,68,68,0.25);
                        border-left: 4px solid #ef4444;
                        border-radius: 12px;
                        padding: 24px 28px;
                        margin-bottom: 16px;
                    ">
                        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.72rem; letter-spacing:2px; color:#f87171; margin-bottom:10px; text-transform:uppercase;">⚠ Detection Result</div>
                        <div style="font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; color:#f87171; margin-bottom:8px;">FRAUD DETECTED</div>
                        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                            <span class="badge-fraud">🚨 {pred.upper()}</span>
                            <span class="{risk_class}">{risk_label}</span>
                        </div>
                        <div style="margin-top:16px; color:#6b7a99; font-size:0.83rem; line-height:1.6;">
                            This click exhibits high-risk patterns consistent with automated bot traffic or
                            click fraud. Confidence score: <strong style="color:#f87171; font-family:'IBM Plex Mono',monospace;">{conf*100:.1f}%</strong>.
                            Recommend blocking this IP.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(5,150,105,0.04));
                        border: 1px solid rgba(16,185,129,0.25);
                        border-left: 4px solid #10b981;
                        border-radius: 12px;
                        padding: 24px 28px;
                        margin-bottom: 16px;
                    ">
                        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.72rem; letter-spacing:2px; color:#34d399; margin-bottom:10px; text-transform:uppercase;">✓ Detection Result</div>
                        <div style="font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; color:#34d399; margin-bottom:8px;">GENUINE CLICK</div>
                        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                            <span class="badge-legit">✅ {pred.upper()}</span>
                            <span class="{risk_class}">{risk_label}</span>
                        </div>
                        <div style="margin-top:16px; color:#6b7a99; font-size:0.83rem; line-height:1.6;">
                            This click matches normal human behaviour patterns. Fraud probability:
                            <strong style="color:#34d399; font-family:'IBM Plex Mono',monospace;">{conf*100:.1f}%</strong>.
                            No action required.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Attribute summary
                st.markdown('<div class="card" style="margin-top:0">', unsafe_allow_html=True)
                st.markdown('<div class="card-title">Submitted Attributes</div>', unsafe_allow_html=True)
                attrs = [
                    ("IP Address", ip_address),
                    ("Device", device_type.title()),
                    ("Browser", browser),
                    ("Location", geo_location),
                    ("Click Interval", f"{click_interval}s"),
                    ("IP Click Count", str(ip_click_count)),
                    ("Hour", str(pd_safe_hour(timestamp))),
                ]
                for label, val in attrs:
                    st.markdown(
                        f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{val}</span></div>',
                        unsafe_allow_html=True,
                    )
                st.markdown('</div>', unsafe_allow_html=True)

            with res_right:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                fig = gauge_confidence(conf, is_fraud)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown(f"""
                <div style="text-align:center; margin-top:8px;">
                    <div style="font-size:0.72rem; color:#4b5d7a; letter-spacing:1.5px; text-transform:uppercase; font-family:'IBM Plex Mono',monospace; margin-bottom:6px;">Confidence Score</div>
                    <div style="font-size:2.5rem; font-family:'IBM Plex Mono',monospace; font-weight:600; color:{'#f87171' if is_fraud else '#34d399'};">{conf*100:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.error(f"API Error {code}: {result.get('detail', 'Unknown error')}")
            if code == 503:
                st.info("💡 The model hasn't been trained yet. Use the 'Train Model' button in the sidebar.")


def pd_safe_hour(ts: str) -> int:
    """Safely parse hour from timestamp string."""
    try:
        import pandas as pd
        return pd.to_datetime(ts).hour
    except Exception:
        return 0
