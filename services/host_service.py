from fastapi import APIRouter, FastAPI, Request, Depends, HTTPException, Response
from requests import Session
from requests import Session
from core.shared_utilities import check_duplicate, record_exists
from db.database import getSession
from schemas.serialized_models import HostAddressSerialized
from db import models

def create_host_address(
    host_address: HostAddressSerialized,
    request: Request,
    session: Session = Depends(getSession),
):
    if check_duplicate(session, models.HostAddress, address=host_address.address):
        return {"error": "Host Address already exists"}
    if not record_exists(session, models.Server, id=host_address.server_id):
        return {"error": "Server ID does not exist"}
    new_host_address = models.HostAddress(address=host_address.address, server_id=host_address.server_id)
    session.add(new_host_address)
    session.commit()
    return {"message": f"Host Address '{host_address.address}' wurde erstellt"}
