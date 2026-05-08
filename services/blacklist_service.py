from fastapi import HTTPException, status
from core.shared_utilities import error_response, success_response, check_duplicate
from db import models
from sqlalchemy.orm import Session
from schemas.serialized_models import BlacklistEntrySerialized, BlacklistUnassignSerialized
from services.activity_log_service import create_activity_log

def get_blacklist_db(session: Session):
    try:
        blacklist_users = session.query(models.IgnoredUser).all()
        blacklist_list = []
        for item in blacklist_users:
            servers = session.query(models.Server).filter(models.Server.id == item.server_id).all()
            server_list = [sv.name for sv in servers] if servers else []
            blacklist_list.append({
                "id": item.id,
                "username": item.username,
                "servers": server_list,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            })
        return blacklist_list
    except Exception as e:
        error_response(f"Failed to fetch blacklist: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def add_to_blacklist_db(blacklist : BlacklistEntrySerialized, session: Session, actor: str | None = None):
    try:
        # Check if the server exists
        existing_server = session.query(models.Server).filter(models.Server.id == blacklist.server_id).first()
        if not existing_server:
            error_response("Server not found", status.HTTP_404_NOT_FOUND)
        # Check if the user is already in the blacklist
        if check_duplicate(session, models.IgnoredUser, username=blacklist.username, server_id=blacklist.server_id):
            error_response("User is already in the blacklist for this server", status.HTTP_409_CONFLICT)
        
        new_blacklist_entry = models.IgnoredUser(username=blacklist.username, server_id=blacklist.server_id)
        session.add(new_blacklist_entry)
        create_activity_log(
            session,
            action="post",
            actor=actor,
            resource="blacklist",
            details=f"server_id={blacklist.server_id};server_name={existing_server.name};server_ip={existing_server.ip};username={blacklist.username}",
        )
        session.commit()
        return {"id": new_blacklist_entry.id, "username": new_blacklist_entry.username, "server_id": new_blacklist_entry.server_id, "created_at": new_blacklist_entry.created_at, "updated_at": new_blacklist_entry.updated_at}
    except Exception as e:
        error_response(f"Failed to add user to blacklist: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_blacklist_by_id(session: Session, blacklist_id: int):
    try:
        blacklist_entry = session.query(models.IgnoredUser).filter(models.IgnoredUser.id == blacklist_id).first()
        if not blacklist_entry:
            error_response("Blacklist entry not found", status.HTTP_404_NOT_FOUND)
        blacklist_list = []
        servers = session.query(models.Server).filter(models.Server.id == blacklist_entry.server_id).all()
        server_list = [sv.name for sv in servers] if servers else []
        blacklist_list.append({
            "id": blacklist_entry.id,
            "username": blacklist_entry.username,
            "servers": server_list,
            "created_at": blacklist_entry.created_at,
            "updated_at": blacklist_entry.updated_at
        })
        return blacklist_list
    except Exception as e:
        error_response(f"Failed to fetch blacklist entry: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def remove_from_blacklist_db(blacklist: BlacklistUnassignSerialized, session: Session, actor: str | None = None):
    try:
        blacklist_entry = session.query(models.IgnoredUser).filter(
            models.IgnoredUser.username == blacklist.username,
            models.IgnoredUser.server_id == blacklist.server_id
        ).first()
        if not blacklist_entry:
            error_response("Blacklist entry not found", status.HTTP_404_NOT_FOUND)
        session.delete(blacklist_entry)
        create_activity_log(
            session,
            action="delete",
            actor=actor,
            resource="blacklist",
            details=f"server_id={blacklist.server_id};server_name={blacklist.name};server_ip={blacklist.ip};username={blacklist.username}",
        )
        session.commit()
        return success_response("User removed from blacklist successfully")
    except Exception as e:
        error_response(f"Failed to remove user from blacklist: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)