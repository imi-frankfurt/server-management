from fastapi import APIRouter, Request, Depends, status, Response
from db import models
from db.database import getSession
from core.dependencies import get_current_user, require_role
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized
from services.user_service import fetch_users, sync_users

router = APIRouter(
        prefix="/api",
        tags=["CRUD Operations"]
)


@router.get("/user", status_code=status.HTTP_200_OK)
def get_users(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return fetch_users()

@router.get("/user/check", status_code=status.HTTP_200_OK)
def get_users_local(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return sync_users(session)
    
