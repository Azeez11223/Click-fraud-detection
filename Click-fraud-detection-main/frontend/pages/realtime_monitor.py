"""
pages/realtime_monitor.py — Realtime Platform Monitoring
AdShield v3 — Google & Facebook ads realtime fraud detection
"""
import random, time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from components.api import (
    get_campaigns, get_realtime_feed, get_platform_stats,
    get_hourly_breakdown, send_platform_event, get_platform_events_api,
)

FRAUD_COLOR = "#f87171"
WARN_COLOR  = "#fbbf24"
VALID_COLOR = "#34d399"
GOOGLE_COLOR = "#4285f4"
FACEBOOK_COLOR = "#1877f2"

COUNTRIES = ["US","IN","CN","BR","RU","DE","GB","FR","JP","AU","NG","PK","BD","MX","ID"]
DEVICES   = ["mobile","desktop","tablet"]
BROWSERS  = ["Chrome","Firefox","Safari","Edge","Opera"]

def _rand_ip():
    return f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def _bot_ip():
    return f"192.168.{random.randint(0,9)}.{random.randint(1,50)}"


def render():
    campaigns = get_campaigns()

    st.markdown("""
    <div class="page-header">
        <div class="page-title">Realtime Monitor</div>
        <div class="page-subtitle">Live Google & Facebook ad click fraud detection</div>
    </div>
    """, unsafe_allow_html=True)

    if not campaigns:
        st.markdown("""<div class="card" style="text-align:center;padding:60px;">
            <div style="font-size:2rem;">📡</div>
            <div style="color:#4b5d7a;margin-top:8px;">No campaigns yet. Create a campaign first.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("＋ Create Campaign"):
            st.session_state.page = "Campaigns"; st.session_state.show_campaign_form = True; st.rerun()
        return

    # ── Campaign selector ──────────────────────────────────────────────────────
    camp_names = {c["name"]: c["id"] for c in campaigns}
    selected_name = st.selectbox("Select Campaign", list(camp_names.keys()), key="rt_campaign_select")
    cid = camp_names[selected_name]
    campaign = next(c for c in campaigns if c["id"] == cid)

    col_plat, col_auto, col_refresh = st.columns([2, 2, 1])
    with col_plat:
        platform_filter = st.selectbox("Platform", ["All","Google","Facebook"], key="rt_platform")
    with col_auto:
        auto_refresh = st.checkbox("⟳ Auto-refresh every 5s", value=False, key="rt_auto")
    with col_refresh:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("↺ Refresh", use_container_width=True): st.rerun()

    if auto_refresh:
        time.sleep(5); st.rerun()

    # ── Platform stats ─────────────────────────────────────────────────────────
    plat_stats = get_platform_stats(cid)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if plat_stats:
        g_stat = next((s for s in plat_stats if s["platform"]=="Google"), {})
        f_stat = next((s for s in plat_stats if s["platform"]=="Facebook"), {})

        # Google card
        g1, g2, f1, f2 = st.columns(4)
        with g1:
            _platform_kpi_card("Google", g_stat.get("total",0), g_stat.get("fraud",0),
                               g_stat.get("total_spend",0), g_stat.get("wasted_spend",0), GOOGLE_COLOR)
        with g2:
            st.metric("Google Fraud Rate",
                      f"{round(g_stat['fraud']/g_stat['total']*100,1) if g_stat.get('total') else 0}%")
        with f1:
            _platform_kpi_card("Facebook", f_stat.get("total",0), f_stat.get("fraud",0),
                               f_stat.get("total_spend",0), f_stat.get("wasted_spend",0), FACEBOOK_COLOR)
        with f2:
            st.metric("Facebook Fraud Rate",
                      f"{round(f_stat['fraud']/f_stat['total']*100,1) if f_stat.get('total') else 0}%")
    else:
        st.info("No platform events yet. Use the simulator below to generate traffic.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Charts row ─────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns([3, 2])

    with ch1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Hourly Click Timeline (24h)</div>', unsafe_allow_html=True)
        hourly = get_hourly_breakdown(cid, hours=24)
        if hourly:
            df = pd.DataFrame(hourly)
            fig = go.Figure()
            for plat, color in [("Google", GOOGLE_COLOR), ("Facebook", FACEBOOK_COLOR)]:
                sub = df[df["platform"]==plat] if "platform" in df.columns else pd.DataFrame()
                if not sub.empty:
                    fraud_sub = sub[sub["classification"]=="FRAUD"] if "classification" in sub.columns else pd.DataFrame()
                    valid_sub = sub[sub["classification"]=="VALID"] if "classification" in sub.columns else pd.DataFrame()
                    if not valid_sub.empty:
                        fig.add_trace(go.Bar(x=valid_sub["hour"], y=valid_sub["cnt"],
                                             name=f"{plat} Valid", marker_color=color, opacity=0.7))
                    if not fraud_sub.empty:
                        fig.add_trace(go.Bar(x=fraud_sub["hour"], y=fraud_sub["cnt"],
                                             name=f"{plat} Fraud", marker_color=FRAUD_COLOR, opacity=0.9))
            fig.update_layout(
                barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9d1e0", family="Inter,sans-serif"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#6b7a99",size=11),
                            orientation="h", yanchor="bottom", y=1.02),
                margin=dict(t=30,b=30,l=30,r=20), height=280,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        else:
            st.markdown('<div style="height:220px;display:flex;align-items:center;justify-content:center;color:#2d3a52;">No data yet</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with ch2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Platform Split</div>', unsafe_allow_html=True)
        if plat_stats:
            labels = [s["platform"] for s in plat_stats]
            totals = [s["total"] for s in plat_stats]
            colors = [GOOGLE_COLOR if p=="Google" else FACEBOOK_COLOR for p in labels]
            fig2 = go.Figure(go.Pie(
                labels=labels, values=totals, hole=0.55,
                marker=dict(colors=colors, line=dict(color="#050811", width=3)),
                textfont=dict(color="#fff", size=12),
                hovertemplate="<b>%{label}</b><br>%{value} clicks<extra></extra>",
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9d1e0"), showlegend=True,
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#6b7a99",size=12)),
                margin=dict(t=20,b=20,l=20,r=20), height=280,
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        else:
            st.markdown('<div style="height:220px;display:flex;align-items:center;justify-content:center;color:#2d3a52;">No data</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Live feed table ────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Live Event Feed</div>', unsafe_allow_html=True)

    pf = None if platform_filter == "All" else platform_filter
    feed = get_realtime_feed(cid, limit=50)
    if platform_filter != "All":
        feed = [e for e in feed if e.get("platform","") == platform_filter or e.get("source") == "click"]

    if feed:
        df_feed = pd.DataFrame(feed)
        # Classification badge colors in display
        df_feed["created_at"] = pd.to_datetime(df_feed["created_at"]).dt.strftime("%H:%M:%S")

        def cls_icon(c):
            return {"FRAUD":"🔴 FRAUD","SUSPICIOUS":"🟡 SUSP","VALID":"🟢 VALID"}.get(c, c)

        df_feed["cls_display"] = df_feed["classification"].apply(cls_icon)
        display_cols = ["created_at","source","platform","ip_address","country","device","cls_display","fraud_reason"]
        existing = [c for c in display_cols if c in df_feed.columns]
        st.dataframe(
            df_feed[existing].rename(columns={
                "created_at":"Time","source":"Source","platform":"Platform",
                "ip_address":"IP","country":"Country","device":"Device",
                "cls_display":"Status","fraud_reason":"Reason",
            }),
            use_container_width=True, hide_index=True,
            height=min(400, 60+len(df_feed)*36),
        )
    else:
        st.markdown('<div style="height:100px;display:flex;align-items:center;justify-content:center;color:#2d3a52;">No events yet. Use the simulator below.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Simulator ─────────────────────────────────────────────────────────────
    with st.expander("🧪 Traffic Simulator (Google & Facebook)", expanded=False):
        s1, s2, s3, s4 = st.columns(4)
        with s1: sim_plat = st.selectbox("Platform", ["Google","Facebook"], key="sim_plat")
        with s2: sim_type = st.selectbox("Event", ["click","impression","conversion"], key="sim_type")
        with s3: sim_ip   = st.text_input("IP", value=_rand_ip(), key="sim_ip2")
        with s4: sim_cost = st.number_input("Cost $", min_value=0.0, value=0.25, step=0.05, key="sim_cost")

        sim_country = st.selectbox("Country", COUNTRIES, key="sim_country")
        sim_device  = st.selectbox("Device",  DEVICES,   key="sim_device")
        sim_browser = st.selectbox("Browser", BROWSERS,  key="sim_browser")

        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            if st.button("⚡ Send Event", use_container_width=True, key="send_ev"):
                r, code = send_platform_event(cid, sim_plat, sim_type, sim_ip,
                                              sim_country, sim_device, sim_browser, sim_cost)
                cls = r.get("classification","?")
                if cls == "FRAUD": st.error(f"🔴 FRAUD — {r.get('reason','')}")
                elif cls == "SUSPICIOUS": st.warning(f"🟡 SUSPICIOUS — {r.get('reason','')}")
                else: st.success("🟢 VALID")
                st.rerun()
        with sc2:
            if st.button("🤖 Simulate 10 Bot Clicks", use_container_width=True, key="bot10"):
                bot_ip = _bot_ip()
                for i in range(10):
                    send_platform_event(cid, sim_plat, "click", bot_ip, "RU","mobile","Chrome", 0.15)
                st.warning(f"Sent 10 bot clicks from {bot_ip}"); st.rerun()
        with sc3:
            if st.button("🌍 Simulate 20 Normal Events", use_container_width=True, key="norm20"):
                for _ in range(20):
                    send_platform_event(cid, random.choice(["Google","Facebook"]), "click",
                                        _rand_ip(), random.choice(COUNTRIES),
                                        random.choice(DEVICES), random.choice(BROWSERS),
                                        round(random.uniform(0.1, 1.5), 2))
                st.success("Sent 20 normal events"); st.rerun()
        with sc4:
            if st.button("💀 Mixed Attack Simulation", use_container_width=True, key="attack"):
                # 5 legit + 10 rapid bot
                for _ in range(5):
                    send_platform_event(cid,"Google","click",_rand_ip(),random.choice(COUNTRIES),"desktop","Chrome",0.30)
                bot = _bot_ip()
                for _ in range(10):
                    send_platform_event(cid,"Facebook","click",bot,"RU","mobile","Chrome",0.20)
                st.error("Attack simulation complete — check feed for detections"); st.rerun()


def _platform_kpi_card(name, total, fraud, spend, wasted, color):
    rate = round(fraud/total*100,1) if total else 0
    st.markdown(f"""
    <div class="card" style="padding:16px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <div style="width:10px;height:10px;border-radius:50%;background:{color};"></div>
            <span style="font-family:'Syne',sans-serif;font-weight:700;font-size:0.9rem;color:#e2e8f5;">{name}</span>
        </div>
        <div style="font-size:1.8rem;font-weight:700;font-family:'IBM Plex Mono',monospace;color:#e2e8f5;">{total:,}</div>
        <div style="font-size:0.72rem;color:#4b5d7a;margin-bottom:8px;">total events</div>
        <div style="display:flex;justify-content:space-between;font-size:0.78rem;">
            <span style="color:#f87171;">🔴 {fraud} fraud</span>
            <span style="color:#4b5d7a;">{rate}%</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-top:4px;">
            <span style="color:#6b7a99;">💰 ${spend:.2f} spend</span>
            <span style="color:#f87171;">🔥 ${wasted:.2f} wasted</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
