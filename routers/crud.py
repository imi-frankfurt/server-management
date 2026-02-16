from fastapi import APIRouter, FastAPI, Request, Depends, HTTPException, Response
from db import models
from db.database import getSession
from dependencies import get_current_user, require_role
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/get-clusters")
def get_clusters(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    s = session.query(models.Cluster).all()
    return {"message": "Clusters sind erreichbar", "clusters": s}
