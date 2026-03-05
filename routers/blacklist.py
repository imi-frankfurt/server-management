from fastapi import APIRouter, Depends, Depends
from requests import Session
from core.dependencies import get_current_user, require_role
from db import models
from db.database import getSession
from services.blacklist_service import add_to_blacklist_db, get_blacklist_db
from schemas.serialized_models import BlacklistEntrySerialized
router = APIRouter(
        prefix="/api",
        tags=["Blacklist Operations"]
)


@router.get("/blacklist", status_code=200)
def get_blacklist(session: Session = Depends(getSession),user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_blacklist_db(session)

@router.post("/blacklist", status_code=201)
def add_to_blacklist(blacklist: BlacklistEntrySerialized, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role"))):
    return add_to_blacklist_db(blacklist, session)