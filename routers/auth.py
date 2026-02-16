from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from keycloak import KeycloakOpenID
from dependencies import get_current_user, get_user_roles, require_role
from dotenv import load_dotenv
import os
import json
import jwt

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
    return {"message": "Hello World"}

@router.get("/login")
async def login():
    auth_url = keycloak_openid.auth_url(redirect_uri="http://localhost:5000/callback", scope="openid profile email")
    print(f"test {auth_url}")
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
        return {"error": "Login fehlgeschlagen", "details": str(e)}



@router.get("/protected")
def protected(user: dict = Depends(get_current_user), roles: List[str] = Depends(get_user_roles)):
    return {
        "message": f"Hallo {user['preferred_username']}, du bist drin!",
        "your_roles": roles
    }

@router.get("/read-data")
def read_data(user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return {"message": "Hier sind deine Daten", "user": user['preferred_username']}


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
