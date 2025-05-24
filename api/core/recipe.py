import json
from typing import Dict, List
from rapidfuzz import fuzz

from api.core.database import get_supabase
from api.models.schemas import RecipeCreate, RecipeDB

supabase = get_supabase()


def normalize_ingredient(name: str) -> str:
    """Normalize ingredient names for comparison"""
    return (
        name.lower()
        .replace("fresh", "")
        .replace("dried", "")
        .replace("chopped", "")
        .strip()
    )


def score_recipe(pantry_items: List[str], recipe: Dict) -> Dict:
    """Score a recipe based on pantry items"""
    pantry_set = {normalize_ingredient(i) for i in pantry_items}
    recipe_ingredients = [
        normalize_ingredient(ing["name"]) for ing in recipe["ingredients"]
    ]

    # Calculate matches
    missing = []
    fuzzy_matches = 0

    for recipe_ing in recipe_ingredients:
        if recipe_ing not in pantry_set:
            # Check fuzzy matches
            best_match = max(
                [
                    (fuzz.ratio(recipe_ing, pantry_ing), pantry_ing)
                    for pantry_ing in pantry_set
                ],
                default=(0, None),
            )

            if best_match[0] > 75:  # 75% similarity threshold
                fuzzy_matches += 1
            else:
                missing.append(recipe_ing)

    total_ingredients = len(recipe_ingredients)
    exact_matches = len(pantry_set.intersection(recipe_ingredients))
    score = (exact_matches + fuzzy_matches * 0.7) / total_ingredients

    return {
        "score": score,
        "missing_ingredients": missing,
        "match_percentage": round(score * 100, 1),
    }


async def store_recipe(recipe: RecipeCreate) -> RecipeDB:
    """Store a new recipe with embeddings and cuisine"""
    # Insert recipe
    res = supabase.from_("recipes").insert(json.loads(recipe.model_dump_json())).execute()
    recipe_db = res.data[0]

    # Generate embedding
    ingredients_text = ", ".join(
        f"{ing.quantity} {ing.unit} {ing.name}" for ing in recipe.ingredients
    )
    embedding = get_embedding(f"{recipe.title} {ingredients_text}")

    supabase.from_("recipe_embeddings").insert(
        {
            "recipe_id": recipe_db["id"],
            "embedding": embedding,
            "ingredients_text": ingredients_text,
        }
    ).execute()

    # Classify cuisine if not provided
    if not recipe_db.get("cuisine"):
        cuisine = classify_cuisine(recipe)
        supabase.from_("recipes").update({"cuisine": cuisine}).eq(
            "id", recipe_db["id"]
        ).execute()
        recipe_db["cuisine"] = cuisine

    return recipe_db
