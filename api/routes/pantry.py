import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from api.core.database import get_supabase
from api.dependecies import get_session_id
from api.models.schemas import GroceryItemOut, Ingredient, PantryItem, PantryItemOut
from api.services.grocery import GroceryService
from api.services.pantry import PantryService
from api.services.session import SessionService

logger = logging.getLogger(__name__)

router = APIRouter()

session_service = SessionService()
pantry_service = PantryService()
grocery_service = GroceryService()

supabase = get_supabase()

@router.post("/", response_model=PantryItemOut)
async def add_pantry_item(
    item: PantryItem, 
    session_id: str = Depends(get_session_id)
    ):
    try:
        return await pantry_service.add_pantry_item(item, session_id)
    except Exception as e:
        raise HTTPException(400, detail=str(e))

@router.get("/", response_model=List[PantryItemOut])
async def get_pantry(
    session_id: str = Depends(get_session_id),
    expiring_soon: bool = False
):
    items = await pantry_service.get_pantry_items(session_id)
    if expiring_soon:
        items = [i for i in items if i.get("days_remaining") is not None and i["days_remaining"] <= 3]
    return items

@router.delete("/{item_id}")
async def delete_pantry_item(
    item_id: int,
    session_id: str = Depends(get_session_id)
    ):
    success = await pantry_service.remove_pantry_item(item_id, session_id)
    return {"deleted": success}

@router.post("/grocery", response_model=List[GroceryItemOut])
async def add_grocery_items(
    ingredients: List[Ingredient],
    session_id: str = Depends(get_session_id)
):
    """Add items to grocery list"""
    try:
        return await grocery_service.add_to_grocery(session_id, ingredients)
    except Exception as e:
        raise HTTPException(400, detail=str(e))

@router.get("/grocery", response_model=List[GroceryItemOut])
async def get_grocery(
    session_id: str = Depends(get_session_id),
    purchased: Optional[bool] = None
):
    """Get grocery list with optional purchased filter"""
    return await grocery_service.get_grocery_list(session_id, purchased)

@router.patch("/grocery/{item_id}/toggle", response_model=GroceryItemOut)
async def toggle_grocery_item(
    item_id: int,
    session_id: str = Depends(get_session_id)
):
    """Toggle purchased status"""
    try:
        return await grocery_service.toggle_purchased(item_id, session_id)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))

@router.delete("/grocery/{item_id}")
async def delete_grocery_item(
    item_id: int,
    session_id: str = Depends(get_session_id)
):
    """Remove item from grocery list"""
    success = await grocery_service.remove_grocery_item(item_id, session_id)
    if not success:
        raise HTTPException(404, detail="Item not found")
    return {"deleted": True}