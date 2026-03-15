from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, require_role
from db.database import getSession
from services.activity_log_service import get_activity_status


router = APIRouter(
    prefix="/api",
    tags=["Activity Logs"],
)


@router.get("/activity/status", status_code=status.HTTP_200_OK)
def get_last_activity(
    session: Session = Depends(getSession),
    user: dict = Depends(get_current_user),
    _roles=Depends(require_role("read-only-role")),
):
    return get_activity_status(session)
