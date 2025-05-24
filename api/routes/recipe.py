from typing import List
from fastapi import APIRouter, HTTPException
from api.core.database import get_supabase

from api.core.rec_engine import generate_recipe_variation
from api.models.requests import RecipeRequest
from api.models.schemas import Recipe, RecipeDB, ScoredRecipe
from api.services.recipe import RecipeService
from api.services.session import SessionService

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

session_service = SessionService()

supabase = get_supabase()


@router.post(
    "/recommend",
    summary="Get Recipe Recommendations",
    description="Recommend recipes based on pantry items",
    response_description="List of recommended recipes",
    response_model=List[ScoredRecipe],
)
async def recommend_recipes(request: RecipeRequest):
    try:
        session = await session_service.get_session(request.session_id)
        ingredients = session["session_data"]["pantry_items"]

        recipe_service = RecipeService()

        # Get recommendations
        # recommendations = await get_recommendations(
        #     pantry_items=pantry_items,
        #     filters=request.filters
        # )

        # return recommendations

        return await recipe_service.scrape_recipes(query=ingredients)
    except Exception as e:
        logger.exception("Failed to recommend recipes")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/search",
    summary="Get Recipe by Searching for Ingredients",
    description="Returns recipes that can be made with the provided ingredients",
    response_description="List of scraped recipes",
    response_model=List[RecipeDB],
)
async def search_recipes(query: str, session_id: str):
    try:
        session = await session_service.get_session(session_id)
        ingredients = session["session_data"]["pantry_items"]

        recipe_service = RecipeService()
        recipes = await recipe_service.scrape_recipes(query=query)

        # Get recommendations
        # recommendations = await get_recommendations(
        #     pantry_items=pantry_items,
        #     filters=request.filters
        # )

        # return recommendations

        return recipes
    except Exception as e:
        logger.exception("Failed to recommend recipes")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recipes/{recipe_id}/variation")
async def generate_variation(recipe_id: str, session_id: str):
    """Generate a recipe variation using pantry items"""
    session = await session_service.get_session(session_id)
    pantry_items = session["session_data"]["pantry_items"]

    recipe = (
        supabase.from_("recipes").select("*").eq("id", recipe_id).single().execute()
    )

    if not recipe.data:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Generate variation (implementation in next section)
    variation = await generate_recipe_variation(
        recipe=recipe.data, pantry_items=pantry_items
    )

    return variation


@router.get("/recipes/{recipe_id}", response_model=RecipeDB)
async def get_recipe(recipe_id: str):
    """Get a single recipe by ID"""
    recipe = (
        supabase.from_("recipes").select("*").eq("id", recipe_id).single().execute()
    )

    if not recipe.data:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return recipe.data
