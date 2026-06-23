"""
pages/ip_manager.py — IP Block/Whitelist Manager + Dataset Upload
AdShield v3
"""
import io
import streamlit as st
import pandas as pd
from components.api import (
    get_ip_list, get_ip_list_counts, add_ip, remove_ip,
    get_ip_datasets, delete_ip_dataset, upload_ip_dataset,
)

LIST_COLORS = {
    "block":     ("#f87171", "rgba(248,113,113,0.12)"),
    "whitelist": ("#34d399", "rgba(52,211,153,0.12)"),
}


def render():
    st.markdown("""
    <div class="page-header">
        <div class="page-title">IP Manager</div>
        <div class="page-subtitle">Block malicious IPs, whitelist trusted ones, upload bulk datasets</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Summary counts ─────────────────────────────────────────────────────────
    counts = get_ip_list_counts()
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("🚫 Blocked IPs",    counts.get("blocked", 0))
    with c2: st.metric("✅ Whitelisted IPs", counts.get("whitelisted", 0))
    with c3: st.metric("📋 Total Entries",   counts.get("total", 0))

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["🚫 Block List", "✅ Whitelist", "📂 Upload Dataset"])

    # ─── TAB 1: Block list ────────────────────────────────────────────────────
    with tab1:
        _render_ip_tab("block", "🚫 Blocked IPs",
                       "IPs flagged as fraud sources. All clicks from these IPs are immediately blocked and logged as FRAUD.")

    # ─── TAB 2: Whitelist ────────────────────────────────────────────────────
    with tab2:
        _render_ip_tab("whitelist", "✅ Whitelisted IPs",
                       "Trusted IPs (e.g. your own team, internal tools). All clicks from these IPs are always marked VALID.")

    # ─── TAB 3: Upload Dataset ───────────────────────────────────────────────
    with tab3:
        _render_upload_tab()


def _render_ip_tab(list_type, title, description):
    st.markdown(f'<div style="color:#4b5d7a; font-size:0.82rem; margin-bottom:16px;">{description}</div>',
                unsafe_allow_html=True)

    # Add single IP form
    color, bg = LIST_COLORS[list_type]
    with st.expander(f"➕ Add IP to {title}", expanded=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_ip = st.text_input("IP Address", placeholder="e.g. 203.45.67.89",
                                   key=f"new_ip_{list_type}")
        with col2:
            note = st.text_input("Note (optional)", placeholder="e.g. competitor bot",
                                 key=f"note_{list_type}")
        with col3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button(f"Add", key=f"add_{list_type}", use_container_width=True):
                if not new_ip:
                    st.error("Enter an IP address")
                else:
                    result, code = add_ip(new_ip.strip(), list_type, note)
                    if code == 200:
                        st.success(f"✓ {new_ip} added to {list_type} list")
                        st.rerun()
                    else:
                        st.error(result.get("detail", "Failed"))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Fetch and display IPs
    ips = get_ip_list(list_type)
    if not ips:
        st.markdown(f"""
        <div class="card" style="text-align:center; padding:40px;">
            <div style="font-size:2rem; margin-bottom:8px;">{'🚫' if list_type=='block' else '✅'}</div>
            <div style="color:#4b5d7a;">No IPs in {list_type} list yet.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Search/filter
    search = st.text_input("🔍 Search IPs", placeholder="Filter by IP or note...",
                           key=f"search_{list_type}", label_visibility="collapsed")
    if search:
        ips = [ip for ip in ips if search.lower() in ip["ip_address"].lower()
               or search.lower() in ip.get("note","").lower()]

    st.markdown(f'<div class="section-label">{len(ips)} entries</div>', unsafe_allow_html=True)

    # Table header
    st.markdown(f"""
    <div style="display:grid; grid-template-columns:2fr 2fr 1fr 1fr; gap:8px;
                padding:8px 12px; border-bottom:1px solid rgba(255,255,255,0.07);
                font-size:0.7rem; color:#4b5d7a; letter-spacing:1px; text-transform:uppercase;">
        <span>IP Address</span><span>Note</span><span>Source</span><span>Added</span>
    </div>
    """, unsafe_allow_html=True)

    for entry in ips:
        ip    = entry["ip_address"]
        enote = entry.get("note","—") or "—"
        src   = entry.get("source","manual")
        date  = entry.get("created_at","")[:10]
        src_badge = f'<span style="background:rgba(59,130,246,0.15); color:#60a5fa; padding:2px 8px; border-radius:4px; font-size:0.68rem;">{src}</span>'

        col_data, col_del = st.columns([5, 1])
        with col_data:
            st.markdown(f"""
            <div style="display:grid; grid-template-columns:2fr 2fr 1fr 1fr; gap:8px;
                        padding:10px 12px; border-bottom:1px solid rgba(255,255,255,0.04);
                        align-items:center;">
                <span style="font-family:'IBM Plex Mono',monospace; font-size:0.83rem;
                             color:{color};">{ip}</span>
                <span style="font-size:0.8rem; color:#6b7a99;">{enote}</span>
                <span>{src_badge}</span>
                <span style="font-size:0.75rem; color:#4b5d7a;">{date}</span>
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            if st.button("✕", key=f"del_{list_type}_{ip}", help=f"Remove {ip}"):
                remove_ip(ip)
                st.rerun()

    # Bulk clear
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button(f"🗑 Clear All {title}", key=f"clear_all_{list_type}"):
        for entry in ips:
            remove_ip(entry["ip_address"])
        st.success(f"Cleared all {len(ips)} entries")
        st.rerun()


def _render_upload_tab():
    st.markdown("""
    <div style="color:#4b5d7a; font-size:0.82rem; margin-bottom:16px;">
        Upload a file of IP addresses to bulk-add to your block list, whitelist, or training dataset.
        Supported formats: <strong>CSV</strong> (first column), <strong>JSON</strong> (array or object values),
        <strong>TXT</strong> (one IP per line).
    </div>
    """, unsafe_allow_html=True)

    # Upload form
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Upload IP File</div>', unsafe_allow_html=True)

    up_col1, up_col2 = st.columns([3, 1])
    with up_col1:
        uploaded = st.file_uploader("Choose file", type=["csv","json","txt"],
                                    label_visibility="collapsed", key="ip_file_upload")
    with up_col2:
        upload_type = st.selectbox("Action", ["block","whitelist","training"],
                                   key="upload_list_type",
                                   format_func=lambda x: {"block":"🚫 Block List","whitelist":"✅ Whitelist","training":"🧠 Training Data"}[x])

    if uploaded:
        file_bytes = uploaded.read()
        st.markdown(f'<div style="font-size:0.8rem; color:#6b7a99; margin:8px 0;">📄 {uploaded.name} · {len(file_bytes):,} bytes</div>',
                    unsafe_allow_html=True)

        # Preview
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
            lines = [l.strip() for l in text.splitlines() if l.strip()][:5]
            st.markdown(f'<div style="font-family:IBM Plex Mono,monospace; font-size:0.75rem; color:#4b5d7a; padding:8px; background:rgba(0,0,0,0.2); border-radius:6px; margin-bottom:12px;">Preview: {" · ".join(lines[:3])}{"..." if len(lines)>3 else ""}</div>',
                        unsafe_allow_html=True)
        except: pass

        if st.button("⬆ Upload & Apply", use_container_width=True, key="do_upload"):
            with st.spinner("Uploading and processing..."):
                result, code = upload_ip_dataset(file_bytes, uploaded.name, upload_type)
            if code == 200:
                st.success(f"✓ Uploaded {result.get('total_ips',0):,} IPs — "
                           f"{result.get('inserted_to_list',0):,} added to {upload_type} list "
                           f"({result.get('skipped',0)} skipped / duplicates)")
                st.rerun()
            else:
                st.error(result.get("detail","Upload failed"))

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Past uploads table ─────────────────────────────────────────────────────
    datasets = get_ip_datasets()
    if datasets:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Upload History</div>', unsafe_allow_html=True)
        for ds in datasets:
            lt_color = "#f87171" if ds["list_type"]=="block" else "#34d399" if ds["list_type"]=="whitelist" else "#60a5fa"
            d_col, b_col = st.columns([5, 1])
            with d_col:
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center;
                            padding:10px 12px; border-bottom:1px solid rgba(255,255,255,0.04);">
                    <div>
                        <span style="font-size:0.85rem; color:#c9d1e0;">{ds['filename']}</span>
                        <span style="margin-left:12px; background:rgba(0,0,0,0.3); color:{lt_color};
                               padding:2px 8px; border-radius:4px; font-size:0.7rem;">{ds['list_type']}</span>
                    </div>
                    <div style="font-size:0.78rem; color:#4b5d7a;">
                        {ds['row_count']:,} IPs · {ds['created_at'][:10]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with b_col:
                if st.button("🗑", key=f"del_ds_{ds['id']}", help="Delete dataset & remove IPs"):
                    delete_ip_dataset(ds["id"])
                    st.success("Dataset deleted"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
