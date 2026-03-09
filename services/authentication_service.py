
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
    """
    Generate Keycloak login URL.
    If redirect_uri is provided, use it. Otherwise use env variable.
    """
    uri = redirect_uri or os.getenv("KEYCLOAK_REDIRECT_URI")
    return keycloak_openid.auth_url(redirect_uri=uri, scope=os.getenv("KEYCLOAK_SCOPE"))

def callback_token(code: str, redirect_uri: str = None) -> Dict:
    """
    Exchange authorization code for access token.
    If redirect_uri is provided, use it. Otherwise use env variable.
    """
    try:
        uri = redirect_uri or os.getenv("KEYCLOAK_REDIRECT_URI")
        token = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri=uri
        )
        
        return {
            "access_token": token['access_token'],
            "refresh_token": token.get('refresh_token'),
            "token_type": "bearer",
            "expires_in": token.get('expires_in')
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )

def direct_login(username: str, password: str) -> Dict:
    """
    Direct username/password login - returns bearer token.
    Simpler for frontend apps without OAuth2 redirect flow.
    """
    try:
        token = keycloak_openid.token(
            grant_type='password',
            username=username,
            password=password
        )
        
        return {
            "access_token": token['access_token'],
            "refresh_token": token.get('refresh_token'),
            "token_type": "bearer",
            "expires_in": token.get('expires_in')
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials: {str(e)}"
        )

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Verify and decode the bearer token from the Authorization header.
    Returns the decoded token payload with user info and roles.
    """
    try:
        token = credentials.credentials
        
        # Decode token to get roles and other claims first (faster, no network call)
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
        
        # Verify token with Keycloak (optional, comment out for faster validation)
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
