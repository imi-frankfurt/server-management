from fastapi import APIRouter, Request, Depends, status, Response
from core.dependencies import get_current_user, require_role
from services.user_service import sync_disabled_users_local
from db.database import getSession
from sqlalchemy.orm import Session
    

router = APIRouter(
        prefix="/api",
        tags=["Restricted Operations"]
)

@router.get("/restricted/sync", status_code=status.HTTP_200_OK)
def sync_disabled_users(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return sync_disabled_users_local(session)