import datetime

from fastapi import logger
from api.core.database import get_supabase
from api.crawler.recipe import RecipeCrawler

supabase = get_supabase()


async def refresh_outdated_recipes(days_old=7):

    # Get recipes older than X days from Supabase
    old_recipes = (
        supabase.table("recipes")
        .select("id,source_url,title")
        .lt("last_updated", datetime.now() - datetime.timedelta(days=days_old))
        .execute()
    )

    crawler = RecipeCrawler()
    for recipe in old_recipes.data:
        try:
            # Recrawl the recipe
            updated = await crawler._scrape_recipe(recipe["source_url"])
            if updated:
                # Update database
                supabase.table("recipes").update(updated.dict()).eq(
                    "id", recipe["id"]
                ).execute()
        except Exception as e:
            logger.error(f"Failed to refresh {recipe['title']}: {e}")
