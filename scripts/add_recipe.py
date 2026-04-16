#!/usr/bin/env python3
"""
Recipe ingestion script for the Cookbook.

Usage:
    python scripts/add_recipe.py --url "https://example.com/recipe"
    python scripts/add_recipe.py --file recipe.html
    python scripts/add_recipe.py --text recipe.txt
    python scripts/add_recipe.py              # interactive prompt
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup

RECIPES_DIR = Path(__file__).resolve().parent.parent / "_recipes"

# ── Auto-tagging dictionaries ──────────────────────────────────────────────

DISH_TYPE_KEYWORDS = {
    "Cocktail": [
        "vodka", "rum", "gin", "tequila", "whiskey", "bourbon", "brandy",
        "liqueur", "bitters", "vermouth", "triple sec", "kahlua", "amaretto",
        "cocktail", "martini", "margarita", "daiquiri", "mojito", "negroni",
        "old fashioned", "manhattan", "cosmopolitan", "simple syrup",
        "angostura", "campari", "aperol", "prosecco", "champagne",
    ],
    "Dessert": [
        "sugar", "vanilla extract", "chocolate", "cocoa", "cake", "cookie",
        "brownie", "pie", "tart", "custard", "pudding", "meringue",
        "frosting", "icing", "powdered sugar", "confectioners", "caramel",
        "mousse", "cheesecake", "soufflé", "ganache", "pastry cream",
        "whipped cream", "baking powder", "baking soda",
    ],
    "Bread": [
        "yeast", "bread flour", "dough", "knead", "proof", "loaf",
        "sourdough", "focaccia", "baguette", "rolls", "brioche",
    ],
    "Soup": [
        "broth", "stock", "soup", "chowder", "bisque", "stew",
        "simmer", "ladle", "puree",
    ],
    "Salad": [
        "lettuce", "arugula", "mixed greens", "vinaigrette", "salad",
        "romaine", "kale salad", "coleslaw", "dressing",
    ],
    "Breakfast": [
        "pancake", "waffle", "omelette", "omelet", "scrambled eggs",
        "french toast", "granola", "oatmeal", "breakfast", "brunch",
        "hash brown", "benedict", "frittata",
    ],
    "Appetizer": [
        "appetizer", "hors d'oeuvre", "hors d'oeuvres", "crostini",
        "bruschetta", "dip", "hummus", "guacamole", "salsa", "canapé",
        "tartare", "carpaccio", "spring roll", "dumpling", "skewer",
        "stuffed mushroom", "deviled egg", "ceviche",
    ],
    "Side": [
        "side dish", "mashed potatoes", "roasted vegetables", "coleslaw",
        "mac and cheese", "cornbread", "baked beans", "rice pilaf",
        "gratin", "au gratin",
    ],
    "Sauce": [
        "sauce", "gravy", "pesto", "aioli", "chimichurri", "hollandaise",
        "béchamel", "bechamel", "marinara", "bolognese", "ragu",
    ],
    "Entrée": [
        "roast", "bake", "grill", "sear", "braise", "sauté",
        "steak", "chicken breast", "pork chop", "salmon fillet",
        "pasta", "risotto", "lasagna", "casserole", "stir fry",
        "curry", "tacos", "burrito", "burger", "meatloaf",
    ],
}

CUISINE_KEYWORDS = {
    "Italian": [
        "parmesan", "parmigiano", "mozzarella", "ricotta", "basil",
        "oregano", "marinara", "pasta", "risotto", "prosciutto",
        "pancetta", "focaccia", "ciabatta", "pesto", "balsamic",
        "bruschetta", "lasagna", "gnocchi", "polenta", "tiramisu",
    ],
    "Mexican": [
        "tortilla", "jalapeño", "chipotle", "cumin", "cilantro",
        "avocado", "salsa", "taco", "burrito", "enchilada",
        "queso", "chorizo", "mole", "ancho", "guajillo",
        "pinto beans", "black beans", "lime", "cotija",
    ],
    "Chinese": [
        "soy sauce", "sesame oil", "ginger", "hoisin", "oyster sauce",
        "five spice", "szechuan", "sichuan", "wok", "bok choy",
        "tofu", "rice vinegar", "star anise", "dim sum", "dumpling",
        "chow mein", "lo mein", "kung pao", "mapo",
    ],
    "Japanese": [
        "miso", "dashi", "mirin", "sake", "nori", "wasabi",
        "sushi", "sashimi", "ramen", "udon", "soba", "tempura",
        "teriyaki", "ponzu", "edamame", "panko", "kombu",
        "furikake", "katsu", "tonkatsu",
    ],
    "Indian": [
        "turmeric", "garam masala", "curry powder", "cardamom",
        "coriander", "cumin", "naan", "basmati", "ghee",
        "tandoori", "masala", "paneer", "chutney", "samosa",
        "biryani", "tikka", "vindaloo", "dal", "lentil",
        "fenugreek", "tamarind",
    ],
    "Thai": [
        "fish sauce", "lemongrass", "thai basil", "galangal",
        "coconut milk", "red curry paste", "green curry", "pad thai",
        "sriracha", "thai chili", "kaffir lime", "tom yum",
        "tom kha", "satay",
    ],
    "French": [
        "butter", "shallot", "thyme", "tarragon", "dijon",
        "crème fraîche", "beurre", "roux", "béchamel", "gruyère",
        "croissant", "soufflé", "confit", "béarnaise", "bouillabaisse",
        "coq au vin", "ratatouille", "quiche", "crêpe",
    ],
    "Mediterranean": [
        "olive oil", "feta", "hummus", "tahini", "za'atar",
        "sumac", "pita", "couscous", "bulgur", "harissa",
        "tzatziki", "grape leaves", "pomegranate",
    ],
    "Korean": [
        "gochujang", "gochugaru", "kimchi", "sesame", "doenjang",
        "bulgogi", "bibimbap", "japchae", "ssamjang", "tteok",
        "korean chili", "perilla",
    ],
    "American": [
        "bbq", "barbecue", "burger", "hot dog", "cornbread",
        "biscuit", "fried chicken", "mac and cheese", "coleslaw",
        "pulled pork", "brisket", "buffalo wings",
    ],
    "Spanish": [
        "saffron", "paprika", "chorizo", "manchego", "paella",
        "patatas bravas", "gazpacho", "tapas", "pimiento",
        "sherry vinegar",
    ],
    "Vietnamese": [
        "fish sauce", "pho", "banh mi", "rice noodle", "nuoc cham",
        "lemongrass", "spring roll", "vermicelli", "vietnamese",
    ],
    "Greek": [
        "feta", "olives", "oregano", "lemon", "yogurt",
        "tzatziki", "gyro", "souvlaki", "spanakopita", "phyllo",
        "moussaka",
    ],
}

MAIN_INGREDIENT_KEYWORDS = {
    "Chicken": ["chicken", "poultry"],
    "Beef": ["beef", "steak", "ground beef", "sirloin", "ribeye", "brisket"],
    "Pork": ["pork", "bacon", "ham", "prosciutto", "pancetta", "pork chop", "pork loin"],
    "Lamb": ["lamb", "lamb chop", "leg of lamb"],
    "Fish": ["salmon", "tuna", "cod", "halibut", "tilapia", "trout", "mahi", "snapper", "swordfish", "bass"],
    "Shellfish": ["shrimp", "lobster", "crab", "scallop", "mussel", "clam", "oyster", "prawn"],
    "Pasta": ["pasta", "spaghetti", "penne", "fettuccine", "linguine", "rigatoni", "macaroni", "noodle"],
    "Rice": ["rice", "risotto", "basmati", "jasmine rice"],
    "Eggs": ["eggs", "egg"],
    "Tofu": ["tofu", "tempeh"],
    "Beans": ["beans", "lentils", "chickpeas", "black beans", "kidney beans"],
    "Vegetables": ["broccoli", "cauliflower", "zucchini", "squash", "eggplant", "mushroom", "pepper", "carrot", "potato", "sweet potato"],
}

DIETARY_KEYWORDS = {
    "Vegetarian": {
        "exclude": ["chicken", "beef", "pork", "lamb", "fish", "salmon", "tuna",
                     "shrimp", "lobster", "crab", "bacon", "prosciutto", "pancetta",
                     "anchovy", "anchovies", "gelatin", "lard"],
    },
    "Vegan": {
        "exclude": ["chicken", "beef", "pork", "lamb", "fish", "salmon", "tuna",
                     "shrimp", "lobster", "crab", "bacon", "prosciutto", "pancetta",
                     "egg", "eggs", "milk", "cream", "butter", "cheese", "yogurt",
                     "honey", "gelatin", "whey", "casein", "lard"],
    },
    "Gluten-Free": {
        "exclude": ["flour", "bread", "pasta", "spaghetti", "penne", "noodle",
                     "breadcrumb", "panko", "crouton", "tortilla", "pita",
                     "couscous", "barley", "wheat", "semolina", "soy sauce"],
    },
}


# ── Classifier ─────────────────────────────────────────────────────────────

def classify_recipe(title: str, ingredients: list[str], instructions_text: str) -> dict:
    """Classify a recipe by dish type, cuisine, main ingredient, and dietary tags."""
    combined = " ".join([title] + ingredients + [instructions_text]).lower()

    # Score each category using word-boundary matching to avoid false positives
    # (e.g. "gin" matching "virgin")
    def score(keywords_dict):
        scores = {}
        for category, keywords in keywords_dict.items():
            count = 0
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, combined):
                    count += 1
            scores[category] = count
        return scores

    # Dish type — pick highest scoring, default to Entrée
    dish_scores = score(DISH_TYPE_KEYWORDS)
    dish_type = max(dish_scores, key=dish_scores.get) if max(dish_scores.values()) > 0 else "Entrée"

    # Cuisine — pick highest scoring
    cuisine_scores = score(CUISINE_KEYWORDS)
    cuisine = max(cuisine_scores, key=cuisine_scores.get) if max(cuisine_scores.values()) > 0 else None

    # Main ingredient — pick highest scoring
    ingredient_scores = score(MAIN_INGREDIENT_KEYWORDS)
    main_ingredient = max(ingredient_scores, key=ingredient_scores.get) if max(ingredient_scores.values()) > 0 else None

    # Dietary tags
    ingredients_lower = " ".join(ingredients).lower()
    dietary_tags = []
    for diet, rules in DIETARY_KEYWORDS.items():
        excluded = any(
            re.search(r'\b' + re.escape(ex) + r'\b', ingredients_lower)
            for ex in rules["exclude"]
        )
        if not excluded:
            dietary_tags.append(diet)

    # Build tags list
    tags = []
    if dish_type:
        tags.append(dish_type)
    if cuisine:
        tags.append(cuisine)
    if main_ingredient:
        tags.append(main_ingredient)
    tags.extend(dietary_tags)

    return {
        "dish_type": dish_type,
        "cuisine": cuisine,
        "main_ingredient": main_ingredient,
        "dietary_tags": dietary_tags,
        "tags": tags,
    }


# ── Parsers ────────────────────────────────────────────────────────────────

def parse_schema_org(soup: BeautifulSoup) -> dict | None:
    """Extract recipe data from Schema.org JSON-LD."""
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        # Handle @graph arrays
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "Recipe":
                    data = item
                    break
            else:
                continue
        if isinstance(data, dict) and data.get("@graph"):
            for item in data["@graph"]:
                if isinstance(item, dict) and item.get("@type") == "Recipe":
                    data = item
                    break
        # Handle arrays in @type
        if isinstance(data, dict):
            dtype = data.get("@type", "")
            if isinstance(dtype, list):
                if "Recipe" not in dtype:
                    continue
            elif dtype != "Recipe":
                continue
        else:
            continue

        # Extract fields
        recipe = {"title": data.get("name", "Untitled")}

        # Ingredients
        ingredients = data.get("recipeIngredient", [])
        if isinstance(ingredients, str):
            ingredients = [ingredients]
        recipe["ingredients"] = [_clean_html(i) for i in ingredients]

        # Instructions
        instructions_raw = data.get("recipeInstructions", [])
        recipe["instructions"] = _parse_instructions(instructions_raw)

        # Times
        recipe["prep_time"] = _format_duration(data.get("prepTime"))
        recipe["cook_time"] = _format_duration(data.get("cookTime"))
        recipe["total_time"] = _format_duration(data.get("totalTime"))

        # Servings
        recipe["servings"] = data.get("recipeYield")
        if isinstance(recipe["servings"], list):
            recipe["servings"] = recipe["servings"][0] if recipe["servings"] else None

        recipe["description"] = _clean_html(data.get("description", ""))

        return recipe
    return None


def _parse_instructions(raw) -> list[str]:
    """Parse instruction data from various Schema.org formats."""
    if isinstance(raw, str):
        return [s.strip() for s in re.split(r'\.\s+', _clean_html(raw)) if s.strip()]
    steps = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                steps.append(_clean_html(item))
            elif isinstance(item, dict):
                if item.get("@type") == "HowToStep":
                    steps.append(_clean_html(item.get("text", "")))
                elif item.get("@type") == "HowToSection":
                    for sub in item.get("itemListElement", []):
                        if isinstance(sub, dict):
                            steps.append(_clean_html(sub.get("text", "")))
                        elif isinstance(sub, str):
                            steps.append(_clean_html(sub))
    return [s for s in steps if s]


def _format_duration(iso_dur: str | None) -> str | None:
    """Convert ISO 8601 duration to human-readable string."""
    if not iso_dur:
        return None
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_dur, re.IGNORECASE)
    if not match:
        return iso_dur
    hours, minutes, seconds = match.groups()
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not hours and not minutes:
        parts.append(f"{seconds}s")
    return " ".join(parts) if parts else None


def _clean_html(text: str) -> str:
    """Strip HTML tags from a string."""
    if not text:
        return ""
    return BeautifulSoup(str(text), "html.parser").get_text().strip()


def parse_html_fallback(soup: BeautifulSoup) -> dict | None:
    """Fallback: try to extract recipe from HTML structure."""
    title = None
    title_tag = soup.find("h1")
    if title_tag:
        title = title_tag.get_text().strip()

    # Look for ingredient lists
    ingredients = []
    for ul in soup.find_all("ul"):
        parent = ul.parent
        if parent and parent.name in ("div", "section"):
            heading = parent.find(re.compile(r"h[2-4]"))
            if heading and "ingredient" in heading.get_text().lower():
                ingredients = [li.get_text().strip() for li in ul.find_all("li")]
                break

    # Look for instruction lists
    instructions = []
    for ol in soup.find_all("ol"):
        parent = ol.parent
        if parent and parent.name in ("div", "section"):
            heading = parent.find(re.compile(r"h[2-4]"))
            if heading and any(w in heading.get_text().lower() for w in ("instruction", "direction", "method", "step")):
                instructions = [li.get_text().strip() for li in ol.find_all("li")]
                break

    if not title and not ingredients:
        return None

    return {
        "title": title or "Untitled",
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time": None,
        "cook_time": None,
        "total_time": None,
        "servings": None,
        "description": "",
    }


def parse_raw_text(text: str) -> dict:
    """Parse a recipe from plain text."""
    lines = [line.strip() for line in text.strip().splitlines()]

    title = lines[0] if lines else "Untitled"
    ingredients = []
    instructions = []
    description = ""

    section = None
    for line in lines[1:]:
        lower = line.lower().strip().rstrip(":")
        if lower in ("ingredients", "ingredient"):
            section = "ingredients"
            continue
        elif lower in ("instructions", "directions", "method", "steps",
                       "preparation", "direction", "procedure"):
            section = "instructions"
            continue
        elif lower in ("description", "about", "notes", "note"):
            section = "description"
            continue
        elif lower in ("variations", "variation", "tips", "tip"):
            section = "notes"
            continue

        if not line:
            continue

        if section == "ingredients":
            # Strip leading bullet/dash/number
            cleaned = re.sub(r'^[\-\*•]\s*', '', line)
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', cleaned)
            ingredients.append(cleaned)
        elif section == "instructions":
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
            instructions.append(cleaned)
        elif section == "description":
            description += line + " "
        elif section is None and not ingredients:
            # Before any section header, treat as description
            description += line + " "

    return {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time": None,
        "cook_time": None,
        "total_time": None,
        "servings": None,
        "description": description.strip(),
    }


def parse_onenote_text(text: str) -> dict | None:
    """Parse a recipe from OneNote-exported text with messy formatting.

    Handles OneNote quirks like:
    - Bullet characters (•) on their own line between ingredients
    - Step numbers on their own line after instruction text
    - Footer lines like 'Recipies Page N'
    - Metadata blocks (title + date + time) at the end of pages
    - Source URLs in various formats (From <URL>, Clipped from:, etc.)
    - Multiple time/serving metadata formats
    """
    lines = text.splitlines()

    # ── Strip footers and metadata ─────────────────────────────────────
    # Remove 'Recipies Page N' footers (note the typo is in the source)
    lines = [l for l in lines if not re.match(r'^\s*Recip[ie]+s\s+Page\s+\d+\s*$', l, re.IGNORECASE)]

    # Remove Office Lens timestamps
    lines = [l for l in lines if not re.match(r'^\s*\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s+Office\s+Lens', l, re.IGNORECASE)]

    # ── Extract source URL ─────────────────────────────────────────────
    source_url = None
    url_patterns = [
        r'From\s+<(https?://[^>]+)>',
        r'Clipped\s+from:\s*(https?://\S+)',
        r'Find\s+it\s+online:\s*(https?://\S+)',
        r'Read\s+more\s+at\s+(https?://\S+)',
        r'\[source:\s*([^\]]+)\]',
    ]
    cleaned_lines = []
    for line in lines:
        found_url = False
        for pattern in url_patterns:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                source_url = source_url or m.group(1).strip()
                found_url = True
                break
        if not found_url:
            cleaned_lines.append(line)
    lines = cleaned_lines

    # Also capture bare URLs at the start of pages but don't use as content
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^https?://\S+$', stripped) and not source_url:
            source_url = stripped
        elif re.match(r'^https?://\S+$', stripped):
            pass  # skip additional bare URLs
        else:
            cleaned_lines.append(line)
    lines = cleaned_lines

    # ── Extract time and serving metadata ──────────────────────────────
    prep_time = None
    cook_time = None
    total_time = None
    servings = None

    time_patterns = [
        # "Prep 20 min | Cook 2-3 hours | Serves 6-8"
        (r'Prep[:\s]+([\d½¼¾\-–]+\s*(?:min(?:utes?)?|hrs?|hours?))', 'prep'),
        (r'Cook(?:\s*Time)?[:\s]+([\d½¼¾\-–]+\s*(?:min(?:utes?)?|hrs?|hours?))', 'cook'),
        (r'Total(?:\s*Time)?[:\s]+([\d½¼¾\-–]+\s*(?:min(?:utes?)?|hrs?|hours?))', 'total'),
        (r'(?:Serves?|Servings?|Yield)[:\s]+([\d\-–]+(?:\s*servings?)?)', 'servings'),
        # "Hands-on Time 16 Mins"
        (r'Hands-on\s+Time[:\s]+([\d½¼¾\-–]+\s*(?:min(?:utes?)?|hrs?|hours?))', 'prep'),
    ]

    metadata_lines = set()
    for i, line in enumerate(lines):
        for pattern, field in time_patterns:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                value = _normalize_time(m.group(1).strip())
                if field == 'prep' and not prep_time:
                    prep_time = value
                elif field == 'cook' and not cook_time:
                    cook_time = value
                elif field == 'total' and not total_time:
                    total_time = value
                elif field == 'servings' and not servings:
                    servings = re.sub(r'\s*servings?', '', m.group(1).strip(), flags=re.IGNORECASE)
                metadata_lines.add(i)

    # Remove lines that were purely metadata (time/servings)
    # Only remove if the line is mostly metadata, not mixed with recipe content
    filtered_lines = []
    for i, line in enumerate(lines):
        if i in metadata_lines:
            # Check if the entire line is metadata (no other meaningful content)
            remaining = line
            for pattern, _ in time_patterns:
                remaining = re.sub(pattern, '', remaining, flags=re.IGNORECASE)
            remaining = re.sub(r'[|/•·,]', '', remaining).strip()
            if remaining and len(remaining) > 20:
                filtered_lines.append(line)  # line has other content, keep it
            # else: line was purely metadata, drop it
        else:
            filtered_lines.append(line)
    lines = filtered_lines

    # ── Strip trailing OneNote page metadata (title + date + time) ─────
    # Pattern: last non-blank lines are often:
    #   Recipe Title
    #   Saturday, April 2, 2016
    #   10:09 AM
    # Strip from the end
    while lines:
        last = lines[-1].strip()
        if not last:
            lines.pop()
            continue
        # Match date patterns: "Saturday, April 2, 2016" or "Monday, January 28, 2019"
        if re.match(r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\w+\s+\d{1,2},\s+\d{4}$', last):
            lines.pop()
            continue
        # Match time patterns: "10:09 AM" or "11:54"
        if re.match(r'^\d{1,2}:\d{2}(?:\s*[AP]M)?$', last, re.IGNORECASE):
            lines.pop()
            continue
        # Match random hash-like strings from OneNote (e.g., "St5fFunZdm")
        if re.match(r'^[A-Za-z0-9]{6,20}$', last) and not re.match(r'^[A-Z][a-z]+$', last):
            lines.pop()
            continue
        break

    # ── Identify title ─────────────────────────────────────────────────
    # Skip blank lines at the top
    while lines and not lines[0].strip():
        lines.pop(0)

    if not lines:
        return None

    # Title: first non-blank, non-metadata line
    # Skip lines that look like time metadata at the very top
    title = None
    title_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that are purely time/serving metadata
        if re.match(r'^(?:Cook\s*Time|Prep\s*Time|Total\s*Time|Serves?|Yield|Level)\b', stripped, re.IGNORECASE):
            continue
        # Skip lines that look like section headers
        if re.match(r'^(?:INGREDIENTS?|DIRECTIONS?|INSTRUCTIONS?)\s*:?$', stripped, re.IGNORECASE):
            continue
        title = stripped
        title_idx = i
        break

    if not title:
        return None

    # ── Parse body into sections ───────────────────────────────────────
    ingredients = []
    instructions = []
    description = ""
    section = None

    # Remove lone bullets (•) and rejoin with content lines
    body_lines = []
    for line in lines[title_idx + 1:]:
        stripped = line.strip()
        if stripped == '•' or stripped == '·':
            continue  # skip standalone bullet characters
        body_lines.append(stripped)

    # Handle step numbers on their own line: merge "2." with the previous line
    merged_lines = []
    for line in body_lines:
        if re.match(r'^\d+\.\s*$', line) and merged_lines:
            # This is just a step number — skip it (the previous line was the step)
            continue
        merged_lines.append(line)
    body_lines = merged_lines

    for line in body_lines:
        lower = line.lower().strip().rstrip(':')

        # Section header detection
        if re.match(r'^(?:ingredients?)$', lower):
            section = 'ingredients'
            continue
        elif re.match(r'^(?:directions?|instructions?|method|steps?|preparation|procedure)$', lower):
            section = 'instructions'
            continue
        elif re.match(r'^(?:description|about)$', lower):
            section = 'description'
            continue
        elif re.match(r'^(?:variations?|tips?|notes?|in\s+a\s+slow\s+cooker)$', lower):
            section = 'skip'  # skip supplementary sections
            continue

        if not line:
            continue

        if section == 'skip':
            continue

        if section == 'ingredients':
            cleaned = re.sub(r'^[\-\*•·]\s*', '', line)
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', cleaned)
            if cleaned:
                ingredients.append(cleaned)
        elif section == 'instructions':
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
            if cleaned:
                instructions.append(cleaned)
        elif section == 'description':
            description += line + ' '
        elif section is None:
            # Before any section header — could be description or time metadata
            # Skip if it's a date or metadata line at the top
            if not re.match(r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', line):
                description += line + ' '

    # Must have at least ingredients or instructions to be a valid recipe
    if not ingredients and not instructions:
        return None

    return {
        'title': title,
        'ingredients': ingredients,
        'instructions': instructions,
        'prep_time': prep_time,
        'cook_time': cook_time,
        'total_time': total_time,
        'servings': servings,
        'description': description.strip(),
        'source_url': source_url,
    }


def _normalize_time(time_str: str) -> str:
    """Normalize a time string like '20 minutes' or '2-3 hours' to shorthand."""
    # Replace unicode fractions
    time_str = time_str.replace('½', '.5').replace('¼', '.25').replace('¾', '.75')
    # Replace en-dash with hyphen
    time_str = time_str.replace('–', '-')

    # Try to parse "N hours M minutes" or similar
    m = re.match(r'^([\d.\-]+)\s*(min(?:utes?)?|hrs?|hours?)$', time_str, re.IGNORECASE)
    if m:
        value = m.group(1)
        unit = m.group(2).lower()
        if 'hour' in unit or unit.startswith('hr'):
            return f"{value}h"
        else:
            return f"{value}m"

    # Already short form
    return time_str


# ── Fetch and route ───────────────────────────────────────────────────────

def fetch_from_url(url: str) -> dict:
    """Fetch and parse a recipe from a URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    recipe = parse_schema_org(soup)
    if not recipe:
        recipe = parse_html_fallback(soup)
    if not recipe:
        print("Could not extract structured recipe data from the URL.")
        print("Falling back to manual entry...")
        recipe = interactive_entry()

    recipe["source_url"] = url
    return recipe


def load_from_file(filepath: str) -> dict:
    """Load a recipe from a local file (HTML or text)."""
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")

    if path.suffix.lower() in (".html", ".htm"):
        soup = BeautifulSoup(content, "html.parser")
        recipe = parse_schema_org(soup)
        if not recipe:
            recipe = parse_html_fallback(soup)
        if recipe:
            return recipe

    return parse_raw_text(content)


def interactive_entry() -> dict:
    """Prompt user to enter recipe details interactively."""
    print("\n── Enter Recipe Details ──")
    title = input("Title: ").strip() or "Untitled"
    description = input("Description (optional): ").strip()

    print("\nEnter ingredients (one per line, blank line to finish):")
    ingredients = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        ingredients.append(line)

    print("\nEnter instructions (one step per line, blank line to finish):")
    instructions = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        instructions.append(line)

    prep_time = input("Prep time (e.g. '15m', optional): ").strip() or None
    cook_time = input("Cook time (e.g. '30m', optional): ").strip() or None
    servings = input("Servings (optional): ").strip() or None

    return {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "total_time": None,
        "servings": servings,
        "description": description,
    }


# ── Output ─────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def save_recipe(recipe: dict, overwrite_path: Path | None = None):
    """Classify, format, and save recipe as a Jekyll markdown file.

    Args:
        recipe: Parsed recipe dict with title, ingredients, instructions, etc.
        overwrite_path: If set, write to this exact path (overwriting it).
                        If None, auto-generate path and avoid overwriting.
    """
    title = recipe.get("title", "Untitled")
    ingredients = recipe.get("ingredients", [])
    instructions = recipe.get("instructions", [])
    instructions_text = " ".join(instructions)

    # Classify
    classification = classify_recipe(title, ingredients, instructions_text)

    # Build front matter
    front = {
        "title": title,
        "dish_type": classification["dish_type"],
        "tags": classification["tags"],
    }
    if classification["cuisine"]:
        front["cuisine"] = classification["cuisine"]
    if classification["main_ingredient"]:
        front["main_ingredient"] = classification["main_ingredient"]
    if recipe.get("description"):
        front["description"] = recipe["description"]
    if recipe.get("prep_time"):
        front["prep_time"] = recipe["prep_time"]
    if recipe.get("cook_time"):
        front["cook_time"] = recipe["cook_time"]
    if recipe.get("total_time"):
        front["total_time"] = recipe["total_time"]
    if recipe.get("servings"):
        front["servings"] = str(recipe["servings"])
    if recipe.get("source_url"):
        front["source_url"] = recipe["source_url"]
    if ingredients:
        front["ingredients"] = ingredients
    if instructions:
        front["instructions"] = instructions

    # Write file
    RECIPES_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(title)

    if overwrite_path:
        filepath = overwrite_path
    else:
        filepath = RECIPES_DIR / f"{slug}.md"
        # Avoid overwriting
        counter = 1
        while filepath.exists():
            filepath = RECIPES_DIR / f"{slug}-{counter}.md"
            counter += 1

    yaml_str = yaml.dump(front, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)
    content = f"---\n{yaml_str}---\n"

    filepath.write_text(content, encoding="utf-8")

    print(f"\n✓ Recipe saved: {filepath.relative_to(RECIPES_DIR.parent)}")
    print(f"  Dish type:       {classification['dish_type']}")
    if classification["cuisine"]:
        print(f"  Cuisine:         {classification['cuisine']}")
    if classification["main_ingredient"]:
        print(f"  Main ingredient: {classification['main_ingredient']}")
    if classification["dietary_tags"]:
        print(f"  Dietary:         {', '.join(classification['dietary_tags'])}")
    print(f"  Tags:            {', '.join(classification['tags'])}")
    return filepath


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Add a recipe to the cookbook")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--url", help="URL of a recipe page to scrape")
    group.add_argument("--file", help="Path to a local HTML or text file")
    group.add_argument("--text", help="Path to a plain text recipe file")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Enter recipe details interactively")
    args = parser.parse_args()

    if args.url:
        recipe = fetch_from_url(args.url)
    elif args.file:
        recipe = load_from_file(args.file)
    elif args.text:
        recipe = load_from_file(args.text)
    elif args.interactive:
        recipe = interactive_entry()
    else:
        print("No input specified. Entering interactive mode.\n")
        recipe = interactive_entry()

    save_recipe(recipe)


if __name__ == "__main__":
    main()
