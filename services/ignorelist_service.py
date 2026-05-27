from fastapi import HTTPException, status
from core.shared_utilities import error_response, success_response, check_duplicate
from db import models
from sqlalchemy.orm import Session
from schemas.serialized_models import IgnoreListEntrySerialized, IgnoreListUnassignSerialized
from services.activity_log_service import create_activity_log

def get_ignorelist_db(session: Session):
    try:
        ignorelist_users = session.query(models.IgnoredUser).all()
        ignorelist_list = []
        for item in ignorelist_users:
            servers = session.query(models.Server).filter(models.Server.id == item.server_id).all()
            server_list = [sv.name for sv in servers] if servers else []
            ignorelist_list.append({
                "id": item.id,
                "username": item.username,
                "servers": server_list,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            })
        return ignorelist_list
    except Exception as e:
        error_response(f"Failed to fetch ignorelist: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def add_to_ignorelist_db(ignorelist : IgnoreListEntrySerialized, session: Session, actor: str | None = None):
    try:
        # Check if the server exists
        existing_server = session.query(models.Server).filter(models.Server.id == ignorelist.server_id).first()
        if not existing_server:
            error_response("Server not found", status.HTTP_404_NOT_FOUND)
        # Check if the user is already in the ignorelist
        if check_duplicate(session, models.IgnoredUser, username=ignorelist.username, server_id=ignorelist.server_id):
            error_response("User is already in the ignorelist for this server", status.HTTP_409_CONFLICT)
        
        new_ignorelist_entry = models.IgnoredUser(username=ignorelist.username, server_id=ignorelist.server_id)
        session.add(new_ignorelist_entry)
        create_activity_log(
            session,
            action="post",
            actor=actor,
            resource="ignorelist",
            details=f"server_id={ignorelist.server_id};server_name={existing_server.name};server_ip={existing_server.ip};username={ignorelist.username}",
        )
        session.commit()
        return {"id": new_ignorelist_entry.id, "username": new_ignorelist_entry.username, "server_id": new_ignorelist_entry.server_id, "created_at": new_ignorelist_entry.created_at, "updated_at": new_ignorelist_entry.updated_at}
    except Exception as e:
        error_response(f"Failed to add user to ignorelist: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_ignorelist_by_id(session: Session, ignorelist_id: int):
    try:
        ignorelist_entry = session.query(models.IgnoredUser).filter(models.IgnoredUser.id == ignorelist_id).first()
        if not ignorelist_entry:
            error_response("ignorelist entry not found", status.HTTP_404_NOT_FOUND)
        ignorelist_list = []
        servers = session.query(models.Server).filter(models.Server.id == ignorelist_entry.server_id).all()
        server_list = [sv.name for sv in servers] if servers else []
        ignorelist_list.append({
            "id": ignorelist_entry.id,
            "username": ignorelist_entry.username,
            "servers": server_list,
            "created_at": ignorelist_entry.created_at,
            "updated_at": ignorelist_entry.updated_at
        })
        return ignorelist_list
    except Exception as e:
        error_response(f"Failed to fetch ignorelist entry: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def remove_from_ignorelist_db(ignorelist: IgnoreListUnassignSerialized, session: Session, actor: str | None = None):
    try:
        ignorelist_entry = session.query(models.IgnoredUser).filter(
            models.IgnoredUser.username == ignorelist.username,
            models.IgnoredUser.server_id == ignorelist.server_id
        ).first()
        if not ignorelist_entry:
            error_response("ignorelist entry not found", status.HTTP_404_NOT_FOUND)
        
        existing_server = session.query(models.Server).filter(models.Server.id == ignorelist.server_id).first()
        server_name = existing_server.name if existing_server else "Unknown"
        server_ip = existing_server.ip if existing_server else "Unknown"

        session.delete(ignorelist_entry)
        create_activity_log(
            session,
            action="delete",
            actor=actor,
            resource="ignorelist",
            details=f"server_id={ignorelist.server_id};server_name={server_name};server_ip={server_ip};username={ignorelist.username}",
        )
        session.commit()
        return success_response("User removed from ignorelist successfully")
    except Exception as e:
        error_response(f"Failed to remove user from ignorelist: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)