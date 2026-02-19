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
from services.authentication_service import create_auth_url, callback_token
load_dotenv()
    


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.get("/")
async def root():
    return success_response(message="API is running")

@router.get("/login")
async def login():
    auth_url = create_auth_url()
    return RedirectResponse(auth_url)

@router.get("/callback")
def callback(code: str, request: Request):
    if callback_token(code, request):
        return RedirectResponse(url="/protected", status_code=status.HTTP_302_FOUND)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login failed")

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
