from datetime import datetime, timedelta
import json
from typing import List
import uuid

from fastapi import HTTPException
from api.core.database import get_supabase
from api.core.rec_engine import get_recommendations
from api.models.sessions import SessionCreate, SessionData

supabase = get_supabase()


class SessionService:
    async def create_session(self, pantry_items: List[str]):
        """Create a new session with pantry items"""
        session_id = str(uuid.uuid4())
        session_data = SessionData(pantry_items=pantry_items)

        supabase.from_("sessions").insert(
            {
                "id": session_id,
                "session_data": json.loads(session_data.model_dump_json()),
                "expires_at": str(datetime.now() + timedelta(days=7)),
            }
        ).execute()

        # Use in recommendations
        recommendations = await get_recommendations(
            session_id=session_id, filters={"max_missing": 2}
        )

        return {
            "session_id": session_id,
            "expires_at": datetime.now() + timedelta(days=7),
        }

        # Store session
        # db_session = (
        #     await supabase.from_("sessions").insert(session.model_dump()).execute()
        # )
        # session_id = db_session.data[0]["id"]

    async def get_session(self, session_id: str):
        res = supabase.from_("sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        return res.data[0]
