from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.dependencies import get_current_user, require_role
from db.database import getSession
from services.blacklist_service import add_to_blacklist_db, get_blacklist_db, get_blacklist_by_id, remove_from_blacklist_db
from schemas.serialized_models import BlacklistEntrySerialized, BlacklistUnassignSerialized
router = APIRouter(
        prefix="/api",
        tags=["Blacklist Operations"]
)


@router.get("/blacklist", status_code=200)
def get_blacklists(session: Session = Depends(getSession),user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_blacklist_db(session)

@router.post("/blacklist", status_code=201)
def add_to_blacklist(blacklist: BlacklistEntrySerialized, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role"))):
    return add_to_blacklist_db(blacklist, session)

@router.delete("/blacklist/unassign", status_code=200)
def unassign_from_blacklist(
    payload: BlacklistUnassignSerialized,
    session: Session = Depends(getSession),
    user: dict = Depends(get_current_user),
    _roles = Depends(require_role("admin-role"))
):
    return remove_from_blacklist_db(session, payload.username, payload.server_id)

@router.get("/blacklist/{blacklist_id:int}", status_code=200)
def get_blacklist(blacklist_id: int, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_blacklist_by_id(session, blacklist_id)