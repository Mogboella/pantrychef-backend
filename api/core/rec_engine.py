import json
import os
from typing import Dict, List, Optional
from api.settings import Settings

from fastapi import HTTPException
from openai import OpenAI
from api.core.database import get_supabase
from api.core.recipe import score_recipe, store_recipe
from api.models.schemas import RecipeCreate, ScoredRecipe

settings = Settings()

supabase = get_supabase()
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def get_embedding(text: str, model="text-embedding-3-small") -> List[float]:
    """Get text embedding from OpenAI"""
    text = text.replace("\n", " ")
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding


def classify_cuisine(recipe) -> str:
    """Classify recipe cuisine using LLM"""
    ingredients = ", ".join(
        f"{i['quantity']} {i['unit']} {i['name']}" for i in recipe.ingredients
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "Classify the cuisine type. Respond with just one word: Italian, Mexican, Chinese, Indian, American, Mediterranean, Japanese, Thai, French, or Other.",
            },
            {
                "role": "user",
                "content": f"Title: {recipe.title}\nIngredients: {ingredients}",
            },
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()


async def get_recommendations(
    pantry_items: List[str], filters: Optional[Dict] = None
) -> List[ScoredRecipe]:
    """Main recommendation logic"""
    if filters is None:
        filters = {}

    # Get similar recipes via vector search
    query_embedding = get_embedding(", ".join(pantry_items))
    query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    similar = supabase.rpc(
        "vector_search",
        {
            "query_embedding": query_embedding_str,
            "match_threshold": 0.7,
            "match_count": 50,
        },
    ).execute()

    # Score each recipe
    scored_recipes = []
    for recipe in similar.data:
        scored = score_recipe(pantry_items, recipe)

        # Apply filters
        if (
            filters.get("max_missing")
            and len(scored["missing_ingredients"]) > filters["max_missing"]
        ):
            continue

        if filters.get("cuisine") and recipe.get("cuisine") != filters["cuisine"]:
            continue

        scored_recipes.append(ScoredRecipe(**{**recipe, **scored}))

    # Sort by score and return
    scored_recipes.sort(key=lambda x: x.score, reverse=True)
    return scored_recipes[: filters.get("limit", 10)]


async def generate_recipe_variation(recipe: Dict, pantry_items: List[str]) -> Dict:
    """Generate a recipe variation using LLM"""
    from openai import OpenAI

    client = OpenAI()

    prompt = f"""Create a variation of this recipe using mainly these ingredients: {', '.join(pantry_items)}.
    
    Original Recipe:
    Title: {recipe['title']}
    Ingredients: {', '.join(f"{i['quantity']} {i['unit']} {i['name']}" for i in recipe['ingredients'])}
    
    Create a similar but modified version that uses as many of the provided ingredients as possible.
    Return in JSON format with: title, ingredients (list with name, quantity, unit), and instructions."""

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a professional chef. Create recipe variations.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    try:
        variation = json.loads(response.choices[0].message.content)
        # Store the variation
        variation_db = await store_recipe(
            RecipeCreate(
                title=variation["title"],
                ingredients=variation["ingredients"],
                source_url=f"variation-of-{recipe['id']}",
                source="llm-generated",
            )
        )
        return variation_db
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to generate variation: {str(e)}"
        )
