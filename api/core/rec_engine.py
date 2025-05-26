import asyncio
import json
import logging
import os
from typing import Dict, List, Optional
from api.core.cache import cache_recipes, get_cached_recipes
from api.settings import Settings
import numpy as np
from fastapi import HTTPException
from openai import OpenAI, OpenAIError, RateLimitError
from .database import get_supabase
from api.models.schemas import Ingredient, RecipeCreate, ScoredRecipe

settings = Settings()
logger = logging.getLogger(__name__)

supabase = get_supabase()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def normalize_ingredient(ingredient: Ingredient) -> str:
    """Normalize ingredient names for comparison"""
    return (
        ingredient.name.lower()
        .replace("fresh", "")
        .replace("dried", "")
        .replace("chopped", "")
        .strip()
    )

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

async def get_embedding(text: str, model="text-embedding-3-small") -> list[float]:
    """Get text embedding from OpenAI asynchronously with error handling"""
    text = text.replace("\n", " ")

    def blocking_call():
        return client.embeddings.create(input=[text], model=model)

    try:
        response = await asyncio.to_thread(blocking_call)
        return response.data[0].embedding
    except RateLimitError as e:
        print(f"OpenAI rate limit error: {e}")
        return []
    except OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return []


def classify_cuisine(recipe) -> str:
    """Classify recipe cuisine using LLM"""
    ingredients = ", ".join(
        f"{i.quantity} {i.unit} {i.name}" for i in recipe.ingredients
    )

    try:
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
    
    except Exception as e:
        logger.warning(f"Cuisine Not Classified : {e}")
        return ""


