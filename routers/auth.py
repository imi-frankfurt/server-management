from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from keycloak import KeycloakOpenID
from core.dependencies import get_current_user, get_user_roles, require_role
from core.shared_utilities import success_response, error_response
from dotenv import load_dotenv
import os
import json
import jwt
from typing import List

load_dotenv()
    
keycloak_openid = KeycloakOpenID(
    server_url=os.getenv("KEYCLOAK_URL"),
    client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
    realm_name=os.getenv("KEYCLOAK_REALM"),
    client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET")
)

router = APIRouter()


@router.get("/")
async def root():
    return success_response(message="API is running")

@router.get("/login")
async def login():
    auth_url = keycloak_openid.auth_url(redirect_uri="http://localhost:5000/callback", scope="openid profile email")
    return RedirectResponse(auth_url)

@router.get("/callback")
def callback(code: str, request: Request):
    try:
        token = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri="http://localhost:5000/callback"
        )
        
        user_info = keycloak_openid.userinfo(token['access_token'])

        decoded_token = jwt.decode(token['access_token'], options={"verify_signature": False})
        
        client_roles = decoded_token.get('resource_access', {}).get(os.getenv("KEYCLOAK_CLIENT_ID"), {}).get('roles', [])
        
        request.session['user'] = user_info
        request.session['roles'] = client_roles
        request.session['access_token'] = token['access_token']
        
        return RedirectResponse("/protected")
        
    except Exception as e:
        error_response(f"Login failed: {str(e)}", status.HTTP_401_UNAUTHORIZED)



@router.get("/protected")
def protected(user: dict = Depends(get_current_user), roles: List[str] = Depends(get_user_roles)):
    return success_response(
        data={"username": user['preferred_username'], "roles": roles},
        message="Access granted"
    )

@router.get("/read-data")
def read_data(user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return success_response(
        data={"username": user['preferred_username']},
        message="Data retrieved successfully"
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
