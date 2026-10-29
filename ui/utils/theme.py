"""
Custom CSS theme for FreshSense dashboard.
Ultra-premium dark glassmorphism design with neon accents and luxury micro-interactions.
"""
import streamlit as st


def inject_custom_css():
    st.markdown("""
    <style>
    /* ── Google Fonts Import ────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    /* ── Root Design System Variables ───────────────────────── */
    :root {
        --fs-primary: #10B981;
        --fs-primary-glow: rgba(16, 185, 129, 0.4);
        --fs-primary-subtle: rgba(16, 185, 129, 0.12);
        --fs-secondary: #06B6D4;
        --fs-accent-blue: #3B82F6;
        --fs-accent-purple: #8B5CF6;
        --fs-danger: #EF4444;
        --fs-danger-glow: rgba(239, 68, 68, 0.35);
        --fs-warning: #F59E0B;
        --fs-warning-glow: rgba(245, 158, 11, 0.35);
        --fs-bg-main: #090D16;
        --fs-bg-surface: #0F172A;
        --fs-bg-surface-elevated: #162036;
        --fs-text-heading: #F8FAFC;
        --fs-text-body: #CBD5E1;
        --fs-text-muted: #64748B;
        --fs-border-subtle: rgba(255, 255, 255, 0.08);
        --fs-border-glow: rgba(16, 185, 129, 0.25);
        --fs-font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        --fs-font-mono: 'JetBrains Mono', monospace;
    }

    /* ── Global App Canvas ──────────────────────────────────── */
    .stApp {
        background: radial-gradient(circle at 15% 10%, rgba(16, 185, 129, 0.07) 0%, transparent 40%),
                    radial-gradient(circle at 85% 20%, rgba(59, 130, 246, 0.06) 0%, transparent 45%),
                    radial-gradient(circle at 50% 90%, rgba(139, 92, 246, 0.05) 0%, transparent 50%),
                    linear-gradient(180deg, #090D16 0%, #0D1322 50%, #090D16 100%) !important;
        font-family: var(--fs-font-sans) !important;
        color: var(--fs-text-body);
    }

    .main .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1440px;
    }

    /* ── Sticky Top Navigation Bar ──────────────────────────── */
    .fs-topbar-wrapper {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 24px;
        background: rgba(15, 23, 42, 0.75);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        margin-bottom: 16px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }

    .fs-topbar-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .fs-topbar-logo-mark {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .fs-topbar-icon {
        font-size: 1.3rem;
        filter: drop-shadow(0 0 10px var(--fs-primary-glow));
    }

    .fs-topbar-title {
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #10B981 0%, #38BDF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .fs-topbar-slash {
        color: var(--fs-text-muted);
        font-size: 1.1rem;
        font-weight: 300;
    }

    .fs-topbar-breadcrumb {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .fs-topbar-page-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: var(--fs-text-heading);
        letter-spacing: -0.01em;
    }

    .fs-topbar-live-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #10B981;
        box-shadow: 0 0 10px #10B981;
        animation: fs-pulse-glow 2s infinite ease-in-out;
    }

    .fs-topbar-center {
        display: flex;
        align-items: center;
    }

    .fs-telemetry-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 9999px;
        font-size: 0.8rem;
        font-family: var(--fs-font-mono);
    }

    .fs-telemetry-icon {
        font-size: 0.85rem;
    }

    .fs-telemetry-val {
        color: #38BDF8;
        font-weight: 600;
    }

    .fs-telemetry-divider {
        color: #475569;
    }

    .fs-telemetry-status {
        color: #10B981;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .fs-topbar-right {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .fs-topbar-alert-badge {
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .fs-topbar-device-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 5px 12px;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #34D399;
    }

    .fs-device-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #34D399;
        box-shadow: 0 0 8px #34D399;
    }

    /* ── Horizontal Navigation Bar (Top Segmented Bar) ──────── */
    div[data-testid="stRadio"]:has(div[role="radiogroup"][aria-label="Quick Nav"]) {
        margin-bottom: 20px;
    }

    div[role="radiogroup"][aria-label="Quick Nav"] {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        background: rgba(15, 23, 42, 0.6) !important;
        padding: 6px !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
    }

    div[role="radiogroup"][aria-label="Quick Nav"] > label {
        flex: 1 1 auto !important;
        min-width: 120px !important;
        margin: 0 !important;
        padding: 8px 16px !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 10px !important;
        color: var(--fs-text-muted) !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        justify-content: center !important;
        text-align: center !important;
    }

    /* Hide standard radio circle in horizontal nav */
    div[role="radiogroup"][aria-label="Quick Nav"] > label > div:first-child {
        display: none !important;
    }

    div[role="radiogroup"][aria-label="Quick Nav"] > label:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        color: var(--fs-text-heading) !important;
    }

    div[role="radiogroup"][aria-label="Quick Nav"] > label[data-checked="true"],
    div[role="radiogroup"][aria-label="Quick Nav"] > label:has(input:checked) {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.16) 0%, rgba(59, 130, 246, 0.12) 100%) !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
        color: #F8FAFC !important;
        box-shadow: 0 4px 15px -3px rgba(16, 185, 129, 0.25) !important;
    }

    /* ── Luxury Sidebar Container ───────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #070B14 0%, #0C1220 50%, #070B14 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
        box-shadow: 10px 0 35px -10px rgba(0, 0, 0, 0.6) !important;
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* ── Luxury Brand Card ──────────────────────────────────── */
    .fs-brand-card {
        position: relative;
        padding: 18px 20px;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(30, 41, 59, 0.6) 100%);
        border: 1px solid rgba(16, 185, 129, 0.22);
        border-radius: 16px;
        overflow: hidden;
        margin-bottom: 14px;
        box-shadow: 0 8px 20px -6px rgba(0, 0, 0, 0.4);
    }

    .fs-brand-glow {
        position: absolute;
        top: -40px;
        right: -40px;
        width: 100px;
        height: 100px;
        background: radial-gradient(circle, rgba(16, 185, 129, 0.2) 0%, transparent 70%);
        pointer-events: none;
    }

    .fs-brand-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 12px;
    }

    .fs-brand-icon-box {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%);
        border: 1px solid rgba(16, 185, 129, 0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.25);
    }

    .fs-brand-meta {
        display: flex;
        flex-direction: column;
    }

    .fs-brand-title {
        font-size: 1.3rem;
        font-weight: 900;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }

    .fs-brand-fresh {
        color: #10B981;
    }

    .fs-brand-sense {
        color: #38BDF8;
    }

    .fs-brand-sub {
        font-size: 0.68rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 2px;
    }

    .fs-brand-pill-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 5px 10px;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
        font-size: 0.72rem;
    }

    .fs-pulse-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #10B981;
        box-shadow: 0 0 8px #10B981;
        animation: fs-pulse-glow 1.8s infinite ease-in-out;
    }

    .fs-pill-text {
        color: #94A3B8;
        font-weight: 500;
        flex: 1;
    }

    .fs-pill-chip {
        color: #34D399;
        font-weight: 700;
        font-size: 0.68rem;
        text-transform: uppercase;
    }

    .fs-nav-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
        margin: 14px 0;
    }

    /* ── Sidebar Radio Navigation Transform ─────────────────── */
    .fs-menu-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0 4px 10px 4px;
        font-size: 0.68rem;
        font-weight: 700;
        color: #64748B;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .fs-menu-count {
        background: rgba(255, 255, 255, 0.06);
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.65rem;
        font-family: var(--fs-font-mono);
        color: #94A3B8;
    }

    /* Transform radio options inside sidebar into luxury menu cards */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
        position: relative !important;
        display: flex !important;
        align-items: center !important;
        padding: 10px 14px !important;
        background: rgba(15, 23, 42, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        color: #94A3B8 !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* Hide standard circular radio dot */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    /* Hover effect */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        border-color: rgba(16, 185, 129, 0.25) !important;
        color: #F8FAFC !important;
        transform: translateX(4px) !important;
    }

    /* Active selected menu item */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"],
    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.18) 0%, rgba(15, 23, 42, 0.8) 100%) !important;
        border: 1px solid rgba(16, 185, 129, 0.4) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 18px -4px rgba(16, 185, 129, 0.25) !important;
    }

    /* Neon left indicator bar for active item */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"]::before,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked)::before {
        content: '';
        position: absolute;
        left: 0;
        top: 20%;
        bottom: 20%;
        width: 3.5px;
        border-radius: 0 4px 4px 0;
        background: linear-gradient(180deg, #10B981, #06B6D4);
        box-shadow: 0 0 10px #10B981;
    }

    /* ── Freshness Health Dial Card ─────────────────────────── */
    .fs-telemetry-card {
        padding: 16px;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 16px;
        box-shadow: 0 8px 24px -8px rgba(0, 0, 0, 0.4);
    }

    .fs-telemetry-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }

    .fs-telemetry-title {
        font-size: 0.68rem;
        font-weight: 700;
        color: #64748B;
        letter-spacing: 0.08em;
    }

    .fs-telemetry-chip {
        padding: 3px 8px;
        border-radius: 8px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .fs-dial-container {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .fs-dial-graphic {
        position: relative;
        width: 78px;
        height: 78px;
        flex-shrink: 0;
    }

    .fs-dial-svg {
        width: 100%;
        height: 100%;
        transform: rotate(-90deg);
    }

    .fs-dial-bg {
        fill: none;
        stroke: rgba(255, 255, 255, 0.08);
        stroke-width: 8;
    }

    .fs-dial-fg {
        fill: none;
        stroke-width: 8;
        stroke-linecap: round;
        transition: stroke-dasharray 1s ease-in-out;
        filter: drop-shadow(0 0 6px currentColor);
    }

    .fs-dial-number-box {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .fs-dial-number {
        font-size: 1.15rem;
        font-weight: 800;
        font-family: var(--fs-font-mono);
        line-height: 1;
    }

    .fs-dial-label {
        font-size: 0.58rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        margin-top: 2px;
    }

    .fs-telemetry-stats {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .fs-stat-line {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.78rem;
    }

    .fs-stat-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 6px;
    }

    .fs-stat-name {
        color: #94A3B8;
        flex: 1;
    }

    .fs-stat-value {
        color: #F8FAFC;
        font-weight: 700;
        font-family: var(--fs-font-mono);
    }

    /* ── Expiry Radar Widget ────────────────────────────────── */
    .fs-radar-live {
        color: #EF4444;
        font-size: 0.65rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        animation: fs-pulse-text 1.5s infinite;
    }

    .fs-radar-list {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .fs-radar-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 7px 10px;
        background: rgba(15, 23, 42, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 9px;
    }

    .fs-radar-left {
        display: flex;
        align-items: center;
        gap: 8px;
        overflow: hidden;
    }

    .fs-radar-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .fs-radar-name {
        font-size: 0.78rem;
        font-weight: 600;
        color: #CBD5E1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .fs-radar-tag {
        font-size: 0.65rem;
        font-weight: 800;
        font-family: var(--fs-font-mono);
        padding: 2px 6px;
        border-radius: 6px;
        border: 1px solid;
    }

    /* ── Hardware / System Footer ───────────────────────────── */
    .fs-footer-card {
        padding: 12px 14px;
        background: rgba(15, 23, 42, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .fs-footer-hw-line {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.72rem;
    }

    .fs-hw-icon {
        font-size: 0.8rem;
    }

    .fs-hw-label {
        color: #64748B;
        font-weight: 500;
    }

    .fs-hw-val {
        color: #94A3B8;
        font-family: var(--fs-font-mono);
        font-weight: 600;
        margin-left: auto;
    }

    .fs-footer-credit {
        font-size: 0.65rem;
        color: #475569;
        text-align: center;
        margin-top: 6px;
        padding-top: 6px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        font-weight: 500;
    }

    /* ── Metric Cards ───────────────────────────────────────── */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(22, 32, 54, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 18px 22px !important;
        box-shadow: 0 10px 25px -10px rgba(0, 0, 0, 0.5) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(16, 185, 129, 0.3) !important;
        box-shadow: 0 15px 30px -10px rgba(16, 185, 129, 0.15) !important;
    }

    div[data-testid="stMetric"] label {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-weight: 800 !important;
        font-size: 2.1rem !important;
        font-family: var(--fs-font-mono) !important;
    }

    /* ── Content Cards ──────────────────────────────────────── */
    .fs-card {
        background: linear-gradient(145deg, rgba(22, 32, 54, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 16px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.4);
        transition: all 0.3s ease;
    }

    .fs-card:hover {
        border-color: rgba(16, 185, 129, 0.28);
        box-shadow: 0 15px 35px -10px rgba(16, 185, 129, 0.12);
    }

    /* ── Status Badges ──────────────────────────────────────── */
    .fs-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .fs-badge-fresh {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .fs-badge-warning {
        background: rgba(245, 158, 11, 0.15);
        color: #FCD34D;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .fs-badge-danger {
        background: rgba(239, 68, 68, 0.15);
        color: #FCA5A5;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .fs-badge-success {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    /* ── Alerts ─────────────────────────────────────────────── */
    .fs-alert {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px 22px;
        border-radius: 14px;
        margin-bottom: 16px;
    }

    .fs-alert-danger {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(185, 28, 28, 0.1) 100%);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-left: 5px solid #EF4444;
    }

    .fs-alert-warning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(180, 83, 9, 0.1) 100%);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-left: 5px solid #F59E0B;
    }

    .fs-alert-success {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-left: 5px solid #10B981;
    }

    .fs-alert-icon {
        font-size: 1.4rem;
    }

    .fs-alert-text {
        color: #F8FAFC;
        font-size: 0.95rem;
    }

    /* ── Progress Bars ──────────────────────────────────────── */
    .fs-progress-container {
        width: 100%;
        height: 6px;
        background: rgba(255, 255, 255, 0.07);
        border-radius: 9999px;
        overflow: hidden;
        margin-top: 10px;
    }

    .fs-progress-bar {
        height: 100%;
        border-radius: 9999px;
        transition: width 0.6s ease;
    }

    .fs-progress-fresh {
        background: linear-gradient(90deg, #10B981, #34D399);
    }

    .fs-progress-warning {
        background: linear-gradient(90deg, #F59E0B, #FCD34D);
    }

    .fs-progress-danger {
        background: linear-gradient(90deg, #EF4444, #FCA5A5);
    }

    /* ── Hero Banner ────────────────────────────────────────── */
    .fs-hero {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(56, 189, 248, 0.08) 50%, rgba(139, 92, 246, 0.06) 100%);
        border: 1px solid rgba(16, 185, 129, 0.22);
        border-radius: 20px;
        padding: 30px 36px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }

    .fs-hero-title {
        font-size: 1.85rem;
        font-weight: 800;
        color: #F8FAFC;
        margin: 0 0 8px 0;
        letter-spacing: -0.02em;
    }

    .fs-hero-subtitle {
        font-size: 0.98rem;
        color: #94A3B8;
        margin: 0;
        line-height: 1.6;
    }

    .fs-hero-accent {
        color: #10B981;
    }

    /* ── Button Overrides ───────────────────────────────────── */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-family: var(--fs-font-sans) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        background: rgba(22, 32, 54, 0.8) !important;
        color: #F8FAFC !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        border-color: rgba(16, 185, 129, 0.4) !important;
        box-shadow: 0 8px 20px -4px rgba(16, 185, 129, 0.2) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
        border: none !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 20px -4px rgba(16, 185, 129, 0.4) !important;
    }

    /* ── Recipe Card ────────────────────────────────────────── */
    .fs-recipe-card {
        background: linear-gradient(145deg, rgba(22, 32, 54, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(139, 92, 246, 0.25);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }

    .fs-recipe-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: #F8FAFC;
        margin: 0 0 6px 0;
    }

    .fs-recipe-meta {
        font-size: 0.82rem;
        color: #A78BFA;
        margin: 0 0 12px 0;
    }

    .fs-recipe-body {
        color: #CBD5E1;
        font-size: 0.92rem;
        line-height: 1.7;
    }

    /* ── Keyframe Animations ────────────────────────────────── */
    @keyframes fs-pulse-glow {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.3); opacity: 0.6; }
    }

    @keyframes fs-pulse-text {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* ── Empty State ────────────────────────────────────────── */
    .fs-empty {
        text-align: center;
        padding: 50px 20px;
        color: #64748B;
    }

    .fs-empty-icon {
        font-size: 3.5rem;
        margin-bottom: 12px;
    }

    .fs-empty-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #94A3B8;
        margin-bottom: 6px;
    }

    .fs-empty-text {
        font-size: 0.9rem;
        color: #64748B;
    }
    </style>
    """, unsafe_allow_html=True)
