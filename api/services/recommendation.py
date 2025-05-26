import json
from typing import Dict, List, Optional

from fastapi import HTTPException
from api.core.cache import cache_recipes, get_cached_recipes
from api.core.database import get_supabase
from api.core.rec_engine import get_embedding
from api.models.schemas import RecipeCreate, ScoredRecipe
from api.services.recipe import RecipeService
from api.utils import parse_time_to_minutes

supabase = get_supabase()

class RecommendationService:
    @staticmethod
    def generate_shopping_list(recipe_id: str, pantry_items: List[str]) -> Dict:
        """Identify missing ingredients for a specific recipe"""
        recipe = RecipeService.get_recipe_from_db(recipe_id)
        scoring = RecipeService.score_recipe(pantry_items, recipe)
        
        return {
            'recipe': recipe['title'],
            'missing_ingredients': scoring['missing_ingredients'],
            'confidence': f"{scoring['match_percentage']}% match"
        }
    
    def personalize_feed(recipes: List[Dict], user_prefs: Dict) -> List[Dict]:
        """Combine score with user preferences"""
        pantry = user_prefs['pantry_items']
        
        for recipe in recipes:
            # Base score from ingredients
            ingredient_score = RecipeService.score_recipe(pantry, recipe)['score']
            
            # Combine with user preferences (e.g., loves Italian cuisine)
            cuisine_boost = 0.2 if recipe.get('cuisine') == user_prefs['fav_cuisine'] else 0
            recipe['personal_score'] = ingredient_score + cuisine_boost
        
        return sorted(recipes, key=lambda x: -x['personal_score'])
    
    @staticmethod
    async def get_recommendations(
        pantry_items: List[str], filters: Optional[Dict] = None, query = None
    ) -> List[ScoredRecipe]:
        """Main recommendation logic"""
        
        filters = filters or {}
        recipes = []

        if query:
            cached = await get_cached_recipes(query)
            if cached:
                return cached

        query_embedding = await get_embedding(", ".join(pantry_items))
        query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]" if query_embedding else ""

        try:
            similar = supabase.rpc(
                "vector_search",
                {
                    "query_embedding": query_embedding_str,
                    "match_threshold": 0.7,
                    "match_count": 50,
                },
            ).execute()
            recipes = similar.data or []
        except Exception as e:
            print(f"Vector search failed: {e}")
            recipes = []

        if not recipes:
           
            query_db = supabase.table("recipes")
            if filters.get("cuisine"):
                query_db = query_db.eq("cuisine", filters["cuisine"])
            
            response = query_db.limit(50).execute()
            recipes = response.data or []

        # Score each recipe
        scored_recipes = []
        for recipe in recipes:
            scored = RecipeService.score_recipe(pantry_items, recipe)

            # Apply filters
            if (
                filters.get("max_missing") is not None 
                and len(scored["missing_ingredients"]) > filters["max_missing"]
            ):
                continue

            if filters.get("cuisine") and recipe.get("cuisine") != filters["cuisine"]:
                continue

            max_time = filters.get("max_time")
            print(max_time)
            if max_time is not None:
                cook_time = recipe.get("cook_time", None)
                prep_time = recipe.get("prep_time", None)
                cook_time_mins = parse_time_to_minutes(cook_time)
                prep_time_mins = parse_time_to_minutes(prep_time)
                total_time = cook_time_mins + prep_time_mins
                print(total_time)

                if total_time == 0 or total_time > max_time:
                    continue

            scored_recipes.append(ScoredRecipe(**{**recipe, **scored}))

        cache_key = query or ",".join(pantry_items)

        await cache_recipes(cache_key, scored_recipes)
        
        # Sort by score and return
        scored_recipes.sort(key=lambda x: x.score, reverse=True)
        return scored_recipes[: filters.get("limit", 10)]

    @staticmethod
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
            variation_db = await RecipeService.store_recipe(
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
