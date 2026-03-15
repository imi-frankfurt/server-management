
import os
import json
import time
import logging
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
import jwt
from fastapi import Depends, Request, status, HTTPException
from dotenv import load_dotenv
from keycloak import KeycloakOpenID
from typing import Dict, Any, Optional

from core.shared_utilities import error_response
load_dotenv()

logger = logging.getLogger(__name__)

keycloak_openid = KeycloakOpenID(
    server_url=os.getenv("KEYCLOAK_URL"),
    client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
    realm_name=os.getenv("KEYCLOAK_REALM"),
    client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET")
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/callback")
security = HTTPBearer(auto_error=True)

_JWKS_CACHE: Dict[str, Any] = {"keys": None, "expires_at": 0.0}
_JWKS_CACHE_TTL_SECONDS = 300


def _normalize_issuer_base(url: Optional[str]) -> str:
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keycloak URL is not configured"
        )
    return url.rstrip("/")


def _expected_issuer() -> str:
    base_url = _normalize_issuer_base(os.getenv("KEYCLOAK_URL"))
    realm = os.getenv("KEYCLOAK_REALM")
    if not realm:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keycloak realm is not configured"
        )
    return f"{base_url}/realms/{realm}"


def _get_jwks() -> Dict[str, Any]:
    now = time.time()
    if _JWKS_CACHE["keys"] and now < _JWKS_CACHE["expires_at"]:
        return _JWKS_CACHE["keys"]

    certs = keycloak_openid.certs()
    if not isinstance(certs, dict) or "keys" not in certs:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to load Keycloak JWKS",
            headers={"WWW-Authenticate": "Bearer"}
        )

    _JWKS_CACHE["keys"] = certs
    _JWKS_CACHE["expires_at"] = now + _JWKS_CACHE_TTL_SECONDS
    return certs


def _select_signing_key(token: str):
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing key id",
            headers={"WWW-Authenticate": "Bearer"}
        )

    jwks = _get_jwks()
    signing_jwk = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)
    if not signing_jwk:
        # Key rotation may have happened, refresh once and retry.
        _JWKS_CACHE["expires_at"] = 0
        jwks = _get_jwks()
        signing_jwk = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)

    if not signing_jwk:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No matching signing key found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(signing_jwk))


def _validate_audience(decoded_token: Dict[str, Any]) -> None:
    client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keycloak client id is not configured"
        )

    aud_claim = decoded_token.get("aud", [])
    aud_values = [aud_claim] if isinstance(aud_claim, str) else aud_claim
    azp_claim = decoded_token.get("azp")

    if client_id not in aud_values and azp_claim != client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
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
          
        signing_key = _select_signing_key(token)

        try:
            decoded_token = jwt.decode(
                token,
                key=signing_key,
                algorithms=["RS256"],
                issuer=_expected_issuer(),
                options={
                    "require": ["exp", "iat", "iss", "sub"],
                },
            )
            _validate_audience(decoded_token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidIssuerError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.ImmatureSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is not active yet",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Build identity from verified JWT claims. This avoids insecure auth fallback when
        # upstream userinfo requests fail or return transient errors.
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
        logger.exception("Error validating authentication token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
