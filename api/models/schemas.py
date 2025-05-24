from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class Ingredient(BaseModel):
    name: str
    unit: Optional[str]
    quantity: Optional[str]


class Recipe(BaseModel):
    title: str
    ingredients: List[Ingredient]
    prep_time: Optional[str]
    cook_time: Optional[str]
    image_url: Optional[str]
    source_url: HttpUrl
    source: str = "allrecipes"


class RecipeCreate(Recipe):
    pass


class RecipeDB(Recipe):
    id: str
    cuisine: Optional[str] = None
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class RecipeEmbeddingCreate(BaseModel):
    recipe_id: str
    embedding: List[float] = Field(..., max_length=1536)
    ingredients_text: str


class RecipeEmbeddingDB(RecipeEmbeddingCreate):
    class Config:
        from_attributes = True


class ScoredRecipe(RecipeDB):
    score: float = Field(..., ge=0, le=1)  # 0-1 match score
    missing_ingredients: List[str]
    match_percentage: float = Field(..., ge=0, le=100)  # 0-100%
