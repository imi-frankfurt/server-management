from datetime import datetime
from fastapi import Depends, HTTPException, Response, status
from keycloak import KeycloakOpenIDConnection
from keycloak import KeycloakAdmin
import os
from dotenv import load_dotenv
from sentry_sdk import session
from core.shared_utilities import check_duplicate, error_response, success_response, validate_keycloak, check_local_id
from db import models
from sqlalchemy.orm import Session
from schemas.serialized_models import UserAssignmentSerialized, UserUpdateSerialized, UserUnassignmentSerialized
from services.activity_log_service import create_activity_log

load_dotenv()

keycloak_connection = KeycloakOpenIDConnection(
                        server_url=os.getenv("KEYCLOAK_URL"),
                        username=os.getenv("KEYCLOAK_ADMIN_USERNAME"),
                        password=os.getenv("KEYCLOAK_ADMIN_PASSWORD"),
                        realm_name=os.getenv("KEYCLOAK_CLIENT_REALM"),
                        user_realm_name=os.getenv("KEYCLOAK_CLIENT_REALM"),
                        client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
                        client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET"),
                        verify=True)

keycloak_admin = KeycloakAdmin(connection=keycloak_connection)


# Currently not needed, but can be used to fetch users directly from Keycloak without syncing to local DB
def fetch_users_keycloak():
    try:
        users = keycloak_admin.get_users({})
        user_list = []
        for user in users:
            user_data = {
                "userid": user["id"], 
                "name": user["username"]
            }
            # Extract pubKey and ensure it's always an array
            if "attributes" in user and "pubKey" in user["attributes"]:
                pubkey = user["attributes"]["pubKey"]
                user_data["pubKey"] = pubkey if isinstance(pubkey, list) else [pubkey]
            else:
                user_data["pubKey"] = []
            
            user_list.append(user_data)
        
        return user_list
    except HTTPException:
        raise
    except Exception as e:
        error_response(f"Failed to fetch users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_disabled_users_keycloak(session: Session):
    try:
            disabled_users = keycloak_admin.get_users({"enabled": "false"})
            all_users = get_users_local_db(session)
            should_disable = []
            for user in disabled_users:
                matching_local_user = next((u for u in all_users if u["keycloak_id"] == user["id"]), None)
                if matching_local_user:
                    should_disable.append({
                        "id": matching_local_user["id"],
                        "keycloak_id": matching_local_user["keycloak_id"],
                        "username": matching_local_user["username"]
                    })
            return should_disable
    except HTTPException as e:
        error_response(f"Failed to fetch disabled users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def sync_disabled_users_local(session: Session):
    try:  
        should_disable = get_disabled_users_keycloak(session)
        
        processed_users = []
        total_unassigned_servers = 0
        
        for user in should_disable:
            local_user = session.query(models.User).filter(models.User.id == user["id"]).first()
            
            if local_user:
                if not local_user.enabled and not local_user.servers:
                    continue

                servers_removed = 0
                affected_servers = []
                if local_user.servers:
                    servers_removed = len(local_user.servers)
                    total_unassigned_servers += servers_removed
                    
                    for server in local_user.servers:
                        unassign_user_from_server(
                            UserUnassignmentSerialized(user_id=user["id"], server_id=server.id), 
                            session, 
                            actor="restricted-sync"
                        )
                        affected_servers.append(server.name or server.ip)
                
                was_active = local_user.enabled
                if was_active:
                    deactivate_user_in_local_db(session, user["id"])
                
                processed_users.append({
                    "id": user["id"],
                    "username": user.get("username", "unknown"),
                    "action": "deactivated" if was_active else "servers_unassigned_only",
                    "servers_removed": servers_removed,
                    "affected_servers": affected_servers
                })

        return {
            "status": "success",
            "message": f"Processed {len(processed_users)} users." if processed_users else "No updates needed. All disabled users are already synced.",
            "summary": {
                "total_disabled_in_keycloak": len(should_disable),
                "actually_processed_locally": len(processed_users),
                "total_servers_unassigned": total_unassigned_servers
            },
            "details": {
                "processed_users": processed_users
            }
        }
        
    except Exception as e:
        error_response(f"Failed to fetch disabled users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)


def deactivate_user_in_local_db(session: Session, user_id: str):
    try:
        user = session.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.enabled = False
            session.commit()
    except Exception as e:
        error_response(f"Failed to deactivate user: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_users_local_db(session: Session):
    try:
        users = session.query(models.User).all()
        user_list = []
        
        for user in users:
            # Get public keys for this user
            pubkeys = session.query(models.PublicKey).filter(models.PublicKey.user_id == user.id).all()
            pubkey_list = [pk.key_content for pk in pubkeys]
            
            # Read assignments from relation table so we can expose assignment metadata.
            assignments = session.query(models.user_server).filter(
                models.user_server.c.user_id == user.id
            ).all()
            servers_by_id = {server.id: server for server in user.servers}
            assigned_servers = []
            for assignment in assignments:
                server = servers_by_id.get(assignment.server_id)
                if not server:
                    continue
                assigned_servers.append({
                    "id": server.id,
                    "name": server.name,
                    "ip": server.ip,
                    "primary_user": bool(getattr(assignment, "primary_user", False)),
                    "assigned_at": assignment.created_at,
                    "assignment_updated_at": assignment.updated_at
                })

            assigned_servers_count = len(assigned_servers)
            
            user_list.append({
                "id": user.id,
                "keycloak_id": user.keycloak_id,
                "enabled": user.enabled,
                "username": user.username,
                "pubKey": pubkey_list,
                "assigned_servers": assigned_servers,
                "assigned_servers_count": assigned_servers_count,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            })
        
        return user_list
    except HTTPException:
        raise
    except Exception as e:
        error_response(f"Failed to fetch local users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)


def resolve_user_identifier(session: Session, user_identifier: str | int):
    normalized_user_id = str(user_identifier).strip()
    if check_local_id(normalized_user_id):
        target_user = session.query(models.User).filter(models.User.id == int(normalized_user_id)).first()
    elif validate_keycloak(normalized_user_id):
        target_user = session.query(models.User).filter(models.User.keycloak_id == normalized_user_id).first()
    else:
        error_response("Invalid user ID or Keycloak ID format", status.HTTP_400_BAD_REQUEST)

    if not target_user:
        error_response("User not found", status.HTTP_404_NOT_FOUND)

    return target_user

def update_user_by_id(session: Session, assignment: UserUpdateSerialized, user_id: str, actor: str | None = None):
    try:
        # Validate whether the provided user_id is a valid Keycloak GUID format or User ID in local DB
        target_user = resolve_user_identifier(session, user_id)
        # Validate Server
        existing_server = session.query(models.Server).filter(models.Server.id == assignment.server_id).first()
        if not existing_server:
            error_response(message="Server not found", status_code=status.HTTP_404_NOT_FOUND)
        # Different Approach: Instead of checking for other primaries
        # If the user is being set as primary, we will update all other assignments for this server to primary_user=False
        if assignment.primary_user:
            session.query(models.user_server).filter(
                models.user_server.c.server_id == assignment.server_id
            ).update({models.user_server.c.primary_user: False})
        # Check if association already exists
        association = session.query(models.user_server).filter(
            models.user_server.c.user_id == target_user.id,
            models.user_server.c.server_id == assignment.server_id
        ).first()
        if association:
            # Update existing association
            update_stmt = models.user_server.update().where(
                models.user_server.c.user_id == target_user.id,
                models.user_server.c.server_id == assignment.server_id
            ).values(primary_user=assignment.primary_user, updated_at=datetime.now())
            session.execute(update_stmt)
        else:
            # Create new association
            create_stmt = models.user_server.insert().values(
                user_id=target_user.id,
                server_id=assignment.server_id,
                primary_user=assignment.primary_user,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.execute(create_stmt)
        create_activity_log(
            session,
            action="put",
            resource="user_assignment",
            actor=actor,
            details=f"user_id={target_user.id};server_id={assignment.server_id};server_name={existing_server.name};server_ip={existing_server.ip};primary_user={assignment.primary_user}",
        )
        session.commit()
        return {"message": "User assignment updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        error_response(message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
def get_user_by_id(session: Session, user_id: str):
    try:
        target_user = resolve_user_identifier(session, user_id)
        
        # Get all public keys for this user
        pubkeys = session.query(models.PublicKey).filter(models.PublicKey.user_id == target_user.id).all()
        pubkey_list = [pk.key_content for pk in pubkeys]
        
        # Get all servers assigned to this user including relation metadata.
        assignments = session.query(models.user_server).filter(
            models.user_server.c.user_id == target_user.id
        ).all()
        assignment_by_server_id = {assignment.server_id: assignment for assignment in assignments}

        # Get all servers assigned to this user
        assigned_servers = []
        for server in target_user.servers:  # Using the relationship defined in models
            assignment = assignment_by_server_id.get(server.id)
            assigned_servers.append({
                "id": server.id,
                "name": server.name,
                "ip": server.ip,
                "primary_user": bool(getattr(assignment, "primary_user", False)) if assignment else False,
                "assigned_at": assignment.created_at if assignment else None,
                "assignment_updated_at": assignment.updated_at if assignment else None,
                "created_at": server.created_at,
                "updated_at": server.updated_at
            })
        
        return {
            "id": target_user.id,
            "keycloak_id": target_user.keycloak_id,
            "username": target_user.username,
            "enabled": target_user.enabled,
            "pubKey": pubkey_list,
            "assigned_servers": assigned_servers,
            "created_at": target_user.created_at,
            "updated_at": target_user.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        error_response(f"Failed to fetch user: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def sync_users(session: Session, actor: str | None = None, log_unchanged: bool = True):
    try:
        added_users = []
        updated_users = []
        deleted_users = []
        processed_user_ids = set()
        
        # Get All users from Keycloak
        keycloak_users = keycloak_admin.get_users({})
        
        # Process each Keycloak user
        for kc_user in keycloak_users:
            kc_id = kc_user["id"]
            kc_username = kc_user["username"]

            
            kc_is_enabled = kc_user.get("enabled", True)
            reactivated_entry = None
            local_user = session.query(models.User).filter(models.User.keycloak_id == kc_id).first()            
            if local_user:
                processed_user_ids.add(local_user.id)
                
                # Szenario A: In Keycloak AKTIV, aber lokal noch DEAKTIVIERT -> Reaktivieren.
                # Kein continue: die Public Keys werden unten ebenfalls abgeglichen, da sie sich
                # waehrend der Deaktivierung in Keycloak geaendert haben koennen.
                if not local_user.enabled and kc_is_enabled:
                    local_user.enabled = True
                    reactivated_entry = {"username": kc_username, "keycloak_id": kc_id, "reactivated": True}
                    added_users.append(reactivated_entry)

                # Szenario B: In Keycloak DEAKTIVIERT, aber lokal noch AKTIV -> Deaktivieren
                elif local_user.enabled and not kc_is_enabled:
                    if local_user.servers:
                        for server in local_user.servers:
                            unassign_user_from_server(
                                UserUnassignmentSerialized(user_id=local_user.id, server_id=server.id), 
                                session, 
                                actor="restricted-sync"
                            )
                    local_user.enabled = False
                    session.commit()
                    
                    updated_users.append({
                        "username": kc_username, 
                        "action": "deactivated", 
                        "removed_from_servers": len(local_user.servers) if local_user.servers else 0
                    })
                    continue
                
                # Szenario C: In Keycloak DEAKTIVIERT und lokal DEAKTIVIERT -> Nichts tun,
                # es sei denn es sind noch Server zugewiesen (z.B. durch einen vorherigen Bug
                # oder eine manuelle Zuweisung nach der Deaktivierung) -> dann trotzdem entfernen
                elif not local_user.enabled and not kc_is_enabled:
                    if local_user.servers:
                        removed_from_servers = len(local_user.servers)
                        for server in local_user.servers:
                            unassign_user_from_server(
                                UserUnassignmentSerialized(user_id=local_user.id, server_id=server.id),
                                session,
                                actor="restricted-sync"
                            )
                        updated_users.append({
                            "username": kc_username,
                            "action": "servers_unassigned_only",
                            "removed_from_servers": removed_from_servers
                        })
                    continue
               
            
            # Extract all pubKeys from Keycloak attributes (can be multiple)
            kc_pubkeys = []
            if "attributes" in kc_user and "pubkey" in kc_user["attributes"]:
                pubkey_data = kc_user["attributes"]["pubkey"]
                if isinstance(pubkey_data, list):
                    kc_pubkeys = [pk for pk in pubkey_data if pk]  # Filter out empty strings
                elif isinstance(pubkey_data, str) and pubkey_data:
                    kc_pubkeys = [pubkey_data]
            if reactivated_entry:
                reactivated_entry["pubkeys_count"] = len(kc_pubkeys)
            
            # Find if user exists in local DB.
            # Primary match is keycloak_id, but if a Keycloak account was recreated,
            # username can stay the same while keycloak_id changes.
            db_user = session.query(models.User).filter(models.User.keycloak_id == kc_id).first()
            if not db_user:
                db_user = session.query(models.User).filter(models.User.username == kc_username).first()
                if db_user and db_user.keycloak_id != kc_id:
                    db_user.keycloak_id = kc_id
                    # print(f"Updated keycloak_id for existing user: {kc_username}")
            
            if not db_user:
                # User doesn't exist - add new user
                new_user = models.User(keycloak_id=kc_id, username=kc_username)
                session.add(new_user)
                session.flush()  # Get the user ID
                processed_user_ids.add(new_user.id)
                
                # Add all public keys
                for kc_pubkey in kc_pubkeys:
                    new_pubkey = models.PublicKey(key_content=kc_pubkey, user_id=new_user.id)
                    session.add(new_pubkey)
                
                added_users.append({"username": kc_username, "keycloak_id": kc_id, "pubkeys_count": len(kc_pubkeys)})
                # print(f"Added new user: {kc_username} with {len(kc_pubkeys)} public key(s)")
            else:
                processed_user_ids.add(db_user.id)
                # User exists - sync public keys
                existing_pubkeys = session.query(models.PublicKey).filter(
                    models.PublicKey.user_id == db_user.id
                ).all()
                
                # Get sets of key contents for comparison
                db_keys_set = {pk.key_content for pk in existing_pubkeys}
                kc_keys_set = set(kc_pubkeys)
                
                # Keys to add (in Keycloak but not in DB)
                keys_to_add = kc_keys_set - db_keys_set
                # Keys to remove (in DB but not in Keycloak)
                keys_to_remove = db_keys_set - kc_keys_set
                
                changes = []
                
                # Add new keys
                for key_content in keys_to_add:
                    new_pubkey = models.PublicKey(key_content=key_content, user_id=db_user.id)
                    session.add(new_pubkey)
                    changes.append(f"added key")
                    # print(f"Added public key for user: {kc_username}")
                
                # Remove old keys
                for pubkey in existing_pubkeys:
                    if pubkey.key_content in keys_to_remove:
                        session.delete(pubkey)
                        changes.append(f"removed key")
                        # print(f"Removed public key for user: {kc_username}")
                
                if changes:
                    db_user.updated_at = datetime.now()
                    updated_users.append({
                        "username": kc_username,
                        "changes": changes,
                        "keys_added": len(keys_to_add),
                        "keys_removed": len(keys_to_remove)
                    })

        # Remove users that no longer exist in Keycloak.
        # Keep only users processed from current Keycloak snapshot.
        local_users = session.query(models.User).all()
        for local_user in local_users:
            if local_user.id not in processed_user_ids:
                deleted_users.append({
                    "username": local_user.username,
                    "keycloak_id": local_user.keycloak_id
                })
                session.delete(local_user)

        has_changes = len(added_users) > 0 or len(updated_users) > 0 or len(deleted_users) > 0

        # Scheduled syncs pass log_unchanged=False so that no-op runs don't flood the activity log
        if has_changes or log_unchanged:
            create_activity_log(
                session,
                action="sync",
                resource="user",
                actor=actor,
                details=f"added={len(added_users)};updated={len(updated_users)};deleted={len(deleted_users)}",
            )
        
        session.commit()
        
        if has_changes:
            return {
                "added_users": added_users,
                "updated_users": updated_users,
                "deleted_users": deleted_users
            }
        return {"message": "All users are already synchronized"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        error_response(f"Failed to synchronize users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def assign_user_to_server(server_user: UserAssignmentSerialized, session: Session, actor: str | None = None):
    try:
        target_user = resolve_user_identifier(session, server_user.user_id)
        # print(f"Assigning user '{target_user.username}' to server ID {server_user.server_id} with primary_user={server_user.primary_user}")
        server = session.query(models.Server).filter(models.Server.id == server_user.server_id).first()

        if not server:
            error_response("Server not found", status.HTTP_404_NOT_FOUND)
        
        # Check if association already exists
        association = session.query(models.user_server).filter(
            models.user_server.c.user_id == target_user.id,
            models.user_server.c.server_id == server_user.server_id
        ).first()
        
        if association:
            error_response("User is already assigned to this server", status.HTTP_400_BAD_REQUEST)
        
        # Create association
        create_association = models.user_server.insert().values(
            user_id=target_user.id,
            server_id=server_user.server_id,
            primary_user=server_user.primary_user,
        )
        session.execute(create_association)
        create_activity_log(
            session,
            action="post",
            resource="user_assignment",
            actor=actor,
            details=f"user_id={target_user.id};server_id={server_user.server_id};server_name={server.name};server_ip={server.ip};primary_user={server_user.primary_user}",
        )
        session.commit()
        return {"message": "User assigned to server successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        error_response(f"Failed to assign user to server: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def unassign_user_from_server(server_user: UserUnassignmentSerialized, session: Session, actor: str | None = None):
    """
    Remove a user's access to a server by deleting the association.
    """
    try:
        target_user = resolve_user_identifier(session, server_user.user_id)
        server = session.query(models.Server).filter(models.Server.id == server_user.server_id).first()

        if not server:
            error_response("Server not found", status.HTTP_404_NOT_FOUND)
        
        # Check if association exists
        association = session.query(models.user_server).filter(
            models.user_server.c.user_id == target_user.id,
            models.user_server.c.server_id == server_user.server_id
        ).first()
        
        if not association:
            error_response("User is not assigned to this server", status.HTTP_404_NOT_FOUND)
        
        # Delete association
        delete_association = models.user_server.delete().where(
            models.user_server.c.user_id == target_user.id,
            models.user_server.c.server_id == server_user.server_id
        )
        session.execute(delete_association)
        create_activity_log(
            session,
            action="post",
            resource="user_unassign",
            actor=actor,
            details=f"user_id={target_user.id};server_id={server_user.server_id};server_name={server.name};server_ip={server.ip};primary_user={getattr(association, 'primary_user', False)}",
        )
        session.commit()
        return {"message": "User removed from server successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        error_response(f"Failed to remove user from server: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)