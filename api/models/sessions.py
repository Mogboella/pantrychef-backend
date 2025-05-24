import datetime
from typing import List
from pydantic import BaseModel


class SessionData(BaseModel):
    pantry_items: List[str] = []
    dietary_restrictions: List[str] = []
    preferred_cuisines: List[str] = []


class SessionCreate(BaseModel):
    session_data: SessionData
    expires_at: datetime


class SessionDB(SessionCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
