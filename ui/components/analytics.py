"""
Analytics — Visual insights and charts for FreshSense inventory data.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.data_manager import DataManager
from utils.helpers import empty_state, render_html


def render_analytics(dm: DataManager):
    """Analytics and visualization page."""

    hero_html = """
<div class="fs-hero" style="padding:24px 32px;">
    <div class="fs-hero-title" style="font-size:1.5rem;">📈 Waste & Fresh Analytics</div>
    <div class="fs-hero-subtitle">
        Deep insights into your fridge patterns, freshness status, and category shelf life.
    </div>
</div>
"""
    render_html(hero_html)

    items = dm.get_all_items()

    if not items:
        render_html(
            empty_state("📊", "No data yet", "Start scanning or adding items to see analytics.")
        )
        return

    summary = dm.get_summary()

    # ── Overview Metrics (Balanced 4-column layout) ─────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📦 Total Items", summary["total_items"])
    with c2:
        st.metric("🏷️ Unique Products", summary["unique_items"])
    with c3:
        st.metric("📂 Categories", summary["categories"])
    with c4:
        st.metric("📅 Earliest Expiry", summary["earliest_expiry"] or "N/A")

    st.markdown("")

    # ── Freshness & Category Distribution ─────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 🎯 Freshness Distribution")
        status_dist = dm.get_status_distribution()
        df_status = pd.DataFrame(
            list(status_dist.items()),
            columns=["Status", "Count"],
        )
        if not df_status.empty and df_status["Count"].sum() > 0:
            df_status = df_status.set_index("Status")
            st.bar_chart(df_status, color="#10B981", horizontal=True, height=240)

    with col_right:
        st.markdown("### 🏷️ Items by Category")
        cat_dist = dm.get_category_distribution()
        if cat_dist:
            df_cat = pd.DataFrame(
                list(cat_dist.items()),
                columns=["Category", "Count"],
            )
            df_cat = df_cat.sort_values("Count", ascending=False).set_index("Category")
            st.bar_chart(df_cat, color="#3B82F6", height=240)

    st.markdown("---")

    # ── Average Shelf Life by Category ────────────────────────────────────
    st.markdown("### ⏳ Average Shelf Life by Category")
    st.caption("Estimated shelf life benchmarked across tracked product categories.")

    products = dm.get_product_catalog()
    cat_shelf = {}
    cat_counts = {}
    for _, prod in products.items():
        cat = prod.get("category", "General")
        shelf = prod.get("shelf_life_days", prod.get("shelf_life", 0))
        cat_shelf[cat] = cat_shelf.get(cat, 0) + shelf
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    for _, prod in getattr(dm, "items_shelf_life", {}).items():
        cat = prod.get("category", "General")
        shelf = prod.get("shelf_life", 0)
        cat_shelf[cat] = cat_shelf.get(cat, 0) + shelf
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    if cat_shelf:
        avg_shelf = []
        for cat in cat_shelf:
            avg = cat_shelf[cat] / cat_counts[cat]
            avg_shelf.append((cat, round(avg)))

        avg_shelf.sort(key=lambda x: -x[1])
        max_days = max((x[1] for x in avg_shelf), default=1)

        # Distribute neatly across two columns to preserve visual structure
        col_s1, col_s2 = st.columns(2)
        mid = (len(avg_shelf) + 1) // 2

        def render_shelf_items(item_list):
            for cat, avg_days in item_list:
                if avg_days > 30:
                    color = "#10B981"
                elif avg_days > 14:
                    color = "#3B82F6"
                elif avg_days > 7:
                    color = "#F59E0B"
                else:
                    color = "#EF4444"

                bar_width = min(100, int((avg_days / max_days) * 100))
                shelf_row_html = f"""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:8px; padding:6px 12px; background:rgba(30,41,59,0.3); border:1px solid rgba(255,255,255,0.04); border-radius:10px;">
    <span style="color:#CBD5E1; min-width:140px; font-size:0.88rem; font-weight:500;">{cat}</span>
    <div style="flex:1; height:8px; background:rgba(51,65,85,0.4); border-radius:4px; overflow:hidden;">
        <div style="width:{bar_width}%; height:100%; background:{color}; border-radius:4px;"></div>
    </div>
    <span style="color:{color}; font-family:'JetBrains Mono',monospace; font-size:0.85rem; font-weight:700; min-width:55px; text-align:right;">{avg_days}d</span>
</div>
"""
                render_html(shelf_row_html)

        with col_s1:
            render_shelf_items(avg_shelf[:mid])

        with col_s2:
            render_shelf_items(avg_shelf[mid:])
    else:
        st.caption("No product catalog data available.")

    # ── Raw Data Export ───────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📤 Export Raw Data"):
        st.markdown("Download your inventory data for external analysis.")
        df_export = pd.DataFrame(items)
        st.dataframe(df_export, use_container_width=True, height=300)

        csv = df_export.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name="freshsense_inventory.csv",
            mime="text/csv",
        )
