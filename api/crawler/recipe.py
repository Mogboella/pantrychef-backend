import json
from typing import List, Optional
import openai
from tenacity import retry, stop_after_attempt, wait_fixed
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from api.core.database import get_supabase
from api.settings import Settings
from api.models.schemas import Ingredient, Recipe

import asyncio
import logging


# Init Settings
settings = Settings()

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Optional: log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(console_handler)


class RecipeCrawler:
    def __init__(self):
        self.proxy_host = settings.BRIGHT_DATA_PROXY_HOST
        self.proxy_port = settings.BRIGHT_DATA_PROXY_PORT
        self.proxy_user = settings.BRIGHT_DATA_PROXY_USERNAME
        self.proxy_pass = settings.BRIGHT_DATA_PROXY_PASSWORD

        self.supabase = get_supabase()

    async def crawl_recipes(self, query="chicken soup", max_recipes=5) -> List[Recipe]:
        async with async_playwright() as p:

            browser = await self._launch_browser(p)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            search_url = self._build_search_url(query)
            logger.info(f"Navigating to {search_url}")
            await page.goto(search_url, timeout=60000, wait_until="load")

            card_selector = await self._determine_card_selector(page)
            recipe_urls = await self._extract_recipe_urls(
                page, card_selector, max_recipes
            )

            recipes = await self._scrape_all_recipes(context, recipe_urls)

            await browser.close()

            logger.info(recipes)

            return recipes

    def _build_search_url(self, query):
        return f"https://www.allrecipes.com/search?q={query.replace(' ', '+')}"

    async def _launch_browser(self, playwright):
        return await playwright.chromium.launch(
            headless=True,
            proxy={
                "server": f"http://{self.proxy_host}:{self.proxy_port}",
                "username": self.proxy_user,
                "password": self.proxy_pass,
            },
        )

    async def _determine_card_selector(self, page):
        try:
            await page.wait_for_selector("a.card", timeout=15000)
            return "a.card"
        except PlaywrightTimeoutError:
            await page.wait_for_selector("div.card__content", timeout=15000)
            return "div.card__content"

    async def _extract_recipe_urls(self, page, card_selector, max_recipes):
        cards = await page.query_selector_all(card_selector)
        urls = []

        for card in cards[:max_recipes]:
            try:
                href = await card.get_attribute("href")
                if href and href.startswith("http"):
                    urls.append(href)
            except Exception as e:
                logger.error(f"Error extracting card href: {e}")
        return urls

    async def _scrape_all_recipes(self, context, urls) -> List[Recipe]:
        semaphore = asyncio.Semaphore(3)

        async def scrape_with_limit(url):
            async with semaphore:
                page = await context.new_page()
                result = await self._scrape_recipe_with_retries(page, url)
                await page.close()
                return result

        tasks = [scrape_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if isinstance(r, Recipe)]

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def _scrape_recipe_with_retries(self, page, url):
        return await self._scrape_recipe(page, url)

    async def _scrape_recipe(self, page, url) -> Optional[Recipe]:
        try:
            logger.info(f"Scraping recipe: {url}")
            await page.goto(url, timeout=60000, wait_until="load")

            title = await self._get_title(page)
            prep_time, cook_time = await self._get_times(page)
            ingredients = await self._get_ingredients(page)
            image_url = await self._get_image_url(page)

            if not ingredients:
                logger.warning("Failed normal scraping, trying LLM fallback")
                page_content = await page.content()
                ingredients = await self._llm_parse_ingredients(page_content)

            if ingredients and title:
                recipe = Recipe(
                    title=title.strip(),
                    prep_time=prep_time,
                    cook_time=cook_time,
                    ingredients=ingredients,
                    image_url=image_url,
                    source_url=url,
                    source="allrecipes",
                )

                return recipe

        except PlaywrightTimeoutError:
            logger.warning(f"Timeout loading recipe page {url}")
        except Exception as e:
            logger.error(f"Error scraping recipe {url}: {e}")

        return None

    async def _llm_parse_ingredients(self, html: str) -> List[Ingredient]:
        """Fallback parsing using LLM when normal scraping fails"""
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Extract recipe ingredients from this HTML. Return JSON with list of ingredients (name, quantity, unit).",
                },
                {"role": "user", "content": html[:15000]},  # Truncate to fit context
            ],
        )

        try:
            data = json.loads(response.choices[0].message.content)
            return [Ingredient(**ing) for ing in data.get("ingredients", [])]
        except:
            return []

    async def _get_image_url(self, page):
        img_el = await page.query_selector("img.primary-image__image")
        img_url = await img_el.get_attribute("src") if img_el else ""
        logger.info(img_el)
        return img_url

    async def _get_title(self, page):
        title_el = await page.query_selector("h1.article-heading")
        return (await title_el.inner_text()).strip() if title_el else "No Title"

    async def _get_times(self, page):
        items = await page.query_selector_all("div.mm-recipes-details__item")
        prep_time = cook_time = None

        for item in items:
            label_el = await item.query_selector("div.mm-recipes-details__label")
            value_el = await item.query_selector("div.mm-recipes-details__value")
            if not label_el or not value_el:
                continue

            label = (await label_el.inner_text()).strip().lower()
            value = (await value_el.inner_text()).strip()

            if "prep time" in label:
                prep_time = value
            elif "cook time" in label:
                cook_time = value

        return prep_time, cook_time

    async def _get_ingredients(self, page) -> List[Ingredient]:
        items = await page.query_selector_all(
            "li.mm-recipes-structured-ingredients__list-item"
        )
        ingredients = []

        for item in items:
            quantity = await item.query_selector("span[data-ingredient-quantity]")
            unit = await item.query_selector("span[data-ingredient-unit]")
            name = await item.query_selector("span[data-ingredient-name]")

            quantity_text = (await quantity.inner_text()).strip() if quantity else ""
            unit_text = (await unit.inner_text()).strip() if unit else ""
            name_text = (await name.inner_text()).strip() if name else ""

            ingredients.append(
                Ingredient(
                    name=name_text,
                    unit=unit_text,
                    quantity=quantity_text,
                )
            )

        return ingredients

    async def _save_to_supabase(self, recipe: Recipe):
        try:
            logger.info(f"Saving recipe to Supabase: {recipe.title}")
            response = self.supabase.table("recipes").insert(recipe.dict()).execute()
            if response.error:
                logger.error(f"Supabase insert error: {response.error}")
        except Exception as e:
            logger.error(f"Failed to insert into Supabase: {e}")
