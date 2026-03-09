from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from core.dependencies import get_current_user, get_user_roles, require_role, get_token_data
from dotenv import load_dotenv
from typing import List, Dict
from pydantic import BaseModel
import os
from services.authentication_service import create_auth_url, callback_token, direct_login
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
async def get_login_url(frontend_callback_url: str = None):
    """
    Get Keycloak login URL for frontend-initiated OAuth2 flow.
    
    Query params:
    - frontend_callback_url: Your frontend URL where Keycloak should redirect (optional)
      Example: http://localhost:3000/auth/callback
    
    Frontend should:
    1. Call this endpoint to get the auth URL
    2. Redirect user to the auth URL
    3. Handle callback with authorization code
    4. Send code to /auth/exchange-code endpoint
    """
    auth_url = create_auth_url(redirect_uri=frontend_callback_url)
    return {"auth_url": auth_url}

@router.get("/auth/login")
async def login_redirect():
    """
    Direct redirect to Keycloak (legacy support).
    Consider using /auth/login-url for frontend-controlled flow.
    """
    auth_url = create_auth_url()
    return RedirectResponse(auth_url)

@router.post("/auth/token")
def login_with_password(credentials: LoginRequest):
    """
    Direct login with username and password.
    Returns bearer token that should be used in Authorization header.
    
    Example:
    POST /auth/token
    {
        "username": "your_username",
        "password": "your_password"
    }
    """
    return direct_login(credentials.username, credentials.password)

@router.post("/auth/exchange-code")
def exchange_code(request: CodeExchangeRequest):
    """
    Exchange authorization code for access token.
    Called by frontend after receiving code from Keycloak.
    
    Body params:
    - code: Authorization code from Keycloak
    - redirect_uri: Must match the redirect_uri used in /auth/login-url (optional)
    
    Returns bearer token for API authentication.
    """
    return callback_token(request.code, redirect_uri=request.redirect_uri)

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


@router.get("/auth/logout")
def logout(token_data: Dict = Depends(get_token_data)):
    """
    Logout endpoint. With bearer tokens, the client should discard the token.
    This endpoint can be used to verify the token before client-side logout.
    """
    return {
        "status": "success",
        "message": "Please discard your token to complete logout"
    }
