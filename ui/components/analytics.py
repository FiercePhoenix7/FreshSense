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
    <div class="fs-hero-title" style="font-size:1.5rem;">📈 Inventory Analytics</div>
    <div class="fs-hero-subtitle">
        Deep insights into your fridge patterns, waste tracking, and consumption trends.
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

    # ── Overview Metrics ──────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("📦 Total Scans", summary["total_items"])
    with c2:
        st.metric("🏷️ Unique Products", summary["unique_items"])
    with c3:
        st.metric("📂 Categories", summary["categories"])
    with c4:
        brands = len(dm.get_brands())
        st.metric("🏢 Brands", brands)
    with c5:
        st.metric("📅 Earliest Expiry", summary["earliest_expiry"] or "N/A")

    st.markdown("")

    # ── Charts Row 1 ──────────────────────────────────────────────────────
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
            st.bar_chart(df_status, color="#10B981", horizontal=True, height=200)

    with col_right:
        st.markdown("### 🏷️ Items by Category")
        cat_dist = dm.get_category_distribution()
        if cat_dist:
            df_cat = pd.DataFrame(
                list(cat_dist.items()),
                columns=["Category", "Count"],
            )
            df_cat = df_cat.sort_values("Count", ascending=False).set_index("Category")
            st.bar_chart(df_cat, color="#3B82F6", height=200)

    st.markdown("")

    # ── Charts Row 2 ──────────────────────────────────────────────────────
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.markdown("### 📅 Expiry Timeline")
        timeline = dm.get_expiry_timeline()
        if timeline:
            df_timeline = pd.DataFrame(timeline, columns=["Date", "Items"])
            df_timeline["Date"] = pd.to_datetime(df_timeline["Date"])
            df_timeline = df_timeline.set_index("Date")
            st.line_chart(df_timeline, color="#F59E0B", height=250)
        else:
            st.info("No expiry date data available.")

    with col_right2:
        st.markdown("### 📡 Data Source Breakdown")
        source_dist = {}
        for item in items:
            src = item.get("source", "unknown")
            src_display = {
                "catalog": "📚 Product Catalog",
                "openfoodfacts": "🌐 Open Food Facts",
                "fallback": "📦 Fallback/Generic",
                "gs1": "📊 GS1 Barcode",
                "manual": "✋ Manual Entry",
                "manual_quick": "⚡ Quick Add",
                "receipt": "🧾 Receipt",
            }.get(src, f"❓ {src}")
            source_dist[src_display] = source_dist.get(src_display, 0) + 1

        if source_dist:
            df_source = pd.DataFrame(
                list(source_dist.items()),
                columns=["Source", "Count"],
            )
            df_source = df_source.sort_values("Count", ascending=False).set_index("Source")
            st.bar_chart(df_source, color="#8B5CF6", horizontal=True, height=200)

    st.markdown("---")

    # ── Scan Activity ─────────────────────────────────────────────────────
    st.markdown("### 🕐 Scanning Activity Over Time")
    scan_dates = {}
    for item in items:
        scanned = item.get("scanned_at", "")
        if scanned:
            day = scanned.split(" ")[0]
            scan_dates[day] = scan_dates.get(day, 0) + 1

    if scan_dates:
        df_scans = pd.DataFrame(
            list(scan_dates.items()),
            columns=["Date", "Items Scanned"],
        )
        df_scans["Date"] = pd.to_datetime(df_scans["Date"])
        df_scans = df_scans.sort_values("Date").set_index("Date")
        st.area_chart(df_scans, color="#10B981", height=200)
    else:
        st.info("No scan data available yet.")

    # ── Brand Leaderboard ─────────────────────────────────────────────────
    st.markdown("---")
    col_brands, col_shelf = st.columns(2)

    with col_brands:
        st.markdown("### 🏆 Top Brands in Your Fridge")
        brand_dist = {}
        for item in items:
            brand = item.get("brand", "Unknown")
            brand_dist[brand] = brand_dist.get(brand, 0) + 1

        if brand_dist:
            sorted_brands = sorted(brand_dist.items(), key=lambda x: -x[1])
            for i, (brand, count) in enumerate(sorted_brands[:8]):
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
                bar_width = int((count / sorted_brands[0][1]) * 100)
                brand_row_html = f"""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
    <span style="min-width:30px; font-size:1.1rem;">{medal}</span>
    <span style="color:#F1F5F9; font-weight:500; min-width:140px;">{brand}</span>
    <div style="flex:1; height:8px; background:rgba(51,65,85,0.4); border-radius:4px; overflow:hidden;">
        <div style="width:{bar_width}%; height:100%; background:linear-gradient(90deg, #3B82F6, #8B5CF6); border-radius:4px;"></div>
    </div>
    <span style="color:#94A3B8; font-family:'JetBrains Mono',monospace; font-size:0.85rem; min-width:30px; text-align:right;">{count}</span>
</div>
"""
                render_html(brand_row_html)

    with col_shelf:
        st.markdown("### ⏳ Average Shelf Life by Category")
        products = dm.get_product_catalog()
        cat_shelf = {}
        cat_counts = {}
        for barcode, prod in products.items():
            cat = prod.get("category", "General")
            shelf = prod.get("shelf_life_days", 0)
            cat_shelf[cat] = cat_shelf.get(cat, 0) + shelf
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        if cat_shelf:
            avg_shelf = []
            for cat in cat_shelf:
                avg = cat_shelf[cat] / cat_counts[cat]
                avg_shelf.append((cat, round(avg)))

            avg_shelf.sort(key=lambda x: -x[1])

            for cat, avg_days in avg_shelf:
                if avg_days > 30:
                    color = "#10B981"
                elif avg_days > 14:
                    color = "#3B82F6"
                elif avg_days > 7:
                    color = "#F59E0B"
                else:
                    color = "#EF4444"

                bar_width = min(100, int((avg_days / max(x[1] for x in avg_shelf)) * 100))
                shelf_row_html = f"""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
    <span style="color:#CBD5E1; min-width:140px; font-size:0.9rem;">{cat}</span>
    <div style="flex:1; height:8px; background:rgba(51,65,85,0.4); border-radius:4px; overflow:hidden;">
        <div style="width:{bar_width}%; height:100%; background:{color}; border-radius:4px;"></div>
    </div>
    <span style="color:{color}; font-family:'JetBrains Mono',monospace; font-size:0.85rem; font-weight:600; min-width:60px; text-align:right;">{avg_days}d</span>
</div>
"""
                render_html(shelf_row_html)
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
