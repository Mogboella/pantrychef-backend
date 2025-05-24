from typing import List
from fastapi import APIRouter, HTTPException

from api.models.requests import RecipeRequest
from api.models.schemas import Recipe
from api.services.recipe import RecipeService

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    summary="Get Recipe Recommendations",
    description="Returns recipes that can be made with the provided ingredients",
    response_description="List of recommended recipes",
    response_model=List[Recipe],
)
async def recommend_recipes(request: RecipeRequest):
    try:
        recipe_service = RecipeService()
        ingredients = ",".join(request.ingredients)
        return await recipe_service.scrape_recipes(query=ingredients)
    except Exception as e:
        logger.exception("Failed to recommend recipes")
        raise HTTPException(status_code=500, detail=str(e))
