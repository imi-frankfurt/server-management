from fastapi import APIRouter, Request, Depends, status
from db import models
from db.database import getSession
from core.dependencies import get_current_user, require_role
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized, HostAddressSerialized
from services.server_service import create_server, get_all_servers
from services.host_service import create_host_address
from core.shared_utilities import success_response

router = APIRouter()


@router.get("/servers", status_code=status.HTTP_200_OK)
def get_servers(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_all_servers(session)

@router.post("/create-server", status_code=status.HTTP_201_CREATED)
def create_server_endpoint(server: ServerSerialized, request: Request = None, session: Session = Depends(getSession)):
    return create_server(server, request, session)


@router.post("/create-host_address", status_code=status.HTTP_201_CREATED)
def create_host_address_endpoint(host_address: HostAddressSerialized, request: Request = None, session: Session = Depends(getSession)):
    return create_host_address(host_address, request, session)
