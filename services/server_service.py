from fastapi import APIRouter, FastAPI, Request, Depends, HTTPException, Response, status
from core.shared_utilities import check_duplicate, success_response, error_response
from db import models
from db.database import getSession
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized, HostAddressSerialized

def create_server(server: ServerSerialized, session: Session = Depends(getSession)):
    if check_duplicate(session, models.Server, alias=server.alias):
        error_response("Server with this alias already exists", status.HTTP_409_CONFLICT)
    new_server = models.Server(alias=server.alias)
    session.add(new_server)
    session.commit()
    return success_response(
        data={"id": new_server.id, "alias": new_server.alias},
        message=f"Server '{server.alias}' created successfully"
    )

def get_all_servers(session: Session):
    servers = session.query(models.Server).all()
    return success_response(
        data=servers,
        message="Servers retrieved successfully"
    )
