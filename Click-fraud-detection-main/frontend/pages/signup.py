"""
pages/signup.py — Signup page for AdShield
"""
import streamlit as st
from components.api import auth_signup, check_api_health


def render():
    # Centred auth card
    st.markdown("""
    <div style="display:flex; justify-content:center; align-items:center; min-height:80vh;">
        <div style="width:100%; max-width:440px;">
            <div style="text-align:center; margin-bottom:32px;">
                <div class="logo-text" style="font-size:2rem;">Ad<span class="logo-accent">Shield</span></div>
                <div class="logo-version" style="font-size:0.72rem; margin-top:4px;">FRAUD DETECTION PLATFORM v2.0</div>
            </div>
    """, unsafe_allow_html=True)

    # API status check
    api_ok = check_api_health()
    if not api_ok:
        st.markdown("""
        <div style="max-width:440px; margin:0 auto 16px auto;">
            <div style="background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25);
                        border-radius:10px; padding:14px 18px; text-align:center;">
                <span class="offline-dot"></span>
                <span style="color:#f87171; font-size:0.82rem; font-weight:600;">API Offline</span>
                <div style="color:#4b5d7a; font-size:0.75rem; margin-top:6px;">
                    Start backend: <code style="color:#60a5fa;">uvicorn backend.main:app --reload</code>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Signup form
    col_pad1, col_form, col_pad2 = st.columns([1, 2, 1])
    with col_form:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title" style="text-align:center; margin-bottom:20px;">Create Account</div>', unsafe_allow_html=True)

        with st.form("signup_form", clear_on_submit=False):
            name = st.text_input("Full Name", placeholder="John Doe")
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="Min 6 characters")
            confirm  = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🚀 Create Account", use_container_width=True)

        if submitted:
            if not name or not email or not password or not confirm:
                st.error("Please fill in all fields")
            elif password != confirm:
                st.error("Passwords do not match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                result, code = auth_signup(name, email, password)
                if code == 200:
                    st.success("Account created! Redirecting to login…")
                    st.session_state.auth_page = "Login"
                    st.rerun()
                else:
                    st.error(result.get("detail", "Signup failed"))

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center; font-size:0.82rem; color:#4b5d7a;">'
            "Already have an account?"
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("← Sign In", use_container_width=True, key="go_login"):
            st.session_state.auth_page = "Login"
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)
