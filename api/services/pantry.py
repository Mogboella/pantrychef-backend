from datetime import datetime, timezone
import hashlib
from typing import List, Optional

from api.core.database import get_supabase
from api.core.rec_engine import normalize_ingredient
from api.models.schemas import PantryItem, PantryItemOut
import logging

logger = logging.getLogger(__name__)
supabase = get_supabase()

def calculate_expiry_status(expiry: datetime) -> str:
    """
    Determine expiry status from a datetime.
    Returns: "expired", "expiring_soon", or "fresh"
    """
    if not expiry:
        return "unknown"
    
    days_remaining = (expiry - datetime.now()).days
    
    if days_remaining < 0:
        return "expired"
    elif days_remaining <= 3:
        return "expiring_soon"
    else:
        return "fresh"


from datetime import datetime

def calculate_expiry_status(expiry: Optional[datetime]) -> str:
    """
    Determine expiry status from a datetime.
    Returns: "expired", "expiring_soon", or "fresh"
    """
    if not expiry:
        return "unknown"
    
    now = datetime.now(timezone.utc)
    days_remaining = (expiry - now).days

    if days_remaining < 0:
        return "expired"
    elif days_remaining <= 3:
        return "expiring_soon"
    else:
        return "fresh"


def enrich_with_expiry(item: dict) -> dict:
    """Add expiry metadata"""
    expiry_raw = item.get("expiry_date")
    expiry = None

    if isinstance(expiry_raw, str):
        try:
            expiry = datetime.fromisoformat(expiry_raw)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
        except ValueError:
            expiry = None
    elif isinstance(expiry_raw, datetime):
        expiry = expiry if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    return {
        **item,
        "expiry_status": calculate_expiry_status(expiry),
        "days_remaining": (expiry - now).days if expiry else None
    }


class PantryService:
    @staticmethod
    async def get_pantry_items(session_id: str) -> List[PantryItemOut]:
        """Retrieve all items for a session with expiry status"""
        items = supabase.from_("pantry_items") \
            .select("*") \
            .eq("session_id", session_id) \
            .execute()
        
        return [enrich_with_expiry(item) for item in items.data]

    @staticmethod
    async def add_pantry_item(item: PantryItem, session_id: str) -> PantryItemOut:
        """Add item and invalidate recipe cache"""
        normalized = normalize_ingredient(item.ingredient)

        existing = supabase.from_("pantry_items") \
            .select("*") \
            .eq("session_id", session_id) \
            .eq("normalized_name", normalized) \
            .execute()

        if existing.data:
            raise Exception(f"Item '{item.ingredient.name}' already exists in pantry.")

        data = {
            **item.model_dump(),
            "session_id": session_id,
            "normalized_name": normalized,
        }

        # Convert expiry_date to ISO format if it exists
        if data.get("expiry_date") and isinstance(data["expiry_date"], datetime):
            data["expiry_date"] = data["expiry_date"].isoformat()

        db_item = supabase.from_("pantry_items").insert(data).execute()
        
        return PantryItemOut(**db_item.data[0])
    
    @staticmethod
    async def remove_pantry_item(item_id, session_id):
        try:
            supabase.table("pantry_items") \
            .delete() \
            .eq("session_id", session_id) \
            .eq("id", item_id)\
            .execute()
        except Exception as e:
            logger.error(f"Failed to update pantry item: {e}")
            return False