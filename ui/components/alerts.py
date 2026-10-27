"""
Alerts — Expiry notifications and alert center for FreshSense.
"""
import streamlit as st
from datetime import date
from utils.data_manager import DataManager
from utils.helpers import alert_banner, item_card_html, empty_state, render_html


def render_alerts(dm: DataManager):
    """Alerts and notifications page."""

    hero_html = """
<div class="fs-hero" style="padding:24px 32px;">
    <div class="fs-hero-title" style="font-size:1.5rem;">🔔 Alert Center</div>
    <div class="fs-hero-subtitle">
        Stay on top of expiring items. FreshSense monitors your fridge 24/7
        and alerts you before food goes to waste.
    </div>
</div>
"""
    render_html(hero_html)

    expired = dm.get_expired_items()
    expiring_today = [i for i in dm.get_expiring_items(0) if i.get("days_until_expiry") == 0]
    expiring_1d = [i for i in dm.get_expiring_items(1) if i.get("days_until_expiry") == 1]
    expiring_2d = [i for i in dm.get_expiring_items(2) if i.get("days_until_expiry") == 2]
    expiring_3d = [i for i in dm.get_expiring_items(3) if i.get("days_until_expiry") == 3]

    total_alerts = len(expired) + len(expiring_today) + len(expiring_1d) + len(expiring_2d) + len(expiring_3d)

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🚨 Total Alerts", total_alerts)
    with c2:
        st.metric("❌ Expired", len(expired))
    with c3:
        st.metric("🔴 Today", len(expiring_today))
    with c4:
        st.metric("🟡 Within 3 Days", len(expiring_1d) + len(expiring_2d) + len(expiring_3d))

    st.markdown("")

    if total_alerts == 0:
        render_html(
            alert_banner("🎉", "<strong>No alerts!</strong> All items in your fridge are fresh. Keep it up!", "success")
        )
        render_html(
            empty_state("🎊", "All Clear!", "Your fridge is in perfect shape. No items need attention right now.")
        )
        return

    # ── Expired Items ─────────────────────────────────────────────────────
    if expired:
        render_html("""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
    <span style="font-size:1.8rem;" class="fs-pulse">🚨</span>
    <span style="color:#FCA5A5; font-size:1.2rem; font-weight:700;">EXPIRED — Remove Immediately</span>
</div>
""")

        for item in expired:
            col1, col2 = st.columns([10, 1])
            with col1:
                render_html(item_card_html(item))
            with col2:
                if st.button("🗑️", key=f"alert_del_{item.get('entry_id')}"):
                    dm.remove_item(item.get("entry_id"))
                    st.toast(f"Removed: {item.get('name')}", icon="🗑️")
                    st.rerun()

        st.markdown("")

    # ── Expiring Today ────────────────────────────────────────────────────
    if expiring_today:
        render_html("""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
    <span style="font-size:1.5rem;">🔴</span>
    <span style="color:#FCD34D; font-size:1.1rem; font-weight:700;">Expiring TODAY</span>
</div>
""")
        for item in expiring_today:
            render_html(item_card_html(item))
        st.markdown("")

    # ── Expiring Tomorrow ─────────────────────────────────────────────────
    if expiring_1d:
        render_html("""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
    <span style="font-size:1.5rem;">🟠</span>
    <span style="color:#FCD34D; font-size:1.1rem; font-weight:600;">Expiring Tomorrow</span>
</div>
""")
        for item in expiring_1d:
            render_html(item_card_html(item))
        st.markdown("")

    # ── Expiring in 2-3 Days ──────────────────────────────────────────────
    rest = expiring_2d + expiring_3d
    if rest:
        render_html("""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
    <span style="font-size:1.5rem;">🟡</span>
    <span style="color:#FCD34D; font-size:1.05rem; font-weight:600;">Expiring in 2-3 Days</span>
</div>
""")
        for item in rest:
            render_html(item_card_html(item))

    # ── Notification Simulation ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📲 Push Notification Preview")
    st.caption("When deployed, FreshSense will send real-time notifications to your phone.")

    if expired or expiring_today:
        urgent = expired + expiring_today
        for item in urgent[:3]:
            name = item.get("name", "Unknown")
            days = item.get("days_until_expiry", 0)
            if days < 0:
                msg = f"has EXPIRED {abs(days)} day(s) ago"
                icon = "🚨"
            else:
                msg = "expires TODAY"
                icon = "⏰"

            notif_html = f"""
<div style="background:linear-gradient(135deg, #1E293B 0%, #263348 100%);
            border:1px solid rgba(51,65,85,0.6); border-radius:14px;
            padding:16px 20px; margin-bottom:10px;
            display:flex; align-items:center; gap:14px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
    <span style="font-size:2rem;">{icon}</span>
    <div>
        <div style="color:#F1F5F9; font-weight:600; font-size:0.95rem;">FreshSense Alert</div>
        <div style="color:#CBD5E1; font-size:0.88rem;">
            <strong>{name}</strong> {msg}! Use it now or check the Recipes page for suggestions.
        </div>
        <div style="color:#64748B; font-size:0.75rem; margin-top:4px;">Just now · Your Fridge</div>
    </div>
</div>
"""
            render_html(notif_html)
    else:
        st.info("No urgent notifications at this time.")
