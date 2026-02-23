from fastapi import APIRouter, FastAPI, Request, Depends, HTTPException, Response, status
from core.shared_utilities import check_duplicate, success_response, error_response
from db import models
from db.database import getSession
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized
from core.shared_utilities import check_duplicate, record_exists

def create_server(server: ServerSerialized, response: Response, session: Session = Depends(getSession)):
    if check_duplicate(session, models.Server, name=server.name):
        error_response("Server with this name already exists", status.HTTP_409_CONFLICT)

    if check_duplicate(session, models.Server, ip=server.ip):
        error_response("Server with this IP already exists", status.HTTP_409_CONFLICT)
    
    # Add to Server Table
    new_server = models.Server(ip=server.ip, name=server.name)

    session.add(new_server)
    session.commit()
    session.refresh(new_server)

    # Add to Alias Table
    alias_list =  []
    if server.alias:
        for alias in server.alias:
            if check_duplicate(session, models.Alias, alias=alias):
                error_response(f"Alias '{alias}' already exists", status.HTTP_409_CONFLICT)
            alias_list.append(models.Alias(alias=alias, server_id=new_server.id))        
    if len(alias_list) > 0:
        for alias in alias_list:
            session.add(alias)

    session.commit()
    response.status_code = status.HTTP_201_CREATED
    response.headers["Location"] = f"/api/server/{new_server.id}"
    return response

def get_all_servers(session: Session):
    servers = session.query(models.Server).all()
    return success_response(
        data=servers,
        message="Servers retrieved successfully"
    )
