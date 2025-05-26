from datetime import datetime, timedelta
import json
from typing import List
import uuid

from fastapi import HTTPException
from api.core.database import get_supabase
from api.models.sessions import SessionCreate, SessionData
from api.services.recommendation import RecommendationService

supabase = get_supabase()


class SessionService:
    async def create_session(self, pantry_items: List[str]=[]):
        """Create a new session with pantry items"""
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=7)
        
        session_data = SessionData(
            pantry_items=pantry_items
        )

        supabase.from_("sessions").insert(
            {
                "id": session_id,
                "session_data": json.loads(session_data.model_dump_json()),
                "expires_at": str(datetime.now() + timedelta(days=7)),
            }
        ).execute()

        return {
            "session_id": session_id,
            "expires_at": datetime.now() + timedelta(days=7),
        }

    async def validate_session(session_id: str) -> bool:
        """Verify session exists and is active"""
        if not session_id:
            return False
        
        result = supabase.from_("sessions") \
            .select("expires_at") \
            .eq("id", session_id) \
            .gt("expires_at", datetime.now()) \
            .maybe_single() \
            .execute()
        
        if not result.data:
            return False
        
        return True

    async def refresh_session(session_id: str) -> datetime:
        """Extend session validity by 7 days from now"""
        new_expiry = datetime.now() + timedelta(days=7)
        supabase.from_("sessions") \
            .update({
                "expires_at": new_expiry,
            }) \
            .eq("id", session_id) \
            .execute()
        return new_expiry

    async def cleanup_expired_sessions():
        """Remove expired sessions and their associated data"""
        expired = supabase.from_("sessions") \
            .select("id") \
            .lt("expires_at", datetime.now()) \
            .execute()
        
        for session in expired.data:
            # Delete session
            supabase.from_("sessions") \
                .delete() \
                .eq("id", session["id"]) \
                .execute()

    async def get_session(self, session_id: str):
        res = supabase.from_("sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        return res.data[0]
