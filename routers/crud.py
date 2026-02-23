from fastapi import APIRouter, Request, Depends, status, Response
from db import models
from db.database import getSession
from core.dependencies import get_current_user, require_role
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized
from services.server_service import create_server, get_all_servers
from core.shared_utilities import success_response, error_response

router = APIRouter(
        prefix="/api",
        tags=["CRUD Operations"]
)


@router.get("/server", status_code=status.HTTP_200_OK)
def get_servers(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_all_servers(session)

@router.post("/server", status_code=status.HTTP_201_CREATED)
def create_server_endpoint(server: ServerSerialized, request: Request = None, response: Response = None, session: Session = Depends(getSession)):
    return create_server(server, response, session)

@router.get("/server/{server_id}", status_code=status.HTTP_200_OK)
def get_server_by_id(server_id: int, request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    try:
        server = session.query(models.Server).filter(models.Server.id == server_id).first()
        # Check if server has any aliases
        aliases = session.query(models.Alias).filter(models.Alias.server_id == server_id).all()
        if aliases:
            alias_list = [alias.alias for alias in aliases]
        else:
            alias_list = []
        return success_response(data={"id": server.id, "name": server.name, "ip": server.ip, "aliases": alias_list, "created_at": server.created_at, "updated_at": server.updated_at}, message="Server retrieved successfully")
    except Exception as e:
        return error_response(message=e)
