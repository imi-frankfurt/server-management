from fastapi import APIRouter, FastAPI, Request, Depends, HTTPException, Response
from db import models
from db.database import getSession
from dependencies import get_current_user, require_role
from sqlalchemy.orm import Session
from serializer.serialized_models import ClusterSerialized, HostAddressSerialized

router = APIRouter()

def check_duplicate(session, model, **kwargs):
    return session.query(model).filter_by(**kwargs).first() is not None

def cluster_id_exists(session: Session, cluster_id: int) -> bool:
    return session.query(models.Cluster).filter_by(id=cluster_id).first() is not None

@router.get("/get-clusters")
def get_clusters(request: Request, session: Session = Depends(getSession), user: dict = Depends(get_current_user), _roles = Depends(require_role("read-only-role"))):
    s = session.query(models.Cluster).all()
    return {"message": "Clusters sind erreichbar", "clusters": s}

@router.post("/create-cluster")
def create_cluster(cluster: ClusterSerialized, request: Request = None, session: Session = Depends(getSession)):
    if check_duplicate(session, models.Cluster, alias=cluster.alias):
            return {"error": "Cluster already exists"}
    new_cluster = models.Cluster(alias=cluster.alias)
    session.add(new_cluster)
    session.commit()
    return {"message": f"Cluster '{cluster.alias}' wurde erstellt"}

@router.post("/create-host_address")
def create_host_address(
    host_address: HostAddressSerialized,
    request: Request,
    session: Session = Depends(getSession),
):
    if check_duplicate(session, models.HostAddress, address=host_address.address):
        return {"error": "Host Address already exists"}
    if not cluster_id_exists(session, host_address.cluster_id):
        return {"error": "Cluster ID does not exist"}
    new_host_address = models.HostAddress(address=host_address.address, cluster_id=host_address.cluster_id)
    session.add(new_host_address)
    session.commit()
    return {"message": f"Host Address '{host_address.address}' wurde erstellt"}