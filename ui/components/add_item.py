"""
Add Item — Manual item entry form for FreshSense.
"""
import streamlit as st
from datetime import date, timedelta
from utils.data_manager import DataManager
from utils.helpers import render_html


CATEGORY_OPTIONS = [
    "General", "Fruit", "Vegetable", "Dairy", "Dairy & Eggs", "Bakery", "Beverages",
    "Snacks", "Spreads", "Produce", "Meat", "Seafood",
    "Frozen", "Packaged Goods", "Condiments", "Grains & Cereals",
    "Canned Goods", "Ready-to-Eat", "Desserts", "Other",
]

COMMON_ITEMS = [
    {"name": "Milk (1L)", "category": "Dairy", "shelf_days": 7},
    {"name": "Egg", "category": "Dairy", "shelf_days": 21},
    {"name": "Bread", "category": "Bakery", "shelf_days": 5},
    {"name": "Butter (100g)", "category": "Dairy", "shelf_days": 30},
    {"name": "Curd (400g)", "category": "Dairy", "shelf_days": 7},
    {"name": "Cheese Slice", "category": "Dairy", "shelf_days": 60},
    {"name": "Paneer (200g)", "category": "Dairy", "shelf_days": 12},
    {"name": "Chicken (500g)", "category": "Meat", "shelf_days": 3},
    {"name": "Tomato", "category": "Vegetable", "shelf_days": 7},
    {"name": "Banana", "category": "Fruit", "shelf_days": 5},
    {"name": "Carrot", "category": "Vegetable", "shelf_days": 21},
    {"name": "Yogurt (400g)", "category": "Dairy", "shelf_days": 14},
]


def render_add_item(dm: DataManager):
    """Manual item entry page."""

    hero_html = """
<div class="fs-hero" style="padding:24px 32px;">
    <div class="fs-hero-title" style="font-size:1.5rem;">➕ Add Item to Fridge</div>
    <div class="fs-hero-subtitle">
        Manually add items when camera scanning isn't available. Use quick-add for common items
        or fill in the form below.
    </div>
</div>
"""
    render_html(hero_html)

    # ── Quick Add Section ─────────────────────────────────────────────────
    st.markdown("### ⚡ Quick Add — Common Items")
    st.caption("Tap to instantly add with auto-calculated expiry dates.")

    cols = st.columns(4)
    for idx, item in enumerate(COMMON_ITEMS):
        col = cols[idx % 4]
        with col:
            shelf_days = item["shelf_days"]
            exp = date.today() + timedelta(days=shelf_days)
            btn_label = f"{item['name']}\n({shelf_days}d shelf life)"

            if st.button(
                btn_label,
                key=f"quick_{idx}",
                use_container_width=True,
            ):
                dm.add_item(
                    name=item["name"],
                    category=item["category"],
                    expiry_date=exp.strftime("%Y-%m-%d"),
                )
                st.toast(f"✅ Added: {item['name']} (expires {exp})", icon="✅")
                st.rerun()

    st.markdown("---")

    # ── Detailed Form ─────────────────────────────────────────────────────
    st.markdown("### 📝 Detailed Entry")

    with st.form("add_item_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            name = st.text_input(
                "Product Name *",
                placeholder="e.g. Banana, Milk (1L)",
            )
            category = st.selectbox("Category", CATEGORY_OPTIONS)

        with c2:
            expiry_date = st.date_input(
                "Expiry Date *",
                value=date.today() + timedelta(days=7),
                min_value=date.today() - timedelta(days=365),
                max_value=date.today() + timedelta(days=730),
            )

        st.markdown("")

        col_submit, col_info = st.columns([1, 3])
        with col_submit:
            submitted = st.form_submit_button(
                "🧊 Add to Fridge",
                type="primary",
                use_container_width=True,
            )
        with col_info:
            st.caption("Fields marked with * are required.")

        if submitted:
            if not name or not name.strip():
                st.error("❌ Product name is required!")
            else:
                dm.add_item(
                    name=name.strip(),
                    category=category,
                    expiry_date=expiry_date.strftime("%Y-%m-%d"),
                )
                st.success(f"✅ **{name}** added to your fridge inventory!")
                st.balloons()

    # ── Recently Added Preview ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🕐 Recently Added")
    items = dm.get_all_items()
    recent_items = sorted(items, key=lambda x: x.get("scanned_at", ""), reverse=True)

    if recent_items:
        for item in recent_items[:5]:
            item_row_html = f"""
<div class="fs-card" style="padding:12px 18px; margin-bottom:6px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="color:#F1F5F9; font-weight:600;">{item.get('name', 'Unknown')}</span>
            <span style="color:#64748B; font-size:0.82rem; margin-left:8px;">{item.get('category', 'General')}</span>
        </div>
        <div style="color:#94A3B8; font-family:'JetBrains Mono', monospace; font-size:0.82rem;">
            📅 {item.get('expiry_date', 'N/A')}
        </div>
    </div>
</div>
"""
            render_html(item_row_html)
    else:
        st.caption("No items added yet.")
