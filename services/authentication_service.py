
import os
import jwt
from fastapi import Request, status
from dotenv import load_dotenv
from keycloak import KeycloakOpenID

from core.shared_utilities import error_response
load_dotenv()

keycloak_openid = KeycloakOpenID(
    server_url=os.getenv("KEYCLOAK_URL"),
    client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
    realm_name=os.getenv("KEYCLOAK_REALM"),
    client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET")
)

def create_auth_url():
    return keycloak_openid.auth_url(redirect_uri=os.getenv("KEYCLOAK_REDIRECT_URI"), scope=os.getenv("KEYCLOAK_SCOPE"))

def callback_token(code: str, request: Request):
    try:
        token = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri=os.getenv("KEYCLOAK_REDIRECT_URI")
        )
        
        user_info = keycloak_openid.userinfo(token['access_token'])

        decoded_token = jwt.decode(token['access_token'], options={"verify_signature": False})
        
        client_roles = decoded_token.get('resource_access', {}).get(os.getenv("KEYCLOAK_CLIENT_ID"), {}).get('roles', [])
        
        request.session['user'] = user_info
        request.session['roles'] = client_roles
        request.session['access_token'] = token['access_token']

        return True        
    except Exception as e:
        error_response(f"Login failed: {str(e)}", status.HTTP_401_UNAUTHORIZED)
        return False
