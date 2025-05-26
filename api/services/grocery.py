import os
import json
from typing import List, Optional
from datetime import datetime
from api.core.database import get_supabase
from api.models.schemas import Ingredient, GroceryItemOut

supabase = get_supabase()

def normalize_ingredient_name(ingredient: Ingredient) -> str:
        """Create consistent searchable name"""
        parts = []
        if ingredient.quantity:
            parts.append(ingredient.quantity)
        parts.append(ingredient.name)
        if ingredient.unit:
            parts.append(ingredient.unit)
        return "_".join(part.lower().strip() for part in parts)


class GroceryService:
    @staticmethod
    async def add_to_grocery(session_id: str, ingredients: List[Ingredient]) -> List[GroceryItemOut]:
        """Add multiple ingredients to grocery list"""
        items = []
        for ingredient in ingredients:
            normalized = normalize_ingredient_name(ingredient)
            items.append({
                "session_id": session_id,
                "ingredient": json.loads(ingredient.json()),
                "normalized_name": normalized
            })
        
        result = supabase.from_("grocery_items").insert(items).execute()
        return [GroceryItemOut(**item) for item in result.data]

    @staticmethod
    async def get_grocery_list(session_id: str, purchased: Optional[bool] = None) -> List[GroceryItemOut]:
        """Retrieve grocery items with purchase filter"""
        query = supabase.from_("grocery_items") \
            .select("*") \
            .eq("session_id", session_id)
        
        if purchased is not None:
            query = query.eq("purchased", purchased)
        
        result = query.order("created_at", desc=True).execute()
        return [GroceryItemOut(**item) for item in result.data]

    @staticmethod
    async def toggle_purchased(item_id: int, session_id: str) -> GroceryItemOut:
        """Mark item as purchased/unpurchased"""
        # Verify ownership first
        item = supabase.from_("grocery_items") \
            .select("*") \
            .eq("id", item_id)\
            .eq("session_id", session_id)\
            .single()\
            .execute()
        
        if not item.data:
            raise ValueError("Item not found in your grocery list")
        
        result = supabase.from_("grocery_items") \
            .update({"purchased": not item.data["purchased"]}) \
            .eq("id", item_id) \
            .execute()
        
        return GroceryItemOut(**result.data[0])

    @staticmethod
    async def remove_grocery_item(item_id: int, session_id: str) -> bool:
        """Delete item from grocery list"""
        # Verify ownership
        exists = supabase.from_("grocery_items") \
            .select("id") \
            .eq("id", item_id)\
            .eq("session_id", session_id)\
            .maybe_single()\
            .execute()
        
        if not exists.data:
            return False
        
        supabase.from_("grocery_items") \
            .delete() \
            .eq("id", item_id) \
            .execute()
        
        return True