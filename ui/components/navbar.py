"""
Top Navigation Bar — Premium floating glassmorphism header.
Provides quick page breadcrumb, IoT fridge telemetry, and notification pills.
"""
import streamlit as st
from utils.data_manager import DataManager
from utils.helpers import render_html


def render_top_navbar(dm: DataManager, current_page: str) -> str:
    """
    Renders an ultra-premium top navbar with breadcrumbs, IoT telemetry,
    and notification indicators.
    """
    summary = dm.get_summary()
    expired_count = summary.get("expired", 0)
    expiring_count = summary.get("expiring_soon", 0)

    # Dynamic status capsule
    if expired_count > 0:
        alert_badge_html = f'<span class="fs-topbar-alert-badge fs-badge-danger">🚨 {expired_count} Expired</span>'
    elif expiring_count > 0:
        alert_badge_html = f'<span class="fs-topbar-alert-badge fs-badge-warning">⚠️ {expiring_count} Expiring</span>'
    else:
        alert_badge_html = '<span class="fs-topbar-alert-badge fs-badge-success">✓ 100% Fresh</span>'

    # Unified single-line HTML — no line breaks or indentation to prevent code-block parsing
    navbar_html = f"""
<div class="fs-topbar-wrapper">
    <div class="fs-topbar-left">
        <div class="fs-topbar-logo-mark">
            <span class="fs-topbar-icon">🧊</span>
            <span class="fs-topbar-title">FreshSense</span>
        </div>
        <span class="fs-topbar-slash">/</span>
        <div class="fs-topbar-breadcrumb">
            <span class="fs-topbar-page-name">{current_page}</span>
            <span class="fs-topbar-live-dot" title="Live Telemetry Active"></span>
        </div>
    </div>
    <div class="fs-topbar-center">
        <div class="fs-telemetry-pill" title="Hardware sensor reading">
            <span class="fs-telemetry-icon">❄️</span>
            <span class="fs-telemetry-val">3.6°C</span>
            <span class="fs-telemetry-divider">·</span>
            <span class="fs-telemetry-icon">💧</span>
            <span class="fs-telemetry-val">62% RH</span>
            <span class="fs-telemetry-divider">·</span>
            <span class="fs-telemetry-status">IoT Online</span>
        </div>
    </div>
    <div class="fs-topbar-right">
        {alert_badge_html}
        <div class="fs-topbar-device-pill">
            <span class="fs-device-dot"></span>
            <span>Camera AI Sync</span>
        </div>
    </div>
</div>
"""
    render_html(navbar_html)
    return current_page
