from fastapi import APIRouter, Request, Depends, status, Response
from db import models
from db.database import getSession
from core.dependencies import get_current_user, require_role, require_csrf_token
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized
from services.server_service import create_server, get_all_servers, get_server_by_id, update_server_by_id, delete_server_by_id

router = APIRouter(
        prefix="/api",
        tags=["CRUD Operations"]
)


@router.get("/server", status_code=status.HTTP_200_OK)
def get_servers(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_all_servers(session)

@router.post("/server", status_code=status.HTTP_201_CREATED)
def create_server_endpoint(server: ServerSerialized, request: Request = None, response: Response = None, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role")), _csrf = Depends(require_csrf_token)):
    username = user.get('preferred_username', 'Unknown') if user else "Unknown"
    return create_server(server, response, session, actor=username)

@router.get("/server/{server_id}", status_code=status.HTTP_200_OK)
def get_server(server_id: int, request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_server_by_id(server_id, session)

@router.put("/server/{server_id}", status_code=status.HTTP_200_OK)
def update_server(server_id: int, server: ServerSerialized, request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role")), _csrf = Depends(require_csrf_token)):
    username = user.get('preferred_username', 'Unknown') if user else "Unknown"
    return update_server_by_id(server_id, server, session, actor=username)

@router.delete("/server/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(server_id: int, request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("admin-role")), _csrf = Depends(require_csrf_token)):
    username = user.get('preferred_username', 'Unknown') if user else "Unknown"
    delete_server_by_id(server_id, session, actor=username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
