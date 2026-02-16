from fastapi import APIRouter, FastAPI, Request, Depends, HTTPException, Response

from dependencies import get_current_user, require_role

router = APIRouter()

@router.get("/get-server")
def get_server(request: Request, user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return {"message": "Server ist erreichbar"}
