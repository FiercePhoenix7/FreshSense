"""
Sidebar component — Ultra-premium navigation & IoT fridge telemetry hub.
"""
import streamlit as st
from utils.data_manager import DataManager
from utils.helpers import render_html


def render_sidebar(dm: DataManager) -> str:
    """Renders the ultra-premium sidebar and returns the selected page name."""
    
    # Initialize session state for active page
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    summary = dm.get_summary()
    total_items = summary.get("total_items", 0)
    fresh_items = summary.get("fresh", 0)
    expiring_items = summary.get("expiring_soon", 0)
    expired_items = summary.get("expired", 0)
    total_alerts = expired_items + expiring_items

    # Compute Freshness Health Index
    health_score = round((fresh_items / total_items * 100)) if total_items > 0 else 100
    if health_score >= 80:
        health_color = "#10B981"
        health_status = "Optimal Fresh"
    elif health_score >= 50:
        health_color = "#F59E0B"
        health_status = "Attention Needed"
    else:
        health_color = "#EF4444"
        health_status = "High Waste Risk"

    with st.sidebar:
        # ── 1. Luxury Brand Header ──────────────────────────────────────
        brand_html = f"""
<div class="fs-brand-card">
    <div class="fs-brand-glow"></div>
    <div class="fs-brand-header">
        <div class="fs-brand-icon-box">
            <span class="fs-brand-icon">🧊</span>
        </div>
        <div class="fs-brand-meta">
            <div class="fs-brand-title">
                <span class="fs-brand-fresh">FRESH</span><span class="fs-brand-sense">SENSE</span>
            </div>
            <div class="fs-brand-sub">Smart Fridge OS · v2.4</div>
        </div>
    </div>
    <div class="fs-brand-pill-bar">
        <span class="fs-pulse-dot"></span>
        <span class="fs-pill-text">IoT Camera Sensor Live</span>
        <span class="fs-pill-chip">Active</span>
    </div>
</div>
"""
        render_html(brand_html)

        render_html('<div class="fs-nav-divider"></div>')

        # ── 2. Navigation Menu ──────────────────────────────────────────
        render_html("""
<div class="fs-menu-label">
    <span>MAIN NAVIGATION</span>
    <span class="fs-menu-count">6 Modules</span>
</div>
""")

        pages = ["Dashboard", "Inventory", "Add Item", "Alerts", "Recipes", "Analytics"]

        def format_nav_label(page_key: str) -> str:
            if page_key == "Dashboard":
                return "📊  Overview Dashboard"
            elif page_key == "Inventory":
                return f"📦  Fridge Inventory ({total_items})"
            elif page_key == "Add Item":
                return "➕  Add Product / Barcode"
            elif page_key == "Alerts":
                if total_alerts > 0:
                    return f"🔔  Alert Center  ({total_alerts} ⚠️)"
                return "🔔  Alert Center (All Clean)"
            elif page_key == "Recipes":
                return "🍳  AI Generated Recipes"
            elif page_key == "Analytics":
                return "📈  Waste & Fresh Analytics"
            return page_key

        current_idx = pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0

        selected_page = st.radio(
            "Navigation Menu",
            pages,
            index=current_idx,
            format_func=format_nav_label,
            key="sidebar_nav_radio",
            label_visibility="collapsed",
        )

        if selected_page != st.session_state.current_page:
            st.session_state.current_page = selected_page
            st.rerun()

        render_html('<div class="fs-nav-divider"></div>')

        # ── 3. Fridge Freshness Health Dial ──────────────────────────────
        r_val = 16 if health_score >= 80 else 239
        g_val = 185 if health_score >= 80 else 68
        b_val = 129 if health_score >= 80 else 68
        dial_html = f"""
<div class="fs-telemetry-card">
    <div class="fs-telemetry-header">
        <span class="fs-telemetry-title">FRIDGE HEALTH INDEX</span>
        <span class="fs-telemetry-chip" style="background: rgba({r_val}, {g_val}, {b_val}, 0.15); color: {health_color};">
            {health_status}
        </span>
    </div>
    
    <div class="fs-dial-container">
        <div class="fs-dial-graphic">
            <svg viewBox="0 0 100 100" class="fs-dial-svg">
                <circle cx="50" cy="50" r="42" class="fs-dial-bg" />
                <circle cx="50" cy="50" r="42" class="fs-dial-fg" 
                        style="stroke: {health_color}; stroke-dasharray: {health_score * 2.64}, 264;" />
            </svg>
            <div class="fs-dial-number-box">
                <span class="fs-dial-number" style="color: {health_color};">{health_score}%</span>
                <span class="fs-dial-label">Freshness</span>
            </div>
        </div>
        <div class="fs-telemetry-stats">
            <div class="fs-stat-line">
                <span class="fs-stat-dot" style="background:#10B981;"></span>
                <span class="fs-stat-name">Fresh Items</span>
                <span class="fs-stat-value">{fresh_items}</span>
            </div>
            <div class="fs-stat-line">
                <span class="fs-stat-dot" style="background:#F59E0B;"></span>
                <span class="fs-stat-name">Expiring Soon</span>
                <span class="fs-stat-value" style="color:#FCD34D;">{expiring_items}</span>
            </div>
            <div class="fs-stat-line">
                <span class="fs-stat-dot" style="background:#EF4444;"></span>
                <span class="fs-stat-name">Expired Items</span>
                <span class="fs-stat-value" style="color:#FCA5A5;">{expired_items}</span>
            </div>
        </div>
    </div>
</div>
"""
        render_html(dial_html)

        # ── 4. Urgent Expiry Radar ──────────────────────────────────────
        expiring_list = dm.get_expiring_items(days_threshold=3)
        if expiring_list:
            render_html("""
<div class="fs-menu-label" style="margin-top: 14px;">
    <span>⏰ EXPIRY RADAR</span>
    <span class="fs-radar-live">LIVE</span>
</div>
""")

            items_html = ""
            for item in expiring_list[:4]:
                name = item.get("name", "Unknown")
                if len(name) > 20:
                    name = name[:18] + "…"
                days = item.get("days_until_expiry", 0)

                if days == 0:
                    tag_color = "#EF4444"
                    tag_text = "TODAY"
                elif days == 1:
                    tag_color = "#F59E0B"
                    tag_text = "TOMORROW"
                else:
                    tag_color = "#FCD34D"
                    tag_text = f"{days}D LEFT"

                items_html += f"""
<div class="fs-radar-item">
    <div class="fs-radar-left">
        <span class="fs-radar-dot" style="background:{tag_color};"></span>
        <span class="fs-radar-name">{name}</span>
    </div>
    <span class="fs-radar-tag" style="color:{tag_color}; border-color:{tag_color}40; background:{tag_color}15;">
        {tag_text}
    </span>
</div>
"""
            render_html(f'<div class="fs-radar-list">{items_html}</div>')

    return st.session_state.current_page
