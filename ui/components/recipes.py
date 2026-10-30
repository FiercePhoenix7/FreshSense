"""
AI Generated Recipes — Streams 3 custom recipes prioritizing items about to expire
in the fridge inventory using local AI.
"""
import streamlit as st
import ollama
from datetime import date
from utils.data_manager import DataManager
from utils.helpers import empty_state, render_html


# ── Curated Recipe Suggestions (Fallback if AI model is unreachable) ─────────
FALLBACK_RECIPES = {
    "Dairy": [
        {
            "name": "Creamy Paneer Butter Masala",
            "time": "35 min",
            "difficulty": "Medium",
            "ingredients": ["Paneer", "Butter", "Cream", "Tomato puree", "Spices"],
            "instructions": "1. Blend tomatoes to a puree. 2. Heat butter, add spices, pour in tomato puree. 3. Simmer, add cream and paneer cubes. 4. Cook for 10 minutes. Serve with naan or rice.",
        },
        {
            "name": "Quick Cheese Omelette",
            "time": "10 min",
            "difficulty": "Easy",
            "ingredients": ["Eggs", "Cheese", "Butter", "Salt", "Pepper"],
            "instructions": "1. Whisk eggs with salt and pepper. 2. Melt butter in a pan. 3. Pour eggs, add cheese when half-set. 4. Fold and serve hot.",
        },
        {
            "name": "Homemade Yogurt Smoothie",
            "time": "5 min",
            "difficulty": "Easy",
            "ingredients": ["Yogurt/Curd", "Banana", "Honey", "Ice"],
            "instructions": "1. Blend all ingredients until smooth. 2. Pour into a glass. 3. Add toppings if desired.",
        },
    ],
    "Bakery": [
        {
            "name": "French Toast Delight",
            "time": "15 min",
            "difficulty": "Easy",
            "ingredients": ["Bread", "Eggs", "Milk", "Cinnamon", "Butter"],
            "instructions": "1. Whisk eggs, milk, and cinnamon. 2. Dip bread slices. 3. Fry in butter until golden. 4. Serve with honey or syrup.",
        },
        {
            "name": "Bread Upma",
            "time": "15 min",
            "difficulty": "Easy",
            "ingredients": ["Bread", "Onion", "Tomato", "Green chili", "Mustard seeds"],
            "instructions": "1. Tear bread into pieces. 2. Temper mustard seeds, add onion and tomato. 3. Add bread pieces, toss well. 4. Season with lemon juice and coriander.",
        },
    ],
    "Produce": [
        {
            "name": "Quick Stir-Fry Vegetables",
            "time": "20 min",
            "difficulty": "Easy",
            "ingredients": ["Mixed vegetables", "Soy sauce", "Garlic", "Ginger", "Oil"],
            "instructions": "1. Heat oil, sauté garlic and ginger. 2. Add vegetables, stir-fry on high heat. 3. Add soy sauce. 4. Serve hot with rice or noodles.",
        },
        {
            "name": "Green Smoothie Bowl",
            "time": "10 min",
            "difficulty": "Easy",
            "ingredients": ["Spinach", "Banana", "Yogurt", "Honey", "Granola"],
            "instructions": "1. Blend spinach, banana, and yogurt. 2. Pour into a bowl. 3. Top with granola and honey.",
        },
    ],
    "Snacks": [
        {
            "name": "Masala Crisps Chaat",
            "time": "10 min",
            "difficulty": "Easy",
            "ingredients": ["Potato crisps", "Onion", "Tomato", "Lemon", "Chaat masala"],
            "instructions": "1. Crush crisps lightly. 2. Mix with chopped onion and tomato. 3. Add lemon juice and chaat masala. 4. Toss and serve immediately.",
        },
    ],
    "Meat": [
        {
            "name": "Simple Chicken Curry",
            "time": "40 min",
            "difficulty": "Medium",
            "ingredients": ["Chicken", "Onion", "Tomato", "Ginger-garlic paste", "Spices"],
            "instructions": "1. Sauté onions, add ginger-garlic paste. 2. Add tomatoes and spices. 3. Add chicken, cook covered for 25 min. 4. Garnish with coriander.",
        },
    ],
    "General": [
        {
            "name": "Leftover Surprise Fried Rice",
            "time": "15 min",
            "difficulty": "Easy",
            "ingredients": ["Cooked rice", "Any vegetables", "Soy sauce", "Eggs", "Oil"],
            "instructions": "1. Heat oil, scramble eggs. 2. Add vegetables, stir-fry. 3. Add rice and soy sauce. 4. Toss well on high heat. Serve hot!",
        },
    ],
}


def _build_ai_recipe_prompt(items: list) -> str:
    """
    Builds the AI prompt providing inventory items along with their expiry dates
    and requesting 3 recipes prioritizing the items that are about to expire.
    """
    inventory_lines = []
    about_to_expire = []

    sorted_items = sorted(
        items,
        key=lambda x: x.get("days_until_expiry") if x.get("days_until_expiry") is not None else 9999
    )

    for item in sorted_items:
        name = item.get("name", "Unknown Item")
        cat = item.get("category", "General")
        exp = item.get("expiry_date", "No date specified")
        days_left = item.get("days_until_expiry")

        if days_left is not None:
            if days_left < 0:
                desc = f"EXPIRED {abs(days_left)} day(s) ago (Expiry: {exp})"
                about_to_expire.append(f"{name} ({desc})")
            elif days_left == 0:
                desc = f"Expires TODAY (Expiry: {exp}) - URGENT"
                about_to_expire.append(f"{name} ({desc})")
            elif days_left <= 3:
                desc = f"Expires in {days_left} day(s) (Expiry: {exp}) - HIGH PRIORITY"
                about_to_expire.append(f"{name} ({desc})")
            else:
                desc = f"Expires in {days_left} day(s) (Expiry: {exp})"
        else:
            desc = f"Expiry date: {exp}"

        inventory_lines.append(f"- {name} [{cat}]: {desc}")

    inv_text = "\n".join(inventory_lines)
    expiring_text = (
        "\n".join([f"• {x}" for x in about_to_expire])
        if about_to_expire
        else "All items are currently fresh. Prioritize items with the nearest expiry dates."
    )

    return f"""You are a professional chef and smart food waste reduction AI assistant.

Here is the current inventory in the fridge with their expiry dates:
{inv_text}

Items that are about to expire (highest priority to use):
{expiring_text}

TASK:
Generate exactly 3 delicious, realistic, and practical recipes that prioritize using the items which are about to expire to avoid food waste.
Assume basic pantry essentials (cooking oil, salt, black pepper, water, basic spices) are available.

For each recipe, use this clean markdown format:
### 1. [Recipe Name] (and 2, 3)
- **Cooking Time:** [e.g. 20 mins]
- **Difficulty:** Easy / Medium / Hard
- **Expiring Ingredients Used:** [List items utilized from fridge]
- **Pantry Staples Needed:** [List any basic staples]
- **Instructions:**
  1. [Step 1]
  2. [Step 2]
  3. [Step 3]
  4. [Step 4]

Make the recipes appetizing, practical, and focused on utilizing the expiring items."""


def _stream_ai_recipes(items: list, model: str = "llama3.1"):
    """
    Generator that streams recipe chunks directly from the local AI model.
    Yields string tokens in real time.
    """
    prompt = _build_ai_recipe_prompt(items)
    stream = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={
            "temperature": 0.7,
            "top_p": 0.9,
        },
    )
    for chunk in stream:
        if hasattr(chunk, "message") and hasattr(chunk.message, "content"):
            yield chunk.message.content
        elif isinstance(chunk, dict) and "message" in chunk:
            yield chunk["message"]["content"]


def _get_fallback_recipes(items: list) -> list:
    """Curated fallback recipes matching the categories present in fridge."""
    categories = set()
    for item in items:
        cat = item.get("category", "General")
        if "Dairy" in cat:
            categories.add("Dairy")
        elif "Bak" in cat:
            categories.add("Bakery")
        elif "Prod" in cat or "Veg" in cat or "Spin" in cat:
            categories.add("Produce")
        elif "Snack" in cat or "Potato" in cat or "crisp" in cat.lower():
            categories.add("Snacks")
        elif "Meat" in cat or "Chicken" in cat:
            categories.add("Meat")
        else:
            categories.add("General")

    recipes = []
    for cat in categories:
        if cat in FALLBACK_RECIPES:
            recipes.extend(FALLBACK_RECIPES[cat])

    if len(recipes) < 3 and "General" in FALLBACK_RECIPES:
        recipes.extend(FALLBACK_RECIPES["General"])

    return recipes[:3]


def render_recipes(dm: DataManager):
    """AI Generated Recipes page with live streaming generation."""

    hero_html = """
<div class="fs-hero" style="padding:24px 32px;">
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
        <span style="font-size:2rem;">🍳</span>
        <div class="fs-hero-title" style="font-size:1.5rem; margin:0;">AI Generated Recipes</div>
    </div>
    <div class="fs-hero-subtitle">
        Intelligent culinary recommendations generated directly from your inventory, prioritized for items that are about to expire to eliminate food waste.
    </div>
</div>
"""
    render_html(hero_html)

    all_items = dm.get_all_items()
    if not all_items:
        render_html(
            empty_state("🧊", "No items in fridge", "Add items to your fridge to get AI generated recipes!")
        )
        return

    # Check for expiring items
    expiring = dm.get_expiring_items(days_threshold=3)
    expired = dm.get_expired_items()
    at_risk = expiring + expired

    # ── Items About to Expire Preview ─────────────────────────────────────
    st.markdown("### 🥘 Items About to Expire")

    preview_items = at_risk if at_risk else all_items[:4]

    if not at_risk:
        render_html("""
<div class="fs-alert fs-alert-success" style="padding:10px 16px; margin-bottom:12px;">
    <span class="fs-alert-icon">🎉</span>
    <span class="fs-alert-text"><strong>All items are currently fresh!</strong> Recipes will utilize ingredients with the nearest expiry dates.</span>
</div>
""")

    cols = st.columns(min(len(preview_items), 4))
    for idx, item in enumerate(preview_items[:8]):
        col = cols[idx % len(cols)]
        with col:
            days = item.get("days_until_expiry")
            exp_date = item.get("expiry_date", "N/A")
            if days is not None and days < 0:
                urgency = "🔴"
                urgency_text = f"Expired ({exp_date})"
            elif days is not None and days <= 1:
                urgency = "🟠"
                urgency_text = f"{days}d left ({exp_date})"
            elif days is not None and days <= 3:
                urgency = "🟡"
                urgency_text = f"{days}d left ({exp_date})"
            else:
                urgency = "🟢"
                urgency_text = f"{days}d left ({exp_date})" if days is not None else exp_date

            card_item_html = f"""
<div class="fs-card" style="padding:14px; text-align:center;">
    <div style="font-size:0.9rem; font-weight:600; color:#F1F5F9; margin-bottom:4px;">
        {item.get('name', 'Unknown')[:22]}
    </div>
    <div style="font-size:0.8rem; color:#94A3B8;">{item.get('category', 'General')}</div>
    <div style="margin-top:6px;">{urgency} <span style="font-size:0.75rem; color:#CBD5E1; font-weight:600;">{urgency_text}</span></div>
</div>
"""
            render_html(card_item_html)

    st.markdown("")

    # ── Action Button ─────────────────────────────────────────────────────
    col_btn, col_info = st.columns([1.5, 3])
    with col_btn:
        generate_clicked = st.button(
            "✨ Generate AI Recipes",
            type="primary",
            use_container_width=True,
        )
    with col_info:
        st.caption("AI streams 3 recipes in real-time, designed specifically for your expiring ingredients.")

    st.markdown("---")

    # ── Real-Time Streaming Recipe Generation & Display ───────────────────
    if generate_clicked:
        st.markdown("### ✨ AI Generated Recipes")
        try:
            # st.write_stream renders tokens live word-by-word with typewriter animation
            recipe_stream = _stream_ai_recipes(all_items, model="llama3.1")
            full_text = st.write_stream(recipe_stream)

            if full_text and full_text.strip():
                st.session_state.ai_recipes_cache = {
                    "is_ai": True,
                    "content": full_text,
                }
            else:
                fallback = _get_fallback_recipes(all_items)
                st.session_state.ai_recipes_cache = {
                    "is_ai": False,
                    "content": fallback,
                }
                st.rerun()
        except Exception as e:
            print(f"[Streaming Error - Triggering fallback]: {e}")
            fallback = _get_fallback_recipes(all_items)
            st.session_state.ai_recipes_cache = {
                "is_ai": False,
                "content": fallback,
            }
            st.rerun()

    elif "ai_recipes_cache" in st.session_state:
        st.markdown("### ✨ AI Generated Recipes")
        cached = st.session_state.ai_recipes_cache

        if cached.get("is_ai"):
            st.markdown(cached["content"])
        else:
            recipes = cached.get("content", [])
            for recipe in recipes:
                diff_colors = {"Easy": "#34D399", "Medium": "#FCD34D", "Hard": "#FCA5A5"}
                diff_color = diff_colors.get(recipe.get("difficulty", "Easy"), "#94A3B8")
                ingredients_html = " · ".join(recipe.get("ingredients", []))

                recipe_card_html = f"""
<div class="fs-recipe-card">
    <div class="fs-recipe-title">🍽️ {recipe['name']}</div>
    <div class="fs-recipe-meta">
        ⏱️ {recipe.get('time', 'N/A')} &nbsp;·&nbsp;
        <span style="color:{diff_color};">●</span> {recipe.get('difficulty', 'Easy')}
    </div>
    <div style="color:#94A3B8; font-size:0.82rem; margin-bottom:10px;">
        <strong>Ingredients:</strong> {ingredients_html}
    </div>
    <div class="fs-recipe-body">
        {recipe.get('instructions', '')}
    </div>
</div>
"""
                render_html(recipe_card_html)

    # ── Tips Section ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("💡 Food Waste Reduction Tips"):
        st.markdown("""
        - **FIFO Method**: First In, First Out — use older items first.
        - **Batch Cooking**: Use expiring vegetables or dairy into broths, bakes, or sauces.
        - **Freezing**: Most items can be frozen before expiry to extend shelf life by months.
        - **Meal Planning**: Plan upcoming meals around items that are expiring soonest.
        - **Proper Storage**: Keep temperature at 3-4°C to optimize freshness.
        """)
