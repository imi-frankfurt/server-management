from fastapi import Depends, HTTPException, Response, status
from keycloak import KeycloakOpenIDConnection
from keycloak import KeycloakAdmin
import os
from dotenv import load_dotenv
from core.shared_utilities import check_duplicate, error_response, success_response
from db import models
from db.database import getSession
from sqlalchemy.orm import Session

from schemas.serialized_models import UserSerialized

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


def fetch_users():
    try:
        users = keycloak_admin.get_users({})
        user_list = [{"userid": user["id"], "name": user["username"]} for user in users]
        return success_response(data=user_list, message="Users fetched successfully")
    except Exception as e:
        error_response(f"Failed to fetch users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)
    

def fetch_user_by_id(user_id: str):
    try:
        user = keycloak_admin.get_user(user_id)
        user_info = {"userid": user["id"], "name": user["username"]}
        return success_response(data=user_info, message="User fetched successfully")
    except Exception as e:
        error_response(f"Failed to fetch user: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def check_user_exists(user_id: str):
    try:
        user = keycloak_admin.get_user(user_id)
        return True
    except Exception as e:
        return False
    
def check_user_local(session: Session, user_id: str):
    # Find from Keycloak ID and check if it exist in the local database
    return session.query(models.User).filter(models.User.keycloak_id == user_id).first() is not None

def get_all_users_local(session: Session):
    users = session.query(models.User).all()
    user_list = [{"id": user.id, "keycloak_id": user.keycloak_id, "username": user.username, "created_at": user.created_at, "updated_at": user.updated_at} for user in users]
    return success_response(data=user_list, message="Users fetched successfully from local database")

def sync_users(session: Session):
    try:
        missing_users = []
        session = getSession()
        # Get All users from DB
        db_users = session.query(models.User).all()
        # Get All users from Keycloak
        keycloak_users = keycloak_admin.get_users({})
        # Compare and find the missing users in the local database
        for kc_user in keycloak_users:
            if not any(db_user.keycloak_id == kc_user["id"] for db_user in db_users):
                new_user = models.User(keycloak_id=kc_user["id"], username=kc_user["username"])
                missing_users.append(new_user)
                add_user_to_local_db(session, kc_user["id"])

        if len(missing_users) > 0:
           return success_response(data={"added_users": missing_users}, message="All users synchronized successfully")
        return success_response(message="All users are already synchronized")
    except Exception as e:
        error_response(f"Failed to synchronize users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def add_user_to_local_db(session: Session, user_id: str):
    try:
        kc_user = keycloak_admin.get_user(user_id)
        if not kc_user:
            error_response("User not found in Keycloak", status.HTTP_404_NOT_FOUND)

        if check_duplicate(session, models.User, keycloak_id=kc_user["id"]):
            error_response("User already exists in local database", status.HTTP_409_CONFLICT)

        new_user = models.User(keycloak_id=kc_user["id"], username=kc_user["username"])
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return True
    except Exception as e:
        return False
    
def create_user(user: UserSerialized, response: Response, session: Session = Depends(getSession)):
    if check_duplicate(session, models.User, keycloak_id=user.keycloak_id):
        error_response("User with this keycloak_id already exists", status.HTTP_409_CONFLICT)

    # Add to User Table
    new_user = models.User(keycloak_id=user.keycloak_id, username=user.username)

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    response.status_code = status.HTTP_201_CREATED
    response.headers["Location"] = f"/api/user/{new_user.id}"
    return response