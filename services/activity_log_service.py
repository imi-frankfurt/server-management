from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from db import models


UPDATE_ACTIONS = ("post", "put")
SYNC_ACTION = "sync"


def create_activity_log(
    session: Session,
    action: str,
    resource: str,
    details: str | None = None,
) -> None:
    """Queue a log row in the current transaction."""
    session.add(
        models.ActivityLog(
            action=action.lower(),
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
