from fastapi import APIRouter, Request, Depends, status, Response
from db import models
from db.database import getSession
from core.dependencies import get_current_user, require_role
from sqlalchemy.orm import Session
from services.user_service import get_users_local_db, sync_users, get_user_by_id, assign_user_to_server, unassign_user_from_server, update_user_by_id
from schemas.serialized_models import UserSerialized, UserAssignmentSerialized, UserUpdateSerialized, UserUnassignmentSerialized
router = APIRouter(
        prefix="/api",
        tags=["CRUD Operations"]
)


@router.get("/user", status_code=status.HTTP_200_OK)
def get_users(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_users_local_db(session)

@router.get("/user/sync", status_code=status.HTTP_200_OK)
def fetch_from_keycloak(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role"))):
    return sync_users(session)

@router.post("/user/assign", status_code=status.HTTP_200_OK)
def assign_user(server_user : UserAssignmentSerialized, request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role"))):
    return assign_user_to_server(server_user, session)

@router.post("/user/unassign", status_code=status.HTTP_200_OK)
def unassign_user_from_server_endpoint(server_user: UserUnassignmentSerialized, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role"))):
    return unassign_user_from_server(server_user, session)

@router.get("/user/{user_id}", status_code=status.HTTP_200_OK)
def get_user(user_id: str, request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_user_by_id(session, user_id)

@router.put("/user/{user_id}", status_code=status.HTTP_200_OK)
def update_user(user_id: str, user_data: UserUpdateSerialized, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role"))):
    return update_user_by_id(session, user_data, user_id)