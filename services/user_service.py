from fastapi import Depends, HTTPException, Response, status
from keycloak import KeycloakOpenIDConnection
from keycloak import KeycloakAdmin
import os
from dotenv import load_dotenv
from core.shared_utilities import check_duplicate, error_response, success_response
from db import models
from sqlalchemy.orm import Session
from schemas.serialized_models import UserAssignmentSerialized

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
    except Exception as e:
        error_response(f"Failed to fetch users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def get_users_local_db(session: Session):
    try:
        users = session.query(models.User).all()
        user_list = []
        
        for user in users:
            # Get public keys for this user
            pubkeys = session.query(models.PublicKey).filter(models.PublicKey.user_id == user.id).all()
            pubkey_list = [pk.key_content for pk in pubkeys]
            
            # Get assigned servers count
            assigned_servers_count = len(user.servers)
            
            user_list.append({
                "id": user.id,
                "keycloak_id": user.keycloak_id,
                "username": user.username,
                "pubKey": pubkey_list,
                "assigned_servers_count": assigned_servers_count,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            })
        
        return user_list
    except Exception as e:
        error_response(f"Failed to fetch local users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_user_by_id(session: Session, user_id: str):
    try:
        user = session.query(models.User).filter(models.User.keycloak_id == user_id).first()
        if not user:
            error_response("User not found", status.HTTP_404_NOT_FOUND)
        
        # Get all public keys for this user
        pubkeys = session.query(models.PublicKey).filter(models.PublicKey.user_id == user.id).all()
        pubkey_list = [pk.key_content for pk in pubkeys]
        
        # Get all servers assigned to this user
        assigned_servers = []
        for server in user.servers:  # Using the relationship defined in models
            assigned_servers.append({
                "id": server.id,
                "name": server.name,
                "ip": server.ip,
                "created_at": server.created_at,
                "updated_at": server.updated_at
            })
        
        return {
            "id": user.id,
            "keycloak_id": user.keycloak_id,
            "username": user.username,
            "pubKey": pubkey_list,
            "assigned_servers": assigned_servers,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    except Exception as e:
        error_response(f"Failed to fetch user: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def sync_users(session: Session):
    try:
        added_users = []
        updated_users = []
        
        # Get All users from Keycloak
        keycloak_users = keycloak_admin.get_users({})
        
        # Process each Keycloak user
        for kc_user in keycloak_users:
            kc_id = kc_user["id"]
            kc_username = kc_user["username"]
            
            # Extract all pubKeys from Keycloak attributes (can be multiple)
            kc_pubkeys = []
            if "attributes" in kc_user and "pubKey" in kc_user["attributes"]:
                pubkey_data = kc_user["attributes"]["pubKey"]
                if isinstance(pubkey_data, list):
                    kc_pubkeys = [pk for pk in pubkey_data if pk]  # Filter out empty strings
                elif isinstance(pubkey_data, str) and pubkey_data:
                    kc_pubkeys = [pubkey_data]
            
            # Find if user exists in local DB
            db_user = session.query(models.User).filter(models.User.keycloak_id == kc_id).first()
            
            if not db_user:
                # User doesn't exist - add new user
                new_user = models.User(keycloak_id=kc_id, username=kc_username)
                session.add(new_user)
                session.flush()  # Get the user ID
                
                # Add all public keys
                for kc_pubkey in kc_pubkeys:
                    new_pubkey = models.PublicKey(key_content=kc_pubkey, user_id=new_user.id)
                    session.add(new_pubkey)
                
                added_users.append({"username": kc_username, "keycloak_id": kc_id, "pubkeys_count": len(kc_pubkeys)})
                print(f"Added new user: {kc_username} with {len(kc_pubkeys)} public key(s)")
            else:
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
                    print(f"Added public key for user: {kc_username}")
                
                # Remove old keys
                for pubkey in existing_pubkeys:
                    if pubkey.key_content in keys_to_remove:
                        session.delete(pubkey)
                        changes.append(f"removed key")
                        print(f"Removed public key for user: {kc_username}")
                
                if changes:
                    updated_users.append({
                        "username": kc_username,
                        "changes": changes,
                        "keys_added": len(keys_to_add),
                        "keys_removed": len(keys_to_remove)
                    })
        
        session.commit()
        
        if len(added_users) > 0 or len(updated_users) > 0:
            return {
                "added_users": added_users,
                "updated_users": updated_users
            }
        return {"message": "All users are already synchronized"}
    except Exception as e:
        session.rollback()
        error_response(f"Failed to synchronize users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def assign_user_to_server(server_user: UserAssignmentSerialized, session: Session):
    try:
        user = session.query(models.User).filter(models.User.id == server_user.user_id).first()
        server = session.query(models.Server).filter(models.Server.id == server_user.server_id).first()
        
        if not user:
            error_response("User not found", status.HTTP_404_NOT_FOUND)
        
        if not server:
            error_response("Server not found", status.HTTP_404_NOT_FOUND)
        
        # Check if association already exists
        association = session.query(models.user_server).filter(
            models.user_server.c.user_id == server_user.user_id,
            models.user_server.c.server_id == server_user.server_id
        ).first()
        
        if association:
            error_response("User is already assigned to this server", status.HTTP_400_BAD_REQUEST)
        
        # Create association
        create_association = models.user_server.insert().values(user_id=server_user.user_id, server_id=server_user.server_id, primary_user=server_user.primary_user)
        session.execute(create_association)
        session.commit()
        return {"message": "User assigned to server successfully"}
    except Exception as e:
        session.rollback()
        error_response(f"Failed to assign user to server: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def unassign_user_from_server(user_id: int, server_id: int, session: Session):
    """
    Remove a user's access to a server by deleting the association.
    """
    try:
        user = session.query(models.User).filter(models.User.id == user_id).first()
        server = session.query(models.Server).filter(models.Server.id == server_id).first()
        
        if not user:
            error_response("User not found", status.HTTP_404_NOT_FOUND)
        
        if not server:
            error_response("Server not found", status.HTTP_404_NOT_FOUND)
        
        # Check if association exists
        association = session.query(models.user_server).filter(
            models.user_server.c.user_id == user_id,
            models.user_server.c.server_id == server_id
        ).first()
        
        if not association:
            error_response("User is not assigned to this server", status.HTTP_404_NOT_FOUND)
        
        # Delete association
        delete_association = models.user_server.delete().where(
            models.user_server.c.user_id == user_id,
            models.user_server.c.server_id == server_id
        )
        session.execute(delete_association)
        session.commit()
        return {"message": "User removed from server successfully"}
    except Exception as e:
        session.rollback()
        error_response(f"Failed to remove user from server: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)