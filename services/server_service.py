from fastapi import APIRouter, FastAPI, Request, Depends, HTTPException, Response, status
from core.shared_utilities import check_duplicate, success_response, error_response
from db import models
from db.database import getSession
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized
from core.shared_utilities import check_duplicate, record_exists
from datetime import datetime
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
    try:
        servers = session.query(models.Server).all()
        server_list = []
        for server in servers:
            aliases = session.query(models.Alias).filter(models.Alias.server_id == server.id).all()
            alias_list = [al.alias for al in aliases]

            server_list.append({
                "id": server.id,
                "name": server.name,
                "ip": server.ip,
                "aliases": alias_list,
                "created_at": server.created_at,
                "updated_at": server.updated_at
            })
        return success_response(
            data=server_list,
            message="Servers retrieved successfully"
        )
    except Exception as e:
        return error_response(message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_server_by_id(server_id: int, session: Session):
    try:
        server = session.query(models.Server).filter(models.Server.id == server_id).first()
        if server is None:
            return error_response(message="Server not found", status_code=status.HTTP_404_NOT_FOUND)
        # Check if server has any aliases
        aliases = session.query(models.Alias).filter(models.Alias.server_id == server_id).all()
        if aliases:
            alias_list = [alias.alias for alias in aliases]
        else:
            alias_list = []
        return success_response(data={"id": server.id, "name": server.name, "ip": server.ip, "aliases": alias_list, "created_at": server.created_at, "updated_at": server.updated_at}, message="Server retrieved successfully")
    except Exception as e:
        return error_response(message=str(e))

def update_server_by_id(server_id: int, server: ServerSerialized, session: Session):
    try:
        existing_server = session.query(models.Server).filter(models.Server.id == server_id).first()
        if not existing_server:
            return error_response(message="Server not found", status_code=status.HTTP_404_NOT_FOUND)
        
        # Check for duplicate name or IP (excluding current server)
        if server.name != existing_server.name and check_duplicate(session, models.Server, name=server.name):
            return error_response(message="Server with this name already exists", status_code=status.HTTP_409_CONFLICT)
        if server.ip != existing_server.ip and check_duplicate(session, models.Server, ip=server.ip):
            return error_response(message="Server with this IP already exists", status_code=status.HTTP_409_CONFLICT)
        
        # Update server fields
        existing_server.name = server.name
        existing_server.ip = server.ip
        existing_server.updated_at = datetime.now()
        
        # Delete old aliases
        session.query(models.Alias).filter(models.Alias.server_id == server_id).delete()
        
        # Add new aliases
        new_alias_objs = []
        if server.alias:
            for alias in server.alias:
                if check_duplicate(session, models.Alias, alias=alias):
                    return error_response(message=f"Alias '{alias}' already exists", status_code=status.HTTP_409_CONFLICT)
                new_alias_objs.append(models.Alias(alias=alias, server_id=existing_server.id))
        
        for alias_obj in new_alias_objs:
            session.add(alias_obj)
        
        session.commit()
        session.refresh(existing_server)
        
        # Get updated aliases as strings for response
        alias_list = [alias.alias for alias in new_alias_objs]
        
        return success_response(data={"id": existing_server.id, "name": existing_server.name, "ip": existing_server.ip, "aliases": alias_list}, message="Server updated successfully")
    except Exception as e:
        return error_response(message=str(e))

def delete_server_by_id(server_id: int, session: Session):
    try:
        existing_server = session.query(models.Server).filter(models.Server.id == server_id).first()
        if not existing_server:
            return error_response(message="Server not found", status_code=status.HTTP_404_NOT_FOUND)
        
        session.delete(existing_server)
        session.commit()
        
        return success_response(message=f"Server '{existing_server.name}' deleted successfully")
    except Exception as e:
        return error_response(message=str(e))