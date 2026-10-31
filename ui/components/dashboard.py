"""
Dashboard component — Overview page with hero, metrics, and quick-glance widgets.
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.data_manager import DataManager
from utils.helpers import alert_banner, status_badge, item_card_html, empty_state, render_html


def render_dashboard(dm: DataManager):
    """Main dashboard overview page."""

    # ── Hero Banner ───────────────────────────────────────────────────────
    today = date.today().strftime("%A, %B %d, %Y")
    summary = dm.get_summary()

    hero_html = f"""
<div class="fs-hero">
    <div class="fs-hero-title">
        🧊 Welcome to <span class="fs-hero-accent">FreshSense</span>
    </div>
    <div class="fs-hero-subtitle">
        Your intelligent fridge inventory system — keeping your food fresh, reducing waste,
        and suggesting recipes before items expire.<br/>
        <span style="color:#64748B; font-size:0.85rem;">📅 {today}</span>
    </div>
</div>
"""
    render_html(hero_html)

    # ── Urgent Alerts ─────────────────────────────────────────────────────
    expired = dm.get_expired_items()
    expiring = dm.get_expiring_items(days_threshold=3)

    if expired:
        names = ", ".join([i.get("name", "Unknown")[:20] for i in expired[:3]])
        more = f" +{len(expired) - 3} more" if len(expired) > 3 else ""
        render_html(
            alert_banner("🚨", f"<strong>{len(expired)} expired item(s)!</strong> {names}{more} — please remove from fridge.", "danger")
        )

    if expiring:
        names = ", ".join([i.get("name", "Unknown")[:20] for i in expiring[:3]])
        more = f" +{len(expiring) - 3} more" if len(expiring) > 3 else ""
        render_html(
            alert_banner("⚠️", f"<strong>{len(expiring)} item(s) expiring within 3 days!</strong> {names}{more}", "warning")
        )

    if not expired and not expiring:
        render_html(
            alert_banner("✅", "<strong>All clear!</strong> No items are expired or expiring soon. Your fridge is in great shape!", "success")
        )

    # ── Key Metrics ───────────────────────────────────────────────────────
    st.markdown("### 📊 At a Glance")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("🛒 Total Items", summary["total_items"])
    with m2:
        st.metric("📦 Unique Products", summary["unique_items"])
    with m3:
        st.metric("✅ Fresh", summary["fresh"])
    with m4:
        st.metric("⚠️ Expiring Soon", summary["expiring_soon"])
    with m5:
        st.metric("❌ Expired", summary["expired"])

    st.markdown("")

    # ── Two Column Layout ─────────────────────────────────────────────────
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown("### 🕐 Recently Added")
        items = dm.get_all_items()
        if items:
            recent = sorted(items, key=lambda x: x.get("scanned_at", ""), reverse=True)[:5]
            for item in recent:
                render_html(item_card_html(item))
        else:
            render_html(
                empty_state("📦", "No items yet", "Scan barcodes or add items manually to get started.")
            )

    with right_col:
        st.markdown("### 🎯 Freshness Status")
        status_dist = dm.get_status_distribution()

        if sum(status_dist.values()) > 0:
            for status_name, count in status_dist.items():
                total = summary["total_items"] or 1
                pct = round((count / total) * 100)

                if status_name == "Fresh":
                    color = "#10B981"
                    emoji = "🟢"
                elif status_name == "Expiring Soon":
                    color = "#F59E0B"
                    emoji = "🟡"
                else:
                    color = "#EF4444"
                    emoji = "🔴"

                card_status_html = f"""
<div class="fs-card" style="padding:14px 18px; margin-bottom:10px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="font-size:1.2rem; margin-right:8px;">{emoji}</span>
            <span style="color:#F1F5F9; font-weight:600;">{status_name}</span>
        </div>
        <div style="text-align:right;">
            <span style="font-size:1.6rem; font-weight:700; color:{color};">{count}</span>
            <span style="color:#64748B; font-size:0.8rem; margin-left:4px;">({pct}%)</span>
        </div>
    </div>
    <div class="fs-progress-container" style="margin-top:10px;">
        <div class="fs-progress-bar" style="width:{pct}%; background:{color};"></div>
    </div>
</div>
"""
                render_html(card_status_html)

        st.markdown("")

        # Category Breakdown
        st.markdown("### 🏷️ Categories")
        cat_dist = dm.get_category_distribution()
        if cat_dist:
            cat_emojis = {
                "Dairy": "🥛", "Dairy & Eggs": "🥚", "Bakery": "🍞",
                "Beverages": "🥤", "Snacks": "🍿", "Spreads": "🫙",
                "Produce": "🥬", "Fruit": "🍌", "Vegetable": "🥕", "Vegetables": "🥦",
                "Meat": "🥩", "Seafood": "🐟",
                "Frozen": "🧊", "Packaged Goods": "📦", "General": "🛒",
                "Potato crisps": "🥔", "Protein": "💪",
            }
            for cat, count in sorted(cat_dist.items(), key=lambda x: -x[1]):
                emoji = cat_emojis.get(cat, "🛒")
                cat_row_html = f"""
<div style="display:flex; justify-content:space-between; align-items:center;
            padding:8px 14px; margin-bottom:4px; border-radius:8px;
            background:rgba(30,41,59,0.4); border:1px solid rgba(51,65,85,0.3);">
    <span style="color:#CBD5E1;">{emoji} {cat}</span>
    <span style="color:#94A3B8; font-weight:600; font-family:'JetBrains Mono',monospace; font-size:0.85rem;">{count}</span>
</div>
"""
                render_html(cat_row_html)
        else:
            st.caption("No categories to display.")

    # ── Expiry Timeline ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📅 Expiry Timeline")
    timeline = dm.get_expiry_timeline()
    if timeline:
        df = pd.DataFrame(timeline, columns=["Expiry Date", "Items"])
        df["Expiry Date"] = pd.to_datetime(df["Expiry Date"])
        st.bar_chart(df.set_index("Expiry Date"), color="#10B981", height=250)
    else:
        st.info("No items with expiry dates to chart.")
