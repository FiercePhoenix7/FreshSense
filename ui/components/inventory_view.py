"""
Inventory View — Full inventory table with filtering, search, and item management.
"""
import streamlit as st
import pandas as pd
from utils.data_manager import DataManager
from utils.helpers import item_card_html, status_badge, empty_state, render_html


def render_inventory(dm: DataManager):
    """Full inventory listing with search and filters."""

    hero_html = """
<div class="fs-hero" style="padding:24px 32px;">
    <div class="fs-hero-title" style="font-size:1.5rem;">📦 Fridge Inventory</div>
    <div class="fs-hero-subtitle">
        View, search, and manage all items currently tracked in your fridge.
    </div>
</div>
"""
    render_html(hero_html)

    items = dm.get_all_items()

    if not items:
        render_html(
            empty_state("🧊", "Your fridge is empty!", "Scan barcodes with the camera or add items manually to start tracking.")
        )
        return

    # ── Filters ───────────────────────────────────────────────────────────
    st.markdown("### 🔍 Filter & Search")
    f1, f2, f3, f4 = st.columns([3, 2, 2, 1])

    with f1:
        search = st.text_input("🔎 Search items", placeholder="Search by name or category...")
    with f2:
        categories = ["All"] + dm.get_categories()
        selected_cat = st.selectbox("🏷️ Category", categories)
    with f3:
        status_opts = ["All", "Fresh", "Expiring Soon", "Expired"]
        selected_status = st.selectbox("📊 Status", status_opts)
    with f4:
        sort_by = st.selectbox("↕️ Sort", ["Expiry ↑", "Expiry ↓", "Name", "Recent"])

    # Apply filters
    filtered = items.copy()

    if search:
        search_lower = search.lower()
        filtered = [
            i for i in filtered
            if search_lower in i.get("name", "").lower()
            or search_lower in i.get("category", "").lower()
        ]

    if selected_cat != "All":
        filtered = [i for i in filtered if i.get("category") == selected_cat]

    if selected_status != "All":
        filtered = [i for i in filtered if i.get("status") == selected_status]

    # Sort
    if sort_by == "Expiry ↑":
        filtered.sort(key=lambda x: x.get("expiry_date", "9999-99-99"))
    elif sort_by == "Expiry ↓":
        filtered.sort(key=lambda x: x.get("expiry_date", "0000-00-00"), reverse=True)
    elif sort_by == "Name":
        filtered.sort(key=lambda x: x.get("name", "").lower())
    elif sort_by == "Recent":
        filtered.sort(key=lambda x: x.get("scanned_at", ""), reverse=True)

    # ── Results Summary ───────────────────────────────────────────────────
    count_summary_html = f"""
<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0;">
    <span style="color:#94A3B8; font-size:0.9rem;">
        Showing <strong style="color:#F1F5F9;">{len(filtered)}</strong> of {len(items)} items
    </span>
</div>
"""
    render_html(count_summary_html)

    # ── View Mode Toggle ──────────────────────────────────────────────────
    view_mode = st.radio("View Mode", ["Card View", "Table View"], horizontal=True, label_visibility="collapsed")

    if view_mode == "Card View":
        for item in filtered:
            col_card, col_action = st.columns([10, 1])
            with col_card:
                render_html(item_card_html(item))
            with col_action:
                entry_id = item.get("entry_id")
                if st.button("🗑️", key=f"del_{entry_id}", help="Remove item"):
                    dm.remove_item(entry_id)
                    st.toast(f"Removed: {item.get('name', 'Unknown')}", icon="🗑️")
                    st.rerun()
    else:
        df = pd.DataFrame(filtered)
        if not df.empty:
            display_cols = ["entry_id", "name", "category", "expiry_date", "days_until_expiry", "status", "scanned_at"]
            available_cols = [c for c in display_cols if c in df.columns]
            df_display = df[available_cols].copy()

            rename_map = {
                "entry_id": "ID",
                "name": "Product",
                "category": "Category",
                "expiry_date": "Expires",
                "days_until_expiry": "Days Left",
                "status": "Status",
                "scanned_at": "Scanned At",
            }
            df_display.rename(columns=rename_map, inplace=True)

            def color_status(val):
                if val == "Fresh":
                    return "color: #34D399"
                elif val == "Expiring Soon":
                    return "color: #FCD34D"
                elif val == "Expired":
                    return "color: #FCA5A5"
                return ""

            styled = df_display.style.applymap(color_status, subset=["Status"] if "Status" in df_display.columns else [])
            st.dataframe(styled, use_container_width=True, height=450)

        st.markdown("")
        if st.button("🗑️ Clear All Expired Items", type="secondary"):
            expired = dm.get_expired_items()
            for item in expired:
                dm.remove_item(item.get("entry_id"))
            if expired:
                st.toast(f"Removed {len(expired)} expired item(s)!", icon="🗑️")
                st.rerun()
            else:
                st.info("No expired items to remove.")
