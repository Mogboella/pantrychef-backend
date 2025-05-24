from typing import List, Optional
from pydantic import BaseModel


class CrawlerTask(BaseModel):
    query: str
    max_recipes: int = 5
    session_id: str


class RecipeFilters(BaseModel):
    max_missing: Optional[int] = None
    cuisine: Optional[List[str]] = None
    max_time: Optional[int] = None


class RecipeRequest(BaseModel):
    ingredients: List[str]
    filters: Optional["RecipeFilters"] = None
    session_id: Optional[str] = None


class RecommendationRequest(BaseModel):
    session_id: str
    filters: Optional["RecipeFilters"] = None
