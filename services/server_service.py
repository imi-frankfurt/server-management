from fastapi import APIRouter, FastAPI, Request, Depends, HTTPException, Response, status
from core.shared_utilities import check_duplicate, success_response, error_response, validate_ip_address
from db import models
from db.database import getSession
from sqlalchemy.orm import Session
from schemas.serialized_models import ServerSerialized
from core.shared_utilities import check_duplicate
from datetime import datetime
from services.activity_log_service import create_activity_log


def create_server(server: ServerSerialized, response: Response, session: Session, actor: str | None = None):
    
    if not validate_ip_address(server.ip):
        error_response("Invalid IP address format", status.HTTP_400_BAD_REQUEST)
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

    create_activity_log(session, action="post", actor=actor, resource="server", details=f"server_id={new_server.id};server_name={new_server.name};server_ip={new_server.ip}")

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
                "alias": alias_list,
                "created_at": server.created_at,
                "updated_at": server.updated_at
            })
        return server_list
    except Exception as e:
        error_response(message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_server_by_id(server_id: int, session: Session):
    try:
        server = session.query(models.Server).filter(models.Server.id == server_id).first()
        if server is None:
            error_response(message="Server not found", status_code=status.HTTP_404_NOT_FOUND)
        # Check if server has any aliases
        aliases = session.query(models.Alias).filter(models.Alias.server_id == server_id).all()
        if aliases:
            alias_list = [alias.alias for alias in aliases]
        else:
            alias_list = []
        return {"id": server.id, "name": server.name, "ip": server.ip, "alias": alias_list, "created_at": server.created_at, "updated_at": server.updated_at}
    except Exception as e:
        error_response(message=str(e))

def update_server_by_id(server_id: int, server: ServerSerialized, session: Session, actor: str | None = None):
    try:
        if not validate_ip_address(server.ip):
            error_response("Invalid IP address format", status.HTTP_400_BAD_REQUEST)
        existing_server = session.query(models.Server).filter(models.Server.id == server_id).first()
        if not existing_server:
            error_response(message="Server not found", status_code=status.HTTP_404_NOT_FOUND)
        
        # Check for duplicate name or IP (excluding current server)
        if server.name != existing_server.name and check_duplicate(session, models.Server, name=server.name):
            error_response(message="Server with this name already exists", status_code=status.HTTP_409_CONFLICT)
        if server.ip != existing_server.ip and check_duplicate(session, models.Server, ip=server.ip):
            error_response(message="Server with this IP already exists", status_code=status.HTTP_409_CONFLICT)
        
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
                    error_response(message=f"Alias '{alias}' already exists", status_code=status.HTTP_409_CONFLICT)
                new_alias_objs.append(models.Alias(alias=alias, server_id=existing_server.id))
        
        for alias_obj in new_alias_objs:
            session.add(alias_obj)

        create_activity_log(session, action="put", actor=actor, resource="server", details=f"server_id={existing_server.id};server_name={existing_server.name};server_ip={existing_server.ip}")
        
        session.commit()
        session.refresh(existing_server)
        
        # Get updated aliases as strings for response
        alias_list = [alias.alias for alias in new_alias_objs]
        
        return {"id": existing_server.id, "name": existing_server.name, "ip": existing_server.ip, "alias": alias_list, "created_at": existing_server.created_at, "updated_at": existing_server.updated_at}
    except Exception as e:
        error_response(message=str(e))

def delete_server_by_id(server_id: int, session: Session, actor: str | None = None):
    try:
        existing_server = session.query(models.Server).filter(models.Server.id == server_id).first()
        if not existing_server:
            error_response(message="Server not found", status_code=status.HTTP_404_NOT_FOUND)
        
        session.delete(existing_server)
        create_activity_log(session, action="delete", actor=actor, resource="server", details=f"server_id={server_id};server_name={existing_server.name};server_ip={existing_server.ip}")
        session.commit()
        
        return None  # 204 No Content
    except Exception as e:
        error_response(message=str(e))