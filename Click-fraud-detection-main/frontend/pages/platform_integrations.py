"""
pages/platform_integrations.py — Platform Integrations Hub
AdShield v3 — Google Ads & Facebook Ads integration management,
live account health, budget tracking, and per-campaign fraud attribution.
"""
import random
import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from components.api import (
    get_campaigns,
    get_platform_stats,
    get_hourly_breakdown,
    get_realtime_feed,
    send_platform_event,
    get_ip_list_counts,
)

# ── Brand colours ──────────────────────────────────────────────────────────────
GOOGLE_COLOR   = "#4285f4"
GOOGLE_BG      = "rgba(66,133,244,0.10)"
GOOGLE_BORDER  = "rgba(66,133,244,0.30)"
FACEBOOK_COLOR = "#1877f2"
FACEBOOK_BG    = "rgba(24,119,242,0.10)"
FACEBOOK_BORDER= "rgba(24,119,242,0.30)"
FRAUD_COLOR    = "#f87171"
VALID_COLOR    = "#34d399"
WARN_COLOR     = "#fbbf24"

COUNTRIES = ["US","IN","CN","BR","RU","DE","GB","FR","JP","AU","NG","MX","ID","CA","ZA"]
DEVICES   = ["mobile","desktop","tablet"]
BROWSERS  = ["Chrome","Firefox","Safari","Edge","Opera"]

def _rand_ip():
    return f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def _bot_ip():
    return f"185.{random.randint(100,180)}.{random.randint(0,255)}.{random.randint(1,254)}"

# ── Shared session-state defaults ──────────────────────────────────────────────
def _init_state():
    defaults = {
        "google_connected":   st.session_state.get("google_connected", False),
        "facebook_connected": st.session_state.get("facebook_connected", False),
        "google_account":     st.session_state.get("google_account", ""),
        "facebook_account":   st.session_state.get("facebook_account", ""),
        "google_budget":      st.session_state.get("google_budget", 500.0),
        "facebook_budget":    st.session_state.get("facebook_budget", 300.0),
        "pi_tab":             st.session_state.get("pi_tab", "overview"),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── Platform connection card ───────────────────────────────────────────────────
def _connection_card(name, color, bg, border, logo_svg, connected_key, account_key, budget_key):
    connected = st.session_state.get(connected_key, False)
    account   = st.session_state.get(account_key, "")
    budget    = st.session_state.get(budget_key, 500.0)

    status_dot   = f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{"#34d399" if connected else "#374151"};margin-right:6px;"></span>'
    status_label = "Connected" if connected else "Not connected"
    status_color = "#34d399" if connected else "#4b5d7a"

    st.markdown(f"""
    <div style="border:1px solid {border if connected else 'rgba(255,255,255,0.07)'};
                border-radius:16px; padding:24px 28px; background:{bg if connected else '#0d1229'};
                transition:all 0.3s ease; margin-bottom:4px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:18px;">
            <div style="display:flex; align-items:center; gap:14px;">
                {logo_svg}
                <div>
                    <div style="font-family:'Syne',sans-serif; font-size:1.05rem; font-weight:700; color:#e2e8f5;">{name} Ads</div>
                    <div style="font-size:0.75rem; color:{status_color}; margin-top:3px;">
                        {status_dot}{status_label}
                    </div>
                </div>
            </div>
            {"" if not connected else f'<div style="font-family:IBM Plex Mono,monospace; font-size:0.72rem; color:#4b5d7a; margin-top:4px;">{account}</div>'}
        </div>
    """, unsafe_allow_html=True)

    if connected:
        # Show budget info
        st.markdown(f"""
        <div style="display:flex; gap:20px; margin-bottom:16px;">
            <div>
                <div style="font-size:0.68rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase;">Monthly Budget</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:1.2rem; color:#e2e8f5; font-weight:600;">₹{budget:,.2f}</div>
            </div>
            <div>
                <div style="font-size:0.68rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase;">Protection</div>
                <div style="font-size:0.85rem; color:#34d399; font-weight:600; margin-top:4px;">🛡 Active</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            new_budget = st.number_input(
                "Adjust budget (₹)", min_value=10.0, value=float(budget),
                step=50.0, key=f"bud_{connected_key}"
            )
            if new_budget != budget:
                st.session_state[budget_key] = new_budget
                st.rerun()
        with c2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button(f"✕ Disconnect {name}", key=f"disc_{connected_key}", use_container_width=True):
                st.session_state[connected_key] = False
                st.session_state[account_key]   = ""
                st.rerun()
    else:
        # Connection form
        acc_input = st.text_input(
            f"{name} Account ID", placeholder="e.g. ads-123456789",
            key=f"acc_input_{connected_key}"
        )
        if st.button(f"Connect {name} Ads", key=f"conn_{connected_key}", use_container_width=True):
            if acc_input.strip():
                st.session_state[connected_key] = True
                st.session_state[account_key]   = acc_input.strip()
                st.success(f"✓ {name} Ads connected!")
                st.rerun()
            else:
                st.error("Please enter an account ID")

    st.markdown("</div>", unsafe_allow_html=True)


# ── Google SVG logo ────────────────────────────────────────────────────────────
GOOGLE_SVG = """<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="32" height="32" rx="8" fill="#fff"/>
  <path d="M28.64 16.32c0-.88-.08-1.73-.22-2.55H16v4.82h7.1a6.07 6.07 0 01-2.63 3.98v3.31h4.25c2.49-2.29 3.92-5.67 3.92-9.56z" fill="#4285F4"/>
  <path d="M16 29c3.57 0 6.56-1.18 8.74-3.22l-4.25-3.31C19.28 23.44 17.74 24 16 24c-3.45 0-6.38-2.33-7.43-5.47H4.19v3.42A13 13 0 0016 29z" fill="#34A853"/>
  <path d="M8.57 18.53A7.83 7.83 0 018.13 16c0-.88.15-1.74.44-2.53V10.05H4.19A13 13 0 003 16c0 2.1.5 4.08 1.19 5.95l4.38-3.42z" fill="#FBBC05"/>
  <path d="M16 8.53c1.95 0 3.7.67 5.08 1.99l3.8-3.8C22.56 4.53 19.57 3 16 3A13 13 0 004.19 10.05l4.38 3.42C9.62 10.86 12.55 8.53 16 8.53z" fill="#EA4335"/>
</svg>"""

FACEBOOK_SVG = """<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="32" height="32" rx="8" fill="#1877F2"/>
  <path d="M22 16h-4v-2c0-.92.37-1.5 1.5-1.5H22V9h-3c-3.31 0-5 2.02-5 5.5V16h-3v3.5h3V29h4v-9.5h2.5L22 16z" fill="#fff"/>
</svg>"""


# ── Aggregated platform summary across all campaigns ──────────────────────────
def _aggregate_platform_stats(campaigns):
    """Sum up Google + Facebook stats across all user campaigns."""
    totals = {
        "Google":   {"total":0,"fraud":0,"suspicious":0,"valid":0,"total_spend":0.0,"wasted_spend":0.0},
        "Facebook": {"total":0,"fraud":0,"suspicious":0,"valid":0,"total_spend":0.0,"wasted_spend":0.0},
    }
    for camp in campaigns:
        stats = get_platform_stats(camp["id"])
        for s in stats:
            plat = s.get("platform","")
            if plat in totals:
                for k in ("total","fraud","suspicious","valid"):
                    totals[plat][k] += s.get(k, 0)
                totals[plat]["total_spend"]  += s.get("total_spend", 0.0)
                totals[plat]["wasted_spend"] += s.get("wasted_spend", 0.0)
    return totals


# ── Savings estimate ──────────────────────────────────────────────────────────
def _savings_card(platform_name, color, bg, wasted, budget):
    saved_pct = (wasted / budget * 100) if budget else 0
    recovery  = min(wasted * 0.85, wasted)          # AdShield blocks ~85% of fraud spend
    st.markdown(f"""
    <div style="border:1px solid rgba(255,255,255,0.07); border-radius:12px; padding:18px 20px;
                background:{bg}; margin-bottom:8px;">
        <div style="font-size:0.68rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase;
                    margin-bottom:10px;">{platform_name} — Budget Protection</div>
        <div style="display:flex; gap:24px;">
            <div>
                <div style="font-size:0.68rem; color:#4b5d7a;">Wasted Spend</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:1.05rem;
                             color:{FRAUD_COLOR}; font-weight:600;">₹{wasted:,.2f}</div>
            </div>
            <div>
                <div style="font-size:0.68rem; color:#4b5d7a;">AdShield Saved</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:1.05rem;
                             color:{VALID_COLOR}; font-weight:600;">₹{recovery:,.2f}</div>
            </div>
            <div>
                <div style="font-size:0.68rem; color:#4b5d7a;">Budget Exposed</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:1.05rem;
                             color:{WARN_COLOR}; font-weight:600;">{saved_pct:.1f}%</div>
            </div>
        </div>
        <div style="margin-top:12px; background:rgba(255,255,255,0.04); border-radius:4px; height:5px; overflow:hidden;">
            <div style="background:{FRAUD_COLOR}; width:{min(saved_pct,100):.1f}%; height:100%; border-radius:4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Per-campaign breakdown table ───────────────────────────────────────────────
def _campaign_breakdown_table(campaigns, platform_filter):
    rows = []
    for camp in campaigns:
        stats = get_platform_stats(camp["id"])
        for s in stats:
            plat = s.get("platform", "")
            if platform_filter != "All" and plat != platform_filter:
                continue
            total = s.get("total", 0)
            fraud = s.get("fraud", 0)
            rate  = round(fraud / total * 100, 1) if total else 0
            rows.append({
                "Campaign":    camp["name"],
                "Platform":    plat,
                "Total Events":total,
                "Fraud":       fraud,
                "Suspicious":  s.get("suspicious", 0),
                "Valid":       s.get("valid", 0),
                "Fraud Rate":  f"{rate}%",
                "Spend (₹)":   f"₹{s.get('total_spend',0):.2f}",
                "Wasted (₹)":  f"₹{s.get('wasted_spend',0):.2f}",
            })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     height=min(400, 60 + len(df) * 40))
    else:
        st.markdown(
            '<div style="padding:40px;text-align:center;color:#2d3a52;">No platform data yet.'
            ' Use the Traffic Simulator to generate events.</div>',
            unsafe_allow_html=True
        )


# ── Hourly combined chart across all campaigns ─────────────────────────────────
def _combined_hourly_chart(campaigns, hours=24):
    all_rows = []
    for camp in campaigns:
        rows = get_hourly_breakdown(camp["id"], hours=hours)
        all_rows.extend(rows)

    if not all_rows:
        st.markdown(
            '<div style="height:220px;display:flex;align-items:center;justify-content:center;color:#2d3a52;">No data yet</div>',
            unsafe_allow_html=True
        )
        return

    df = pd.DataFrame(all_rows)

    fig = go.Figure()
    palette = {"Google": GOOGLE_COLOR, "Facebook": FACEBOOK_COLOR}
    for plat, color in palette.items():
        sub = df[df["platform"] == plat] if "platform" in df.columns else pd.DataFrame()
        if sub.empty:
            continue
        valid_sub = sub[sub["classification"] == "VALID"]
        fraud_sub = sub[sub["classification"] == "FRAUD"]
        sus_sub   = sub[sub["classification"] == "SUSPICIOUS"]
        if not valid_sub.empty:
            fig.add_trace(go.Bar(x=valid_sub["hour"], y=valid_sub["cnt"],
                                 name=f"{plat} Valid", marker_color=color, opacity=0.7))
        if not sus_sub.empty:
            fig.add_trace(go.Bar(x=sus_sub["hour"], y=sus_sub["cnt"],
                                 name=f"{plat} Suspicious", marker_color=WARN_COLOR, opacity=0.8))
        if not fraud_sub.empty:
            fig.add_trace(go.Bar(x=fraud_sub["hour"], y=fraud_sub["cnt"],
                                 name=f"{plat} Fraud", marker_color=FRAUD_COLOR, opacity=0.9))

    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1e0", family="Inter,sans-serif"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Hour"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Events"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#6b7a99", size=11),
                    orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=30, b=30, l=30, r=20), height=280,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Fraud rate comparison bar chart ───────────────────────────────────────────
def _fraud_rate_comparison(agg):
    platforms = []
    fraud_rates = []
    colors = []
    for plat, color in [("Google", GOOGLE_COLOR), ("Facebook", FACEBOOK_COLOR)]:
        t = agg[plat]["total"]
        f = agg[plat]["fraud"]
        rate = round(f / t * 100, 1) if t else 0
        platforms.append(plat)
        fraud_rates.append(rate)
        colors.append(color)

    fig = go.Figure(go.Bar(
        x=platforms, y=fraud_rates,
        marker_color=colors,
        text=[f"{r}%" for r in fraud_rates],
        textposition="outside",
        textfont=dict(color="#c9d1e0", size=13),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1e0"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Fraud Rate (%)", range=[0, 100]),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        margin=dict(t=20, b=20, l=30, r=20), height=240,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Spend vs wasted donut ──────────────────────────────────────────────────────
def _spend_donut(agg):
    total_spend  = agg["Google"]["total_spend"]  + agg["Facebook"]["total_spend"]
    total_wasted = agg["Google"]["wasted_spend"] + agg["Facebook"]["wasted_spend"]
    total_valid  = max(total_spend - total_wasted, 0)

    if total_spend == 0:
        st.markdown(
            '<div style="height:220px;display:flex;align-items:center;justify-content:center;color:#2d3a52;">No spend data</div>',
            unsafe_allow_html=True
        )
        return

    fig = go.Figure(go.Pie(
        labels=["Effective Spend", "Wasted on Fraud"],
        values=[total_valid, total_wasted],
        hole=0.6,
        marker=dict(colors=[VALID_COLOR, FRAUD_COLOR],
                    line=dict(color="#050811", width=3)),
        textfont=dict(color="#fff", size=12),
        hovertemplate="<b>%{label}</b><br>₹%{value:.2f}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"₹{total_spend:.2f}<br><span style='font-size:10px'>total</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="#e2e8f5", family="IBM Plex Mono"),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1e0"), showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#6b7a99", size=11)),
        margin=dict(t=10, b=10, l=10, r=10), height=240,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Traffic simulator ──────────────────────────────────────────────────────────
def _simulator_section(campaigns):
    if not campaigns:
        st.info("Create a campaign first to use the simulator.")
        return

    camp_map = {c["name"]: c["id"] for c in campaigns}

    st.markdown("""
    <div style="font-size:0.78rem; color:#4b5d7a; margin-bottom:16px; line-height:1.6;">
        Simulate real-world Google and Facebook ad traffic including bot attacks, VPN clicks,
        and mixed traffic patterns to test your fraud detection in real time.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        selected_camp = st.selectbox("Campaign", list(camp_map.keys()), key="sim_pi_camp")
    with col2:
        sim_platform  = st.selectbox("Platform", ["Google", "Facebook", "Both"], key="sim_pi_plat")

    cid = camp_map[selected_camp]

    sc1, sc2, sc3, sc4 = st.columns(4)

    with sc1:
        st.markdown("**⚡ Single Event**")
        s_ip   = st.text_input("IP", value=_rand_ip(), key="sim_pi_ip")
        s_cost = st.number_input("Cost ₹", 0.0, value=0.25, step=0.05, key="sim_pi_cost")
        s_evt  = st.selectbox("Event", ["click","impression","conversion"], key="sim_pi_evt")
        if st.button("Send", key="sim_pi_send", use_container_width=True):
            plats = ["Google","Facebook"] if sim_platform == "Both" else [sim_platform]
            for p in plats:
                r, _ = send_platform_event(cid, p, s_evt, s_ip,
                                           random.choice(COUNTRIES),
                                           random.choice(DEVICES),
                                           random.choice(BROWSERS), s_cost)
                cls = r.get("classification","?")
                if cls == "FRAUD":    st.error(f"🔴 {p}: FRAUD — {r.get('reason','')}")
                elif cls == "SUSPICIOUS": st.warning(f"🟡 {p}: SUSPICIOUS")
                else:                 st.success(f"🟢 {p}: VALID")
            st.rerun()

    with sc2:
        st.markdown("**🤖 Bot Attack**")
        st.markdown('<div style="color:#4b5d7a;font-size:0.78rem;margin-bottom:8px;">Rapid-fire clicks from one IP to simulate a bot network</div>', unsafe_allow_html=True)
        n_bot = st.slider("Clicks", 5, 30, 10, key="sim_pi_nbot")
        if st.button("Launch Attack", key="sim_pi_bot", use_container_width=True):
            bot_ip = _bot_ip()
            plats = ["Google","Facebook"] if sim_platform == "Both" else [sim_platform]
            for p in plats:
                for _ in range(n_bot):
                    send_platform_event(cid, p, "click", bot_ip, "RU","mobile","Chrome", 0.15)
            st.error(f"🤖 {n_bot} bot clicks sent from {bot_ip}")
            st.rerun()

    with sc3:
        st.markdown("**🌍 Normal Traffic**")
        st.markdown('<div style="color:#4b5d7a;font-size:0.78rem;margin-bottom:8px;">Mixed geographic, device, and browser diversity</div>', unsafe_allow_html=True)
        n_norm = st.slider("Events", 10, 50, 20, key="sim_pi_nnorm")
        if st.button("Generate", key="sim_pi_norm", use_container_width=True):
            plats = ["Google","Facebook"] if sim_platform == "Both" else [sim_platform]
            for _ in range(n_norm):
                p = random.choice(plats)
                send_platform_event(cid, p, "click",
                                    _rand_ip(), random.choice(COUNTRIES),
                                    random.choice(DEVICES), random.choice(BROWSERS),
                                    round(random.uniform(0.05, 2.0), 2))
            st.success(f"✓ {n_norm} normal events sent")
            st.rerun()

    with sc4:
        st.markdown("**💀 Mixed Attack**")
        st.markdown('<div style="color:#4b5d7a;font-size:0.78rem;margin-bottom:8px;">Blends legitimate and fraudulent traffic to test detection accuracy</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Run Scenario", key="sim_pi_mixed", use_container_width=True):
            plats = ["Google","Facebook"] if sim_platform == "Both" else [sim_platform]
            # 10 legit
            for _ in range(10):
                p = random.choice(plats)
                send_platform_event(cid, p, "click", _rand_ip(),
                                    random.choice(COUNTRIES), "desktop", "Chrome",
                                    round(random.uniform(0.2, 1.0), 2))
            # 15 bot
            bot = _bot_ip()
            for p in plats:
                for _ in range(15):
                    send_platform_event(cid, p, "click", bot, "CN","mobile","Chrome", 0.10)
            # 5 VPN-looking
            for _ in range(5):
                p = random.choice(plats)
                send_platform_event(cid, p, "click",
                                    f"10.{random.randint(0,9)}.{random.randint(0,255)}.{random.randint(1,254)}",
                                    "RU","desktop","Firefox", 0.18)
            st.error("💀 Mixed attack scenario complete — check live feed")
            st.rerun()


# ── Main render ────────────────────────────────────────────────────────────────
def render():
    _init_state()

    st.markdown("""
    <div class="page-header">
        <div class="page-title">Platform Integrations</div>
        <div class="page-subtitle">Google Ads &amp; Facebook Ads — connection, monitoring, and budget protection</div>
    </div>
    """, unsafe_allow_html=True)

    campaigns = get_campaigns()
    g_conn = st.session_state.get("google_connected", False)
    f_conn = st.session_state.get("facebook_connected", False)

    # ── Tab bar (manual pills) ─────────────────────────────────────────────────
    tab_options = ["overview", "connections", "analytics", "simulator"]
    tab_labels  = {
        "overview":    "📊  Overview",
        "connections": "🔌  Connections",
        "analytics":   "📈  Analytics",
        "simulator":   "🧪  Simulator",
    }
    current_tab = st.session_state.get("pi_tab", "overview")

    cols = st.columns(len(tab_options))
    for i, key in enumerate(tab_options):
        with cols[i]:
            active = current_tab == key
            btn_style = (
                "background:rgba(96,165,250,0.12);color:#60a5fa;border:1px solid rgba(96,165,250,0.25);"
                if active else
                "background:rgba(255,255,255,0.04);color:#6b7a99;border:1px solid rgba(255,255,255,0.07);"
            )
            if st.button(tab_labels[key], key=f"pi_tab_{key}", use_container_width=True):
                st.session_state.pi_tab = key
                st.rerun()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    tab = st.session_state.get("pi_tab", "overview")

    # ══════════════════════════════════════════════════════════════════════════
    if tab == "overview":
        _render_overview(campaigns, g_conn, f_conn)

    elif tab == "connections":
        _render_connections()

    elif tab == "analytics":
        _render_analytics(campaigns)

    elif tab == "simulator":
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Traffic Simulator</div>', unsafe_allow_html=True)
        _simulator_section(campaigns)
        st.markdown('</div>', unsafe_allow_html=True)


# ── Overview tab ──────────────────────────────────────────────────────────────
def _render_overview(campaigns, g_conn, f_conn):
    agg = _aggregate_platform_stats(campaigns)

    # Connection status banner
    n_conn = sum([g_conn, f_conn])
    if n_conn == 0:
        st.markdown("""
        <div style="border:1px solid rgba(251,191,36,0.3); border-radius:12px; padding:16px 20px;
                    background:rgba(251,191,36,0.06); margin-bottom:16px;">
            <span style="color:#fbbf24; font-weight:600;">⚠ No platforms connected</span>
            <span style="color:#6b7a99; font-size:0.85rem; margin-left:8px;">
                Go to the <strong>Connections</strong> tab to link your Google or Facebook Ads accounts.
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        connected_names = []
        if g_conn: connected_names.append("Google Ads")
        if f_conn: connected_names.append("Facebook Ads")
        st.markdown(f"""
        <div style="border:1px solid rgba(52,211,153,0.25); border-radius:12px; padding:14px 20px;
                    background:rgba(52,211,153,0.06); margin-bottom:16px;">
            <span style="color:#34d399; font-weight:600;">🛡 Protected</span>
            <span style="color:#6b7a99; font-size:0.85rem; margin-left:8px;">
                {' & '.join(connected_names)} — AdShield is actively monitoring all incoming events.
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Global KPI row ────────────────────────────────────────────────────────
    g = agg["Google"]; f = agg["Facebook"]
    total_events = g["total"] + f["total"]
    total_fraud  = g["fraud"] + f["fraud"]
    total_spend  = g["total_spend"] + f["total_spend"]
    total_wasted = g["wasted_spend"] + f["wasted_spend"]

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Events", f"{total_events:,}", "All platforms")
    with k2:
        rate = round(total_fraud / total_events * 100, 1) if total_events else 0
        st.metric("Fraud Detected", f"{total_fraud:,}", f"{rate}% rate", delta_color="inverse")
    with k3:
        st.metric("Total Ad Spend", f"₹{total_spend:,.2f}")
    with k4:
        st.metric("Wasted Spend", f"₹{total_wasted:,.2f}",
                  f"₹{max(total_spend-total_wasted,0):.2f} saved", delta_color="inverse")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Platform cards row ────────────────────────────────────────────────────
    pcol1, pcol2 = st.columns(2)

    with pcol1:
        _platform_overview_card("Google", GOOGLE_COLOR, GOOGLE_BG, GOOGLE_BORDER, g, GOOGLE_SVG)

    with pcol2:
        _platform_overview_card("Facebook", FACEBOOK_COLOR, FACEBOOK_BG, FACEBOOK_BORDER, f, FACEBOOK_SVG)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Savings + donut row ───────────────────────────────────────────────────
    sv1, sv2 = st.columns([3, 2])
    with sv1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Budget Protection Summary</div>', unsafe_allow_html=True)
        _savings_card("Google", GOOGLE_COLOR, GOOGLE_BG,
                      g["wasted_spend"], st.session_state.get("google_budget", 500.0))
        _savings_card("Facebook", FACEBOOK_COLOR, FACEBOOK_BG,
                      f["wasted_spend"], st.session_state.get("facebook_budget", 300.0))
        st.markdown('</div>', unsafe_allow_html=True)
    with sv2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Spend Quality</div>', unsafe_allow_html=True)
        _spend_donut(agg)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Recent live feed (last 20 events) ────────────────────────────────────
    if campaigns:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Recent Platform Events (all campaigns)</div>', unsafe_allow_html=True)
        feed_rows = []
        for camp in campaigns[:5]:      # cap at 5 campaigns to avoid too many API calls
            rows = get_realtime_feed(camp["id"], limit=10)
            for r in rows:
                r["campaign"] = camp["name"]
                feed_rows.append(r)
        feed_rows = sorted(feed_rows, key=lambda x: x.get("created_at",""), reverse=True)[:20]
        if feed_rows:
            df = pd.DataFrame(feed_rows)
            df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%H:%M:%S")
            def cls_icon(c):
                return {"FRAUD":"🔴 FRAUD","SUSPICIOUS":"🟡 SUSP","VALID":"🟢 VALID"}.get(c, c)
            df["Status"] = df["classification"].apply(cls_icon)
            show_cols = [c for c in ["created_at","campaign","source","platform","ip_address","country","device","Status","fraud_reason"] if c in df.columns]
            st.dataframe(
                df[show_cols].rename(columns={"created_at":"Time","campaign":"Campaign",
                                               "source":"Src","platform":"Platform",
                                               "ip_address":"IP","country":"Country",
                                               "device":"Device","fraud_reason":"Reason"}),
                use_container_width=True, hide_index=True,
                height=min(380, 60 + len(df) * 36),
            )
        else:
            st.markdown('<div style="padding:40px;text-align:center;color:#2d3a52;">No events yet. Use the Simulator tab to generate data.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def _platform_overview_card(name, color, bg, border, stats, logo_svg):
    total = stats["total"]
    fraud = stats["fraud"]
    sus   = stats["suspicious"]
    valid = stats["valid"]
    spend = stats["total_spend"]
    wasted= stats["wasted_spend"]
    rate  = round(fraud / total * 100, 1) if total else 0
    fraud_bar_w = min(rate, 100)

    st.markdown(f"""
    <div style="border:1px solid {border}; border-radius:16px; padding:22px 24px;
                background:{bg}; height:100%;">
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:18px;">
            {logo_svg}
            <div style="font-family:'Syne',sans-serif; font-size:1rem; font-weight:700; color:#e2e8f5;">{name} Ads</div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:16px;">
            <div>
                <div style="font-size:0.65rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase;">Total Events</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#e2e8f5;">{total:,}</div>
            </div>
            <div>
                <div style="font-size:0.65rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase;">Fraud Rate</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700;
                             color:{'#f87171' if rate > 20 else '#fbbf24' if rate > 10 else '#34d399'};">{rate}%</div>
            </div>
            <div>
                <div style="font-size:0.65rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase;">Valid</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:1rem; color:#34d399; font-weight:600;">{valid:,}</div>
            </div>
            <div>
                <div style="font-size:0.65rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase;">Fraud + Susp</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:1rem; color:#f87171; font-weight:600;">{fraud + sus:,}</div>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.78rem; margin-bottom:8px;">
            <span style="color:#6b7a99;">💰 ₹{spend:.2f} spend</span>
            <span style="color:{FRAUD_COLOR};">🔥 ₹{wasted:.2f} wasted</span>
        </div>
        <div style="background:rgba(255,255,255,0.05); border-radius:4px; height:4px; overflow:hidden;">
            <div style="background:{FRAUD_COLOR}; width:{fraud_bar_w}%; height:100%; border-radius:4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Connections tab ────────────────────────────────────────────────────────────
def _render_connections():
    st.markdown("""
    <div style="font-size:0.82rem; color:#4b5d7a; margin-bottom:20px; max-width:640px;">
        Connect your ad platform accounts to enable real-time event ingestion, budget monitoring,
        and automatic fraud blocking. Each platform uses AdShield's IP block/whitelist rules
        to filter fraudulent traffic before it's counted.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        _connection_card(
            "Google", GOOGLE_COLOR, GOOGLE_BG, GOOGLE_BORDER,
            GOOGLE_SVG,
            "google_connected", "google_account", "google_budget",
        )
    with c2:
        _connection_card(
            "Facebook", FACEBOOK_COLOR, FACEBOOK_BG, FACEBOOK_BORDER,
            FACEBOOK_SVG,
            "facebook_connected", "facebook_account", "facebook_budget",
        )

    # How it works section
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">How Integration Works</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:20px; padding-bottom:8px;">
        <div>
            <div style="color:#60a5fa; font-size:1.1rem; margin-bottom:8px;">① Ingest</div>
            <div style="font-size:0.82rem; color:#6b7a99; line-height:1.6;">
                Each ad click and impression from your connected platform is forwarded to AdShield
                via the <code style="font-family:IBM Plex Mono,monospace;color:#93c5fd;">/platform-event</code> endpoint.
            </div>
        </div>
        <div>
            <div style="color:#60a5fa; font-size:1.1rem; margin-bottom:8px;">② Classify</div>
            <div style="font-size:0.82rem; color:#6b7a99; line-height:1.6;">
                Each event is checked against your IP block list, rate-limit rules,
                and the XGBoost ML model. It's flagged as VALID, SUSPICIOUS, or FRAUD.
            </div>
        </div>
        <div>
            <div style="color:#60a5fa; font-size:1.1rem; margin-bottom:8px;">③ Block & Report</div>
            <div style="font-size:0.82rem; color:#6b7a99; line-height:1.6;">
                Fraudulent IPs are automatically added to your block list and excluded from
                future billing. Spend and savings are tracked per campaign.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── Analytics tab ─────────────────────────────────────────────────────────────
def _render_analytics(campaigns):
    if not campaigns:
        st.info("Create campaigns first to view analytics.")
        return

    # Filters row
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        plat_filter = st.selectbox("Platform", ["All","Google","Facebook"], key="pi_an_plat")
    with f2:
        hours_back  = st.selectbox("Timeframe", [6, 12, 24, 48, 168],
                                   format_func=lambda h: f"Last {h}h" if h < 48 else "Last 7d",
                                   index=2, key="pi_an_hours")
    with f3:
        camp_names  = ["All campaigns"] + [c["name"] for c in campaigns]
        camp_sel    = st.selectbox("Campaign", camp_names, key="pi_an_camp")

    # filter campaigns if needed
    filtered_camps = campaigns
    if camp_sel != "All campaigns":
        filtered_camps = [c for c in campaigns if c["name"] == camp_sel]

    agg = _aggregate_platform_stats(filtered_camps)

    ch1, ch2 = st.columns([3, 2])
    with ch1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Hourly Event Volume</div>', unsafe_allow_html=True)
        _combined_hourly_chart(filtered_camps, hours=hours_back)
        st.markdown('</div>', unsafe_allow_html=True)
    with ch2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Fraud Rate by Platform</div>', unsafe_allow_html=True)
        _fraud_rate_comparison(agg)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Per-campaign breakdown
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Campaign × Platform Breakdown</div>', unsafe_allow_html=True)
    _campaign_breakdown_table(filtered_camps, plat_filter)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # IP summary
    ip_counts = get_ip_list_counts()
    st.markdown(f"""
    <div style="display:flex; gap:16px;">
        <div class="card" style="padding:18px 22px; flex:1;">
            <div style="font-size:0.65rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Blocked IPs</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#f87171;">{ip_counts.get('blocked',0):,}</div>
        </div>
        <div class="card" style="padding:18px 22px; flex:1;">
            <div style="font-size:0.65rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Whitelisted IPs</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#34d399;">{ip_counts.get('whitelisted',0):,}</div>
        </div>
        <div class="card" style="padding:18px 22px; flex:1;">
            <div style="font-size:0.65rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Total Events Monitored</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#e2e8f5;">{agg['Google']['total'] + agg['Facebook']['total']:,}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
