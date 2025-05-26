import hashlib
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Optional

from .database import get_supabase
from api.models.schemas import RecipeDB

supabase = get_supabase()

def generate_query_hash(query: str) -> str:
    """Generate consistent MD5 hash for query strings"""
    return hashlib.md5(query.lower().encode()).hexdigest()

async def get_cached_recipes(query: str) -> Optional[List[RecipeDB]]:
    """Check cache for existing results"""
    query_hash = generate_query_hash(query)
    
    res = supabase.table("recipe_cache") \
        .select("results") \
        .eq("query_hash", query_hash) \
        .gt("expires_at", datetime.now()) \
        .execute()
    
    return [RecipeDB(**recipe) for item in res.data for recipe in item["results"]] if res.data else None


async def cache_recipes(query: str, recipes: List[RecipeDB]) -> None:
    query_hash = generate_query_hash(query)
    results = [recipe.model_dump(mode='json') for recipe in recipes]
    
    data_to_insert = {
            "query_hash": query_hash,
            "query": query.lower(),
            "results": results, 
            "expires_at": (datetime.now() + timedelta(days=1)).isoformat()  
        }
        
    supabase.table("recipe_cache").upsert(data_to_insert, on_conflict="query_hash").execute()


async def clean_expired_cache():
    """Remove expired cache entries"""
    supabase.table("recipe_cache") \
        .delete() \
        .lt("expires_at", datetime.now()) \
        .execute()