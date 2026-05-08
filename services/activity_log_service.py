from datetime import datetime
from fastapi import HTTPException, status
from core.shared_utilities import error_response
from sqlalchemy import func
from sqlalchemy.orm import Session

from db import models


UPDATE_ACTIONS = ("post", "put")
SYNC_ACTION = "sync"


def create_activity_log(
    session: Session,
    action: str,
    resource: str,
    actor: str | None = None,
    details: str | None = None,
) -> None:
    """Queue a log row in the current transaction."""
    session.add(
        models.ActivityLog(
            action=action.lower(),
            actor=actor,
            resource=resource,
            details=details,
        )
    )


def get_activity_status(session: Session) -> dict:
    """Return latest sync and latest update timestamps."""
    last_synced = (
        session.query(func.max(models.ActivityLog.created_at))
        .filter(models.ActivityLog.action == SYNC_ACTION)
        .scalar()
    )

    last_updated = (
        session.query(func.max(models.ActivityLog.created_at))
        .filter(models.ActivityLog.action.in_(UPDATE_ACTIONS))
        .scalar()
    )

    return {
        "last_synced": last_synced,
        "last_updated": last_updated,
        "server_time": datetime.now(),
    }

def get_logs(session: Session, action: str | None = None, resource: str | None = None, limit: int = 100) -> list[dict]:
    """Return a list of activity logs, optionally filtered by action and/or resource."""
    try :
        query = session.query(models.ActivityLog)

        if action:
            query = query.filter(models.ActivityLog.action == action.lower())
        if resource:
            query = query.filter(models.ActivityLog.resource == resource.lower())

        logs = query.order_by(models.ActivityLog.created_at.desc()).limit(limit).all()

        return [
            {
                "id": log.id,
                "action": log.action,
                "actor": log.actor,
                "resource": log.resource,
                "details": log.details,
                "created_at": log.created_at,
                "updated_at": log.updated_at,
            }
            for log in logs
        ]
    except Exception as e:
        error_response(f"Failed to fetch activity logs: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)
        