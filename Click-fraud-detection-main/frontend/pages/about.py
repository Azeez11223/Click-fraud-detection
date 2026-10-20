"""
pages/about.py — About / Info page
"""
import streamlit as st


def render():
    st.markdown("""
    <div class="page-header">
        <div class="page-title">About AdShield</div>
        <div class="page-subtitle">Platform overview, architecture, and technical documentation</div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Project overview
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Project Overview</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.9rem; color:#8b9bbf; line-height:1.8;">
            <p>
                <strong style="color:#c9d1e0;">AdShield</strong> is a production-grade click fraud detection platform
                built for ad-tech operations. It uses machine learning to identify fraudulent ad clicks in real-time,
                protecting advertisers from wasted budget and inflated metrics.
            </p>
            <p>
                The system analyzes incoming click events against a set of behavioral signals — including click
                frequency, timing patterns, device fingerprinting, and geographic anomalies — to assign a fraud
                probability score to each click within milliseconds.
            </p>
            <p>
                Built as a final-year project demonstrating the full MLOps pipeline: from data generation and
                model training to REST API deployment and real-time dashboard monitoring.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # How it works
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">How It Works</div>', unsafe_allow_html=True)

        steps = [
            ("01", "Data Ingestion", "Click events arrive via POST /predict with IP, device, browser, geo, and timing attributes."),
            ("02", "Feature Engineering", "Raw data is transformed: timestamps → hour extraction, click intervals → bot-behavior flags, IP frequency analysis."),
            ("03", "ML Inference", "XGBoost model evaluates engineered features and returns a fraud probability score (0–1)."),
            ("04", "Risk Classification", "Score mapped to Low / Medium / High risk tier. Verdict stored to SQLite for audit trail."),
            ("05", "Dashboard Update", "Results surface instantly in the Operations Dashboard with live metrics and visualizations."),
        ]

        for num, title, desc in steps:
            st.markdown(f"""
            <div style="display:flex; gap:16px; margin-bottom:20px; align-items:flex-start;">
                <div style="
                    min-width:36px; height:36px;
                    background:rgba(59,130,246,0.1);
                    border:1px solid rgba(59,130,246,0.2);
                    border-radius:8px;
                    display:flex; align-items:center; justify-content:center;
                    font-family:'IBM Plex Mono',monospace; font-size:0.7rem;
                    font-weight:600; color:#3b82f6;
                ">{num}</div>
                <div>
                    <div style="font-weight:600; color:#c9d1e0; font-size:0.88rem; margin-bottom:3px;">{title}</div>
                    <div style="font-size:0.81rem; color:#6b7a99; line-height:1.5;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        # Tech stack
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Tech Stack</div>', unsafe_allow_html=True)

        stack = [
            ("🤖", "XGBoost", "Gradient boosted classifier for fraud detection with SMOTE imbalance handling"),
            ("⚡", "FastAPI",  "High-performance async REST API backend with automatic OpenAPI docs"),
            ("🎯", "Streamlit","Interactive multi-page dashboard frontend"),
            ("🗃️", "SQLite",   "Lightweight embedded database for click and prediction persistence"),
            ("📊", "Plotly",   "Interactive charting library for analytics visualizations"),
            ("🔬", "scikit-learn", "Preprocessing, label encoding, and evaluation metrics"),
            ("🐍", "Python 3.10+", "Core language across ML pipeline, API, and frontend"),
        ]

        for icon, name, desc in stack:
            st.markdown(f"""
            <div style="
                display:flex; align-items:flex-start; gap:12px;
                padding:12px 0;
                border-bottom:1px solid rgba(255,255,255,0.04);
            ">
                <span style="font-size:1.2rem; line-height:1.4;">{icon}</span>
                <div>
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.82rem; font-weight:600; color:#93c5fd; margin-bottom:2px;">{name}</div>
                    <div style="font-size:0.78rem; color:#4b5d7a; line-height:1.4;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # API Reference
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">API Endpoints</div>', unsafe_allow_html=True)

        endpoints = [
            ("POST", "/predict", "Analyze a click event for fraud"),
            ("POST", "/train",   "Train XGBoost on dataset.csv"),
            ("GET",  "/metrics", "Return model evaluation metrics"),
            ("GET",  "/clicks",  "Fetch recent prediction records"),
            ("GET",  "/stats",   "Aggregated fraud vs legit counts"),
            ("GET",  "/",        "API health check"),
        ]

        for method, path, desc in endpoints:
            method_color = "#34d399" if method == "GET" else "#fbbf24"
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:8px; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.04);">
                <span style="
                    font-family:'IBM Plex Mono',monospace; font-size:0.65rem; font-weight:700;
                    color:{method_color}; background:rgba(255,255,255,0.04);
                    padding:2px 7px; border-radius:4px; min-width:38px; text-align:center;
                ">{method}</span>
                <span style="font-family:'IBM Plex Mono',monospace; font-size:0.78rem; color:#93c5fd; flex:1;">{path}</span>
                <span style="font-size:0.72rem; color:#4b5d7a;">{desc}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:12px; font-size:0.75rem; color:#2d3a52;">
            📚 Full OpenAPI docs available at <span style="color:#3b82f6; font-family:'IBM Plex Mono',monospace;">http://localhost:8000/docs</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Run instructions
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Quick Start</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.77rem; color:#6b7a99; line-height:2;">
            <div style="color:#4b5d7a; margin-bottom:8px; font-size:0.7rem; letter-spacing:1px;">TERMINAL 1 — BACKEND</div>
            <div style="background:#030508; border-radius:6px; padding:12px 14px; margin-bottom:12px; border:1px solid rgba(255,255,255,0.05);">
                <span style="color:#34d399;">cd</span> click-fraud-project<br>
                <span style="color:#34d399;">uvicorn</span> backend.main:app --reload
            </div>
            <div style="color:#4b5d7a; margin-bottom:8px; font-size:0.7rem; letter-spacing:1px;">TERMINAL 2 — FRONTEND</div>
            <div style="background:#030508; border-radius:6px; padding:12px 14px; border:1px solid rgba(255,255,255,0.05);">
                <span style="color:#34d399;">streamlit</span> run frontend/app.py
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
