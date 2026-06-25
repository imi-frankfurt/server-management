from fastapi import APIRouter, Depends
from requests import Session
from core.dependencies import get_current_user, require_role
from db.database import getSession
from services.ansible_service import ansible_export

router = APIRouter(
    prefix="/api",
    tags=["Ensemble API"]
)

@router.get("/ansible", status_code=200)
def export_ansible_data(session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return ansible_export(session)
