from typing import List

from fastapi import APIRouter, Depends
from requests import Session
from core.dependencies import get_current_user, require_role
from db.database import getSession
from services.ansible_service import ansible_export, get_ansible_history
from schemas.serialized_models import AnsibleContentGroupResponse

router = APIRouter(
    prefix="/api",
    tags=["Ensemble API"]
)

@router.get("/ansible", status_code=200)
def export_ansible_data(session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return ansible_export(session)

@router.get("/ansible/history", response_model=List[AnsibleContentGroupResponse], status_code=200)
def fetch_ansible_history(session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    return get_ansible_history(session)


