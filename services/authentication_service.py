
import os
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
import jwt
from fastapi import Depends, Request, status, HTTPException
from dotenv import load_dotenv
from keycloak import KeycloakOpenID
from typing import Dict

from core.shared_utilities import error_response
load_dotenv()

keycloak_openid = KeycloakOpenID(
    server_url=os.getenv("KEYCLOAK_URL"),
    client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
    realm_name=os.getenv("KEYCLOAK_REALM"),
    client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET")
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/callback")
security = HTTPBearer(auto_error=True)
    
def create_auth_url(redirect_uri: str = None):
    uri = redirect_uri or os.getenv("KEYCLOAK_REDIRECT_URI")
    return keycloak_openid.auth_url(redirect_uri=uri, scope=os.getenv("KEYCLOAK_SCOPE"))

from fastapi import Response

def callback_token(code: str, response: Response, redirect_uri: str = None) -> Dict:
    try:
        uri = redirect_uri or os.getenv("KEYCLOAK_REDIRECT_URI")
        token = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri=uri
        )
        
        # Set access token cookie
        response.set_cookie(
            key="access_token",
            value=token['access_token'],
            httponly=True,
            secure=True,  # Required for SameSite=None
            samesite="none",  # Required for cross-origin cookies
            path="/",
            max_age=token.get('expires_in', 3600)
        )

        # Set refresh token cookie if present
        if token.get('refresh_token'):
            response.set_cookie(
                key="refresh_token",
                value=token['refresh_token'],
                httponly=True,
                secure=True,  # Required for SameSite=None
                samesite="none",  # Required for cross-origin cookies
                path="/",
                max_age=2592000  # 30 days
            )
        
        return {
            "status": "success",
            "message": "Authentication successful",
            "expires_in": token.get('expires_in')
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )


def verify_token(request: Request) -> Dict:
    try:
        token = request.cookies.get("access_token")
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No authentication token found"
                )
          
        try:
            decoded_token = jwt.decode(
                token,
                options={"verify_signature": False, "verify_aud": False},
                algorithms=["RS256"]
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        try:
            user_info = keycloak_openid.userinfo(token)
        except Exception as e:
            print(f"Warning: Could not verify token with Keycloak: {e}")
            # Fallback to decoded token data if Keycloak verification fails
            user_info = {
                "sub": decoded_token.get("sub"),
                "preferred_username": decoded_token.get("preferred_username"),
                "email": decoded_token.get("email"),
                "name": decoded_token.get("name")
            }
        
        # Extract client roles
        client_id = os.getenv("KEYCLOAK_CLIENT_ID")
        client_roles = decoded_token.get('resource_access', {}).get(
            client_id, {}
        ).get('roles', [])
        
        # Also check realm roles
        realm_roles = decoded_token.get('realm_access', {}).get('roles', [])
        
        return {
            "user_info": user_info,
            "roles": client_roles + realm_roles,  # Combine both client and realm roles
            "decoded_token": decoded_token
        }
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        print(f"Error in verify_token: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
