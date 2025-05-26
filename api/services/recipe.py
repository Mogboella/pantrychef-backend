import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List
from api.core.cache import cache_recipes, get_cached_recipes
from rapidfuzz import fuzz

from api.core.database import get_supabase
from api.core.rec_engine import cosine_similarity, normalize_ingredient, classify_cuisine, get_embedding
from api.crawler.recipe import RecipeCrawler
from api.models.schemas import Recipe, RecipeCreate, RecipeDB, ScoredRecipe

supabase = get_supabase()
logger = logging.getLogger(__name__)

class RecipeService:
    @staticmethod
    def get_recipe_from_db(recipe_id) -> RecipeDB:
        recipes = supabase.from_("recipes").select("*").eq("id", recipe_id).single().execute()
        return recipes.data if recipes else {}
    
    @staticmethod
    async def scrape_recipes(query: str, max_recipes: int = 5) -> List[Recipe]:
        try:
            if cached := await get_cached_recipes(query):
                logger.info(f"Cache hit for query: {query}")
                return cached[:max_recipes]
            
            recipe_crawler = RecipeCrawler()
            raw_recipes = await recipe_crawler.crawl_recipes(query, max_recipes)

            if not raw_recipes:
                logger.warning(f"No recipes found for query: {query}")
                return []
            
            await cache_recipes(query, raw_recipes)
            
            # Store recipes in parallel
            stored_recipes = await RecipeService.store_recipes(raw_recipes) 
            
            return stored_recipes
        except Exception as e:
            logger.error(f"Error scraping recipes: {str(e)}")
            raise

    @staticmethod
    async def score_recipe(
        pantry_items: List[str],
        recipe: Dict,
        use_embeddings: bool = True,
        fuzzy_threshold: int = 75,
        embedding_weight: float = 0.3
    ) -> ScoredRecipe:
        """
        Scores a recipe based on pantry items using hybrid matching.
        
        Args:
            pantry_items: List of available ingredient names
            recipe: Recipe dictionary containing 'id' and 'ingredients'
            use_embeddings: Whether to use semantic similarity
            fuzzy_threshold: Minimum fuzz ratio to count as match (0-100)
            embedding_weight: How much to weight embedding similarity (0-1)
            
        Returns:
            ScoreResult with detailed scoring breakdown
        """
        # Initialize results
        missing = []
        fuzzy_matches = 0
        embedding_sim = None

        pantry_set = {normalize_ingredient(i) for i in pantry_items}
        recipe_ingredients = [
            normalize_ingredient(ing["name"]) for ing in recipe["ingredients"]
        ]

        # Exact + Fuzzy Matching
        for ingredient in recipe_ingredients:
            if ingredient not in pantry_set:
                # Check fuzzy matches
                best_match = max(
                    [
                        (fuzz.ratio(ingredient, pantry_ing), pantry_ing)
                        for pantry_ing in pantry_set
                    ],
                    default=(0, None),
                )

                if best_match[0] > 75:  # 75% similarity threshold
                    fuzzy_matches += 1
                else:
                    missing.append(ingredient)

        total_ingredients = len(recipe_ingredients)
        exact_matches = len(pantry_set.intersection(recipe_ingredients))
        
        exact_score = (exact_matches + fuzzy_matches * 0.7) / total_ingredients

        if use_embeddings and "id" in recipe:
            try:
                # Get pre-computed embedding
                emb_response = supabase.from_("recipe_embeddings") \
                    .select("embedding") \
                    .eq("recipe_id", recipe["id"]) \
                    .single().execute()
                
                if emb_response.data:
                    pantry_embedding = await get_embedding(", ".join(pantry_items))
                    embedding_sim = cosine_similarity(
                        pantry_embedding,
                        emb_response.data["embedding"]
                    )
                    
                    # Combine scores
                    final_score = (1 - embedding_weight) * exact_score + \
                                embedding_weight * embedding_sim
                else:
                    final_score = exact_score
            except Exception as e:
                logger.warning(f"Embedding scoring failed: {str(e)}")
                final_score = exact_score
        else:
            final_score = exact_score

        return {
            "score": min(max(final_score, 0), 1),  
            "missing_ingredients": missing,
            "match_percentage": round(final_score * 100, 1),
            "exact_matches": exact_matches,
            "fuzzy_matches": fuzzy_matches,
            "embedding_similarity": embedding_sim
        }

    @staticmethod
    async def store_recipe(recipe: RecipeCreate) -> RecipeDB:
        """Store a new recipe with embeddings and cuisine"""
        # Insert recipe
        res = supabase.from_("recipes").insert(json.loads(recipe.model_dump_json())).execute()
        recipe_db = res.data[0]

        # Generate embedding
        ingredients_text = ", ".join(
            f"{ing.quantity} {ing.unit} {ing.name}" for ing in recipe.ingredients
        )
        embedding = await get_embedding(f"{recipe.title} {ingredients_text}")

        supabase.from_("recipe_embeddings").insert(
            {
                "recipe_id": recipe_db["id"],
                "embedding": embedding,
                "ingredients_text": ingredients_text,
            }
        ).execute()

        # Classify cuisine if not provided
        if not recipe_db.get("cuisine"):
            cuisine = classify_cuisine(recipe)
            supabase.from_("recipes").update({"cuisine": cuisine}).eq(
                "id", recipe_db["id"]
            ).execute()
            recipe_db["cuisine"] = cuisine

        return recipe_db

    @staticmethod
    async def store_recipes(recipes: List[RecipeCreate]) -> List[RecipeDB]:
        """Store multiple recipes with embeddings and optional cuisine classification"""
        if not recipes:
            return []

        # Insert all recipes into the 'recipes' table
        recipes_payload = [json.loads(recipe.model_dump_json()) for recipe in recipes]
        res = supabase.from_("recipes").insert(recipes_payload).execute()
        db_recipes = res.data  # List of inserted recipes with IDs

        # Prepare embeddings and ingredients text
        embeddings_payload = []
        updates = []
        for recipe, db_recipe in zip(recipes, db_recipes):
            ingredients_text = ", ".join(
                f"{ing.quantity} {ing.unit} {ing.name}" for ing in recipe.ingredients
            )
            embedding = await get_embedding(f"{recipe.title} {ingredients_text}")

            if not embedding or len(embedding) == 0:
                print(f"Skipping recipe '{recipe.title}' due to empty embedding.")
                continue
            
            embeddings_payload.append({
                "recipe_id": db_recipe["id"],
                "embedding": embedding,
                "ingredients_text": ingredients_text,
            })

            # Classify cuisine if missing
            if not db_recipe.get("cuisine"):
                cuisine = classify_cuisine(recipe)
                updates.append({"id": db_recipe["id"], "cuisine": cuisine})
                db_recipe["cuisine"] = cuisine

        # Insert all recipe embeddings at once
        if embeddings_payload:
            supabase.from_("recipe_embeddings").insert(embeddings_payload).execute()

        # Update cuisine classifications in bulk (if any)
        for update in updates:
            supabase.from_("recipes").update(
                {"cuisine": update["cuisine"]}
            ).eq("id", update["id"]).execute()

        return db_recipes
