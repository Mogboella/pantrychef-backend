from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from api.core.database import get_supabase

from api.dependecies import get_session_id
from api.models.requests import RecipeFilters, RecipeRequest
from api.models.schemas import Recipe, RecipeDB, ScoredRecipe
from api.services.pantry import PantryService
from api.services.recipe import RecipeService
from api.services.recommendation import RecommendationService
from api.services.session import SessionService

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

session_service = SessionService()
recipe_service = RecipeService()
recom_service = RecommendationService()
pantry_service = PantryService()

supabase = get_supabase()

@router.get("/", response_model=List[Recipe])
async def list_recipes(
    session_id: str = Depends(get_session_id),
    query: Optional[str] = None,
    cuisine: Optional[str] = None,
    max_time: Optional[int] = None,
    max_missing: Optional[int] = None
):
    """Search with filters"""
    filters = RecipeFilters(
        cuisine=cuisine,
        max_time=max_time,
        max_missing=max_missing
    ).dict(exclude_none=True)

   
    if query is not None:
        await recipe_service.scrape_recipes(query)

    try :
        pantry_items_data = await pantry_service.get_pantry_items(session_id)
        pantry_items = [item.normalized_name for item in pantry_items_data]
        recommendations = await recom_service.get_recommendations(
            pantry_items, filters, query
        )
    except Exception as e:
        logger.error(f"Failed to Generate Recommendations: {e}")
    
    return recommendations

@router.post("/recommend")
async def get_recommended_recipes(
    session_id: str = Depends(get_session_id),
    max_missing: Optional[int] = None,
    min_score: Optional[float] = 0.4
    ):
    """Get recipes sorted by pantry match score"""
    filters = {
        "max_missing": max_missing,
        "min_score": min_score
    }

    try :
        pantry_items = await pantry_service.get_pantry_items(session_id)
        recommendations = await recom_service.get_recommendations(
            pantry_items, filters
        )
    except Exception as e:
        logger.error(f"Failed to Generate Recommendations: {e}")
    
    return recommendations


@router.get("/{recipe_id}", response_model=RecipeDB)
async def get_recipe(
    recipe_id: str,
    session_id: str = Depends(get_session_id)
):
    """Get detailed recipe with scoring"""
    recipe = recipe_service.get_recipe_from_db(recipe_id)
    if not recipe:
        raise HTTPException(404, detail="Recipe not found")
    return recipe