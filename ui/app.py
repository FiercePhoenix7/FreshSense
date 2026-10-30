"""
FreshSense — Smart Fridge Inventory Dashboard
Main Streamlit application entry point.

Run with: streamlit run ui/app.py
"""
import streamlit as st

# ── Page Config (must be first Streamlit command) ─────────────────────────
st.set_page_config(
    page_title="FreshSense · Smart Fridge OS",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports ───────────────────────────────────────────────────────────────
import json
import os
import sys
from datetime import datetime, date, timedelta

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from components.sidebar import render_sidebar
from components.navbar import render_top_navbar
from components.dashboard import render_dashboard
from components.inventory_view import render_inventory
from components.add_item import render_add_item
from components.alerts import render_alerts
from components.recipes import render_recipes
from components.analytics import render_analytics
from utils.data_manager import DataManager
from utils.theme import inject_custom_css

# ── Custom CSS Injection ──────────────────────────────────────────────────
inject_custom_css()

# ── Session State Initialization ──────────────────────────────────────────
if "data_manager" not in st.session_state:
    st.session_state.data_manager = DataManager(PROJECT_ROOT)

if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

if "notifications" not in st.session_state:
    st.session_state.notifications = []

# Fetch central DataManager & reload if modified
dm = st.session_state.data_manager
dm.reload()

# ── Real-Time File Sync Fragment (Watches inventory.json every 1s) ────────
@st.fragment(run_every="1s")
def check_external_sync(data_mgr: DataManager):
    """
    Background fragment that polls file stats every second.
    If an external script (e.g. camera scanner) writes to inventory.json,
    it triggers an immediate rerun so the dashboard always shows the latest version.
    """
    if data_mgr.has_inventory_changed():
        st.toast("📥 Inventory updated from external scan!", icon="🔄")
        st.rerun()

check_external_sync(dm)

# ── Sidebar Navigation ───────────────────────────────────────────────────
selected_page = render_sidebar(dm)

# ── Top Navigation Bar & Action Ribbon ───────────────────────────────────
active_page = render_top_navbar(dm, selected_page)

# ── Toast Notifications for Expiring Items (once per session alert) ───────
expiring_items = dm.get_expiring_items(days_threshold=3)
expired_items = dm.get_expired_items()

if "alerts_toasted" not in st.session_state:
    if expired_items:
        st.toast(f"🚨 {len(expired_items)} item(s) have EXPIRED!", icon="🚨")
    if expiring_items:
        st.toast(f"⚠️ {len(expiring_items)} item(s) expiring within 3 days!", icon="⚠️")
    st.session_state.alerts_toasted = True

# ── Page Routing ──────────────────────────────────────────────────────────
if active_page == "Dashboard":
    render_dashboard(dm)
elif active_page == "Inventory":
    render_inventory(dm)
elif active_page == "Add Item":
    render_add_item(dm)
elif active_page == "Alerts":
    render_alerts(dm)
elif active_page == "Recipes":
    render_recipes(dm)
elif active_page == "Analytics":
    render_analytics(dm)
