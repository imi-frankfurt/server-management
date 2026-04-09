import secrets

from fastapi import Depends, HTTPException, Request, status
from typing import List, Dict
from services.authentication_service import verify_token

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def require_csrf_token(request: Request) -> None:
    if request.method.upper() in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return

    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)

    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid"
        )

def get_token_data(token_data: Dict = Depends(verify_token)) -> Dict:
    return token_data

def get_current_user(token_data: Dict = Depends(get_token_data)) -> Dict:
    return token_data["user_info"]

def get_user_roles(token_data: Dict = Depends(get_token_data)) -> List[str]:
    return token_data["roles"]

def require_role(required_role: str):
    """
    Dependency factory: Check if the user has a specific role.
    """
    def role_checker(token_data: Dict = Depends(get_token_data)):
        roles = token_data["roles"]
        if required_role not in roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied: Role '{required_role}' required"
            )
        return roles
    return role_checker