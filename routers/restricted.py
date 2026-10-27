from fastapi import APIRouter, HTTPException, Request, Depends, status, Response
from fastapi.security import APIKeyHeader
from core.dependencies import get_current_user, require_role
from services.user_service import sync_disabled_users_local
from core.scheduler import sync_lock
from db.database import getSession
from sqlalchemy.orm import Session
from core.limiter import limiter
from dotenv import load_dotenv
import os

load_dotenv()

api_scheme = APIKeyHeader(name="X-API-Key")

router = APIRouter(
        prefix="/api",
        tags=["Restricted Operations"]
)

@router.get("/restricted/sync", status_code=status.HTTP_200_OK)
@limiter.limit("1/5 minutes")
def sync_disabled_users(request: Request, session: Session = Depends(getSession), api_key: str = Depends(api_scheme)):
    if api_key != os.getenv("SYNC_API"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if not sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sync already in progress")
    try:
        return sync_disabled_users_local(session)
    finally:
        sync_lock.release()