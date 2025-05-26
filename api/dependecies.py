from fastapi import Depends, Header, HTTPException
from typing import Optional
from .services.session import SessionService as sessions

async def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_token: Optional[str] = Header(None, alias="Session-Token")  # Alternative
) -> str:
    """Dependency to validate and return session ID"""
    session_id = x_session_id or session_token
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="Session ID required in X-Session-ID header"
        )
    
    if not await sessions.validate_session(session_id):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session"
        )
    
    return session_id