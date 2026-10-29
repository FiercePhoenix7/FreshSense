"""
AI Recipe Suggestions — Uses local Llama 3.1 8B via Ollama to suggest recipes
based on items that are about to expire.

Falls back to built-in suggestions when the local AI model is not available.
"""
import streamlit as st
import json
import subprocess
from datetime import date
from utils.data_manager import DataManager
from utils.helpers import empty_state, render_html


# ── Built-in Recipe Suggestions (fallback when Ollama is unavailable) ─────
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
            "name": "Masala Chips Chaat",
            "time": "10 min",
            "difficulty": "Easy",
            "ingredients": ["Potato chips", "Onion", "Tomato", "Lemon", "Chaat masala"],
            "instructions": "1. Crush chips lightly. 2. Mix with chopped onion and tomato. 3. Add lemon juice and chaat masala. 4. Toss and serve immediately.",
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


def _check_ollama_available() -> bool:
    """Check if Ollama is running and has a model available."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _query_llama(prompt: str, model: str = "llama3.1:8b") -> str:
    """Query a local Ollama model and return the response text."""
    try:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 800,
            }
        })

        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/generate",
             "-d", payload],
            capture_output=True, text=True, timeout=60,
        )

        if result.returncode == 0:
            response = json.loads(result.stdout)
            return response.get("response", "")
    except Exception:
        pass
    return ""


def _build_prompt(items: list) -> str:
    """Build a recipe suggestion prompt from expiring items."""
    item_lines = []
    for item in items:
        name = item.get("name", "Unknown")
        category = item.get("category", "General")
        days = item.get("days_until_expiry", "?")
        item_lines.append(f"- {name} ({category}) — expires in {days} day(s)")

    items_text = "\n".join(item_lines)

    return f"""You are FreshSense AI, a smart fridge assistant. The user has the following food items that are about to expire or have already expired:

{items_text}

Suggest 2-3 creative, practical recipes that prioritize using these expiring items to minimize food waste. For each recipe provide:
1. Recipe name
2. Estimated cooking time
3. Difficulty (Easy/Medium/Hard)
4. Full ingredient list (include the expiring items + common pantry staples)
5. Brief step-by-step instructions

Focus on Indian and international cuisines. Be creative but practical. Format your response clearly with headers for each recipe."""


def _get_fallback_recipes(items: list) -> list:
    """Get relevant recipes from fallback library based on item categories."""
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

    if len(recipes) < 2 and "General" in FALLBACK_RECIPES:
        recipes.extend(FALLBACK_RECIPES["General"])

    return recipes


def render_recipes(dm: DataManager):
    """AI-powered recipe suggestions page."""

    hero_html = """
<div class="fs-hero" style="padding:24px 32px;">
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
        <span style="font-size:2rem;">🍳</span>
        <div class="fs-hero-title" style="font-size:1.5rem; margin:0;">AI Recipe Suggestions</div>
    </div>
    <div class="fs-hero-subtitle">
        Don't let food go to waste! FreshSense AI analyzes your expiring items
        and suggests delicious recipes powered by <strong style="color:#A78BFA;">Llama 3.1 8B</strong> running locally.
    </div>
</div>
"""
    render_html(hero_html)

    # Get items that need attention
    expiring = dm.get_expiring_items(days_threshold=3)
    expired = dm.get_expired_items()
    at_risk = expiring + expired

    if not at_risk:
        all_items = dm.get_all_items()
        if not all_items:
            render_html(
                empty_state("🧊", "No items in fridge", "Add items to your fridge to get recipe suggestions!")
            )
            return

        render_html("""
<div class="fs-alert fs-alert-success">
    <span class="fs-alert-icon">🎉</span>
    <span class="fs-alert-text"><strong>No urgently expiring items!</strong> All your food is fresh.
    You can still generate recipes from your current inventory.</span>
</div>
""")
        at_risk = all_items[:6]

    # ── Items Being Used ──────────────────────────────────────────────────
    st.markdown("### 🥘 Items to Use Up")
    cols = st.columns(min(len(at_risk), 4))
    for idx, item in enumerate(at_risk[:8]):
        col = cols[idx % len(cols)]
        with col:
            days = item.get("days_until_expiry")
            if days is not None and days < 0:
                urgency = "🔴"
                urgency_text = "Expired"
            elif days is not None and days <= 1:
                urgency = "🟠"
                urgency_text = f"{days}d left"
            elif days is not None and days <= 3:
                urgency = "🟡"
                urgency_text = f"{days}d left"
            else:
                urgency = "🟢"
                urgency_text = f"{days}d left" if days is not None else "N/A"

            card_item_html = f"""
<div class="fs-card" style="padding:14px; text-align:center;">
    <div style="font-size:0.9rem; font-weight:600; color:#F1F5F9; margin-bottom:4px;">
        {item.get('name', 'Unknown')[:22]}
    </div>
    <div style="font-size:0.8rem; color:#94A3B8;">{item.get('category', '')}</div>
    <div style="margin-top:6px;">{urgency} <span style="font-size:0.78rem; color:#94A3B8;">{urgency_text}</span></div>
</div>
"""
            render_html(card_item_html)

    st.markdown("")

    # ── AI Model Status ───────────────────────────────────────────────────
    ollama_available = _check_ollama_available()

    col_status, col_button = st.columns([3, 1])
    with col_status:
        if ollama_available:
            render_html("""
<div class="fs-alert fs-alert-success" style="padding:12px 18px;">
    <span>🤖</span>
    <span class="fs-alert-text"><strong>Llama 3.1 8B</strong> is available via Ollama — AI-powered recipes ready!</span>
</div>
""")
        else:
            render_html("""
<div class="fs-alert fs-alert-warning" style="padding:12px 18px;">
    <span>⚠️</span>
    <span class="fs-alert-text"><strong>Ollama not detected.</strong> Using curated recipe library instead.
    Install Ollama + Llama 3.1 for AI-generated recipes.</span>
</div>
""")

    with col_button:
        generate_clicked = st.button(
            "🧠 Generate Recipes" if ollama_available else "📖 Show Recipes",
            type="primary",
            use_container_width=True,
        )

    st.markdown("---")

    # ── Recipe Generation ─────────────────────────────────────────────────
    if generate_clicked or "last_recipes" in st.session_state:
        if generate_clicked:
            if ollama_available:
                with st.spinner("🧠 Llama 3.1 is cooking up recipe ideas..."):
                    prompt = _build_prompt(at_risk)
                    response = _query_llama(prompt)

                    if response:
                        st.session_state.last_recipes = {"type": "ai", "content": response}
                    else:
                        recipes = _get_fallback_recipes(at_risk)
                        st.session_state.last_recipes = {"type": "fallback", "content": recipes}
            else:
                recipes = _get_fallback_recipes(at_risk)
                st.session_state.last_recipes = {"type": "fallback", "content": recipes}

        # Display recipes
        if "last_recipes" in st.session_state:
            result = st.session_state.last_recipes

            if result["type"] == "ai":
                st.markdown("### 🤖 AI-Generated Recipes")
                with st.container():
                    st.info(f"Generated by Llama 3.1 8B · Based on {len(at_risk)} items")
                    st.markdown(result["content"])

            else:
                st.markdown("### 📖 Suggested Recipes")
                recipes = result["content"]

                for i, recipe in enumerate(recipes):
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
        - **Freezing**: Most items can be frozen to extend shelf life significantly.
        - **Meal Planning**: Plan meals around items that are expiring soonest.
        - **Portion Control**: Buy only what you need for the week.
        - **Proper Storage**: Keep items at their recommended temperatures.
        - **Composting**: If items do expire, consider composting instead of discarding.
        """)

    with st.expander("🔧 Setting Up Local AI (Llama 3.1)"):
        st.markdown("""
        To enable AI-powered recipe suggestions:

        1. **Install Ollama**: Visit [ollama.ai](https://ollama.ai) and download for your OS.
        2. **Pull the model**: Run `ollama pull llama3.1:8b` in your terminal.
        3. **Start Ollama**: It runs as a background service automatically.
        4. **Refresh this page**: FreshSense will auto-detect the model!

        The model runs 100% locally — no internet, no API keys, complete privacy.
        """)
