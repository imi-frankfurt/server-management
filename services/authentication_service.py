
import os
import json
import time
import logging
import secrets
import token
import jwt
import requests
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, Request, status, HTTPException, Response
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
_ISSUER_CACHE: Dict[str, Any] = {"issuers": None, "expires_at": 0.0}
_ISSUER_CACHE_TTL_SECONDS = 300


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=_cookie_secure_enabled(),
        samesite=_cookie_samesite_value(),
        path="/",
    )


def _cookie_secure_enabled() -> bool:
    return os.getenv("COOKIE_SECURE", "true").strip().lower() in {"1", "true", "yes", "on"}


def _cookie_samesite_value() -> str:
    # SameSite=None requires Secure=true in modern browsers.
    if _cookie_secure_enabled():
        return "none"
    return os.getenv("COOKIE_SAMESITE", "lax").strip().lower()


def _normalize_issuer_base(url: Optional[str]) -> str:
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keycloak URL is not configured"
        )
    return url.rstrip("/")


def _expected_issuer_from_env() -> str:
    base_url = _normalize_issuer_base(os.getenv("KEYCLOAK_URL"))
    realm = os.getenv("KEYCLOAK_REALM")
    if not realm:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keycloak realm is not configured"
        )
    return f"{base_url}/realms/{realm}"


def _get_allowed_issuers() -> set[str]:
    now = time.time()
    if _ISSUER_CACHE["issuers"] and now < _ISSUER_CACHE["expires_at"]:
        return _ISSUER_CACHE["issuers"]

    issuers = set()

    env_issuer = os.getenv("KEYCLOAK_ISSUER")
    if env_issuer:
        issuers.add(env_issuer.rstrip("/"))

    issuers.add(_expected_issuer_from_env().rstrip("/"))

    try:
        well_known = keycloak_openid.well_known()
        discovered_issuer = well_known.get("issuer") if isinstance(well_known, dict) else None
        if discovered_issuer:
            issuers.add(discovered_issuer.rstrip("/"))
    except Exception:
        logger.warning("Could not fetch Keycloak well-known issuer", exc_info=True)

    _ISSUER_CACHE["issuers"] = issuers
    _ISSUER_CACHE["expires_at"] = now + _ISSUER_CACHE_TTL_SECONDS
    return issuers


def _validate_issuer(decoded_token: Dict[str, Any]) -> None:
    token_issuer = (decoded_token.get("iss") or "").rstrip("/")
    allowed_issuers = _get_allowed_issuers()

    if not token_issuer or token_issuer not in allowed_issuers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
            headers={"WWW-Authenticate": "Bearer"}
        )


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
    resource_access = decoded_token.get("resource_access", {})
    has_client_resource_access = isinstance(resource_access, dict) and client_id in resource_access

    if client_id not in aud_values and azp_claim != client_id and not has_client_resource_access:
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
        cookie_secure = _cookie_secure_enabled()
        cookie_samesite = _cookie_samesite_value()
        csrf_token = generate_csrf_token()

        uri = redirect_uri or os.getenv("KEYCLOAK_REDIRECT_URI")
        token = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri=uri
        )
        
        # Set access token cookie
        if (token.get('access_token')):
            response.set_cookie(
                key="access_token",
                value=token['access_token'],
                httponly=True,
                secure=cookie_secure,
                samesite=cookie_samesite,
                path="/",
                max_age=token.get('expires_in', 3600)
            )
        if (token.get('refresh_token')):
            response.set_cookie(
                    key="refresh_token",
                    value=token['refresh_token'],
                    httponly=True,
                    secure=cookie_secure,
                    samesite=cookie_samesite,
                    path="/",
                    max_age=2592000  # 30 days
                )
        _set_csrf_cookie(response, csrf_token)
                
        return {
            "status": "success",
            "message": "Authentication successful",
            "expires_in": token.get('expires_in'),
            "csrf_token": csrf_token
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )

def refresh_token(request: Request, response: Response) -> Dict:
    try:
        cookie_secure = _cookie_secure_enabled()
        cookie_samesite = _cookie_samesite_value()
        csrf_token = generate_csrf_token()
        refresh_token = request.cookies.get("refresh_token");
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token found"
            )
        payload ={
            'grant_type': os.getenv("KEYCLOAK_REFRESH_SCOPE", "refresh_token"),
            'refresh_token': refresh_token,
            'client_id': os.getenv("KEYCLOAK_CLIENT_ID"),
            'client_secret': os.getenv("KEYCLOAK_CLIENT_SECRET")
        }
        url = f"{os.getenv('KEYCLOAK_URL')}realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/token"
        r = requests.post(url, data=payload)

        if r.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Keycloak refresh failed: {r.text}")
        
        token_data = r.json()    

        response.set_cookie(
            key="access_token",
            value=token_data['access_token'],
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
            path="/"
        )
        if token_data.get('refresh_token'):
            response.set_cookie(
                key="refresh_token",
                value=token_data['refresh_token'],
                httponly=True,
                secure=cookie_secure,
                samesite=cookie_samesite,
                path="/",
                max_age=2592000  # 30 days
            )
            
        _set_csrf_cookie(response, csrf_token)
        return {
            "status": "success",
            "message": "Token refreshed",
            "expires_in": token_data.get("expires_in"),
            "csrf_token": csrf_token
        }    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
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
                options={
                    "require": ["exp", "iat", "iss", "sub"],
                    "verify_aud": False,
                },
            )
            _validate_issuer(decoded_token)
            _validate_audience(decoded_token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
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
    except HTTPException as auth_exc:
        logger.warning("Token validation rejected request: %s", auth_exc.detail)
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.exception("Error validating authentication token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
