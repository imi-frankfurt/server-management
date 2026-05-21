from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.dependencies import get_current_user, require_role, require_csrf_token
from db.database import getSession
from services.ignorelist_service import add_to_ignorelist_db, get_ignorelist_db, get_ignorelist_by_id, remove_from_ignorelist_db
from schemas.serialized_models import IgnoreListEntrySerialized, IgnoreListUnassignSerialized
router = APIRouter(
        prefix="/api",
        tags=["Ignorelist Operations"]
)
@router.get("/ignorelist", status_code=200)
def get_ignorelists(session: Session = Depends(getSession),user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_ignorelist_db(session)

@router.post("/ignorelist", status_code=201)
def add_to_ignorelist(ignorelist: IgnoreListEntrySerialized, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role")), _csrf = Depends(require_csrf_token)):
    username = user.get('preferred_username', 'Unknown') if user else "Unknown"
    return add_to_ignorelist_db(ignorelist, session, actor=username)

@router.delete("/ignorelist/unassign", status_code=200)
def unassign_from_ignorelist(
    payload: IgnoreListUnassignSerialized,
    session: Session = Depends(getSession),
    user: dict = Depends(get_current_user),
    _roles = Depends(require_role("admin-role")),
    _csrf = Depends(require_csrf_token)
):
    username = user.get('preferred_username', 'Unknown') if user else "Unknown"
    return remove_from_ignorelist_db(payload, session, actor=username)

@router.get("/ignorelist/{ignorelist_id:int}", status_code=200)
def get_ignorelist(ignorelist_id: int, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_ignorelist_by_id(session, ignorelist_id)