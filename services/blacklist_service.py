from fastapi import HTTPException, status
from core.shared_utilities import error_response, success_response, check_duplicate
from db import models
from sqlalchemy.orm import Session
from schemas.serialized_models import BlacklistEntrySerialized

def get_blacklist_db(session: Session):
    try:
        blacklist_users = session.query(models.IgnoredUser).all()
        blacklist_list = []
        for item in blacklist_users:
            servers = session.query(models.Server).filter(models.Server.id == item.server_id).all()
            server_list = [sv.id for sv in servers] if servers else []
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

def add_to_blacklist_db(blacklist : BlacklistEntrySerialized, session: Session):
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
        session.commit()
        return {"id": new_blacklist_entry.id, "username": new_blacklist_entry.username, "server_id": new_blacklist_entry.server_id, "created_at": new_blacklist_entry.created_at, "updated_at": new_blacklist_entry.updated_at}
    except Exception as e:
        error_response(f"Failed to add user to blacklist: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)