import logging
from typing import List


from fastapi import APIRouter

from api.core.database import get_supabase
from api.models.sessions import SessionData
from api.services.session import SessionService

logger = logging.getLogger(__name__)

router = APIRouter()

session_service = SessionService()

supabase = get_supabase()


@router.post("/", response_model=dict)
async def create_session(pantry_items: List[str]):
    """Create a new session with pantry items"""
    session_service = SessionService()
    return await session_service.create_session(pantry_items)
