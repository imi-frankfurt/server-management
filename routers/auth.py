from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from core.dependencies import get_current_user, get_user_roles, require_role, get_token_data, require_csrf_token
from dotenv import load_dotenv
from typing import List
from pydantic import BaseModel
from services.authentication_service import create_auth_url, callback_token, refresh_token, set_pkce_verifier_cookie
load_dotenv()

class LoginRequest(BaseModel):
    username: str
    password: str

class CodeExchangeRequest(BaseModel):
    code: str
    redirect_uri: str = None
    


router = APIRouter(
    tags=["Authentication"]
)


@router.get("/")
async def root():
    return {"message": "API is running"}

@router.get("/auth/login-url")
async def get_login_url(response: Response, frontend_callback_url: str = None):
    auth_url, code_verifier = create_auth_url(redirect_uri=frontend_callback_url)
    set_pkce_verifier_cookie(response, code_verifier)
    return {"auth_url": auth_url}

@router.get("/auth/login")
async def login_redirect():
    auth_url, code_verifier = create_auth_url()
    # Cookies on an injected Response are not applied when returning a RedirectResponse.
    redirect = RedirectResponse(auth_url)
    set_pkce_verifier_cookie(redirect, code_verifier)
    return redirect

@router.post("/auth/refresh")
def refresh_token_route(request: Request, response: Response):
    result = refresh_token(request, response)
    return result

@router.post("/auth/exchange-code")
def exchange_code(body: CodeExchangeRequest, request: Request, response: Response):
    result = callback_token(body.code, request, response, redirect_uri=body.redirect_uri)
    return result

@router.get("/protected")
def protected(user: dict = Depends(get_current_user), roles: List[str] = Depends(get_user_roles)):
    return {
        "status": "success",
        "message": "Access granted",
        "data": {"username": user['preferred_username'], "roles": roles}
    }

@router.get("/read-data")
def read_data(user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return {
        "status": "success",
        "message": "Data retrieved successfully",
        "data": {"username": user['preferred_username']}
    }

@router.get("/auth/session")
def get_session(
    user: dict = Depends(get_current_user),
    roles: List[str] = Depends(get_user_roles)
):
    return {
        "status": "authenticated",
        "user": {
            "username": user.get("preferred_username"),
            "email": user.get("email"),
            "roles": roles
        }
    }

@router.post("/auth/logout")
def logout(response: Response, _csrf = Depends(require_csrf_token)):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    response.delete_cookie(key="csrf_token", path="/")
    return {"status": "success", "message": "Logged out successfully"}
