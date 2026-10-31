"""
Reusable HTML rendering helpers for FreshSense components.
All HTML is safely compacted to prevent Markdown from ever treating
indented HTML or blank lines as code blocks.
"""
import streamlit as st


def render_html(html_str: str):
    """
    Safely render HTML without markdown treating indentation or blank lines as code blocks.
    Strips all leading/trailing whitespace per line and joins contiguous HTML.
    """
    if not html_str:
        return
    clean_lines = [line.strip() for line in html_str.strip().splitlines() if line.strip()]
    compact_html = "".join(clean_lines)
    st.markdown(compact_html, unsafe_allow_html=True)


def status_badge(status: str) -> str:
    """Returns an HTML badge span for the given freshness status."""
    if status == "Fresh":
        return '<span class="fs-badge fs-badge-fresh">✓ Fresh</span>'
    elif status == "Expiring Soon":
        return '<span class="fs-badge fs-badge-warning">⚠ Expiring Soon</span>'
    elif status == "Expired":
        return '<span class="fs-badge fs-badge-danger">✗ Expired</span>'
    return '<span class="fs-badge" style="color:#94A3B8;">? Unknown</span>'


def freshness_bar(days_left: int, max_days: int = 30) -> str:
    """Returns an HTML progress bar representing remaining shelf life."""
    if days_left is None:
        return ""
    pct = max(0, min(100, (days_left / max_days) * 100))
    if days_left < 0:
        bar_class = "fs-progress-danger"
        pct = 100
    elif days_left <= 3:
        bar_class = "fs-progress-warning"
    else:
        bar_class = "fs-progress-fresh"

    return f'<div class="fs-progress-container"><div class="fs-progress-bar {bar_class}" style="width: {pct}%;"></div></div>'


def alert_banner(icon: str, message: str, level: str = "warning") -> str:
    """Returns an HTML alert banner."""
    return f'<div class="fs-alert fs-alert-{level}"><span class="fs-alert-icon">{icon}</span><span class="fs-alert-text">{message}</span></div>'


def item_card_html(item: dict) -> str:
    """Returns styled HTML card for a single inventory item."""
    name = item.get("name", "Unknown")
    category = item.get("category", "General")
    expiry = item.get("expiry_date", "N/A")
    days = item.get("days_until_expiry")
    status = item.get("status", "Unknown")
    scanned_at = item.get("scanned_at", "")

    badge = status_badge(status)

    if days is not None:
        if days < 0:
            days_text = f'<span style="color:#FCA5A5; font-weight:700;">Expired {abs(days)}d ago</span>'
        elif days == 0:
            days_text = '<span style="color:#FCD34D; font-weight:700;">Expires TODAY</span>'
        elif days <= 3:
            days_text = f'<span style="color:#FCD34D; font-weight:700;">{days}d left</span>'
        else:
            days_text = f'<span style="color:#34D399; font-weight:600;">{days}d left</span>'
    else:
        days_text = '<span style="color:#64748B;">N/A</span>'

    bar = freshness_bar(days, max_days=30)

    cat_emojis = {
        "Dairy": "🥚", "Dairy & Eggs": "🥚", "Bakery": "🍞",
        "Beverages": "🥤", "Snacks": "🍿", "Spreads": "🫙",
        "Produce": "🥬", "Fruit": "🍌", "Vegetable": "🥦", "Vegetables": "🥦",
        "Meat": "🥩", "Seafood": "🐟",
        "Frozen": "🧊", "Packaged Goods": "📦", "General": "🛒",
        "Potato crisps": "🥔", "Protein": "💪",
    }
    emoji = cat_emojis.get(category, "🛒")
    meta_parts = [category]
    if scanned_at:
        meta_parts.append(f"Added {scanned_at}")
    meta_str = " · ".join(meta_parts)

    return f"""
<div class="fs-card" style="padding: 18px 22px;">
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div style="flex:1;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                <span style="font-size:1.4rem;">{emoji}</span>
                <span class="fs-item-name">{name}</span>
                {badge}
            </div>
            <div class="fs-item-meta" style="margin-bottom:4px;">
                {meta_str}
            </div>
        </div>
        <div style="text-align:right; min-width:140px;">
            <div class="fs-item-expiry" style="color:#94A3B8; margin-bottom:2px;">
                📅 {expiry}
            </div>
            <div>{days_text}</div>
        </div>
    </div>
    {bar}
</div>
"""


def empty_state(icon: str, title: str, text: str) -> str:
    """Returns a centered empty-state placeholder."""
    return f"""
<div class="fs-empty">
    <div class="fs-empty-icon">{icon}</div>
    <div class="fs-empty-title">{title}</div>
    <div class="fs-empty-text">{text}</div>
</div>
"""
