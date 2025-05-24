import datetime
from typing import List

from fastapi import logger
from api.core.database import get_supabase
from api.crawler.recipe import RecipeCrawler
from api.models.schemas import Recipe

supabase = get_supabase()


class RecipeService:
    @staticmethod
    async def scrape_recipes(query: str, max_recipes: int = 5) -> List[Recipe]:

        cached = (
            supabase.table("recipe_cache")
            .select("*")
            .eq("query", query.lower())
            .execute()
        )

        if cached.data:
            logger.info(f"Returning cached results for {query}")
            return [Recipe(**r) for r in cached.data[:max_recipes]]

        recipe_crawler = RecipeCrawler()
        raw_recipes = await recipe_crawler.crawl_recipes(query, max_recipes)

        if raw_recipes:
            supabase.table("recipe_cache").insert(
                [
                    {
                        "query": query.lower(),
                        "data": recipe.dict(),
                        "expires_at": datetime.now() + timedelta(days=1),
                    }
                    for recipe in raw_recipes
                ]
            ).execute()

            await recipe_crawler._save_to_supabase(recipe for recipe in raw_recipes)

            # # Insert to DB
            # db_recipe = await supabase.from_("recipes").insert(recipe.model_dump()).execute()
            # recipe_id = db_recipe.data[0]["id"]

            # # Generate embedding
            # embedding = get_embedding(f"{recipe.title} {recipe.ingredients}")
            # await supabase.from_("recipe_embeddings").insert({
            #     "recipe_id": recipe_id,
            #     "embedding": embedding,
            #     "ingredients_text": normalize_ingredients(recipe.ingredients)
            # })
        return raw_recipes
