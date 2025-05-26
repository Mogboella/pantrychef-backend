from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class Ingredient(BaseModel):
    name: str
    unit: Optional[str] = ""
    quantity: Optional[str] = ""

class PantryItem(BaseModel):
    ingredient: Ingredient
    expiry_date: Optional[datetime] = None

class PantryItemOut(PantryItem):
    id: int
    created_at: datetime
    normalized_name: str

class PantryHash(BaseModel):
    hash: str
    items: List[str]

class GroceryItemCreate(BaseModel):
    ingredient: Ingredient

class GroceryItemOut(GroceryItemCreate):
    id: int
    session_id: str
    normalized_name: str
    purchased: bool
    created_at: datetime

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
    id: str = ""
    cuisine: Optional[str] = None
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            HttpUrl: lambda v: str(v),
        }


class RecipeEmbeddingCreate(BaseModel):
    recipe_id: str
    embedding: List[float] = Field(..., max_length=1536)
    ingredients_text: str


class RecipeEmbeddingDB(RecipeEmbeddingCreate):
    class Config:
        from_attributes = True


class ScoredRecipe(RecipeDB):
    score: float = Field(..., ge=0, le=1)  
    missing_ingredients: List[str]
    match_percentage: float = Field(..., ge=0, le=100)  # 0-100%
    exact_matches: int
    fuzzy_matches: int
    embedding_similarity: Optional[float]
