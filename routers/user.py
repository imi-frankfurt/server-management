from fastapi import APIRouter, Request, Depends, status, Response
from db import models
from db.database import getSession
from core.dependencies import get_current_user, require_role
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized
from services.user_service import get_users_local_db, sync_users, get_user_by_id

router = APIRouter(
        prefix="/api",
        tags=["CRUD Operations"]
)


@router.get("/user", status_code=status.HTTP_200_OK)
def get_users(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_users_local_db(session)

@router.get("/user/sync", status_code=status.HTTP_200_OK)
def fetch_from_keycloak(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return sync_users(session)

@router.get("/user/{keycloak_id}", status_code=status.HTTP_200_OK)
def get_user(keycloak_id: str, request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_user_by_id(session, keycloak_id)
    
