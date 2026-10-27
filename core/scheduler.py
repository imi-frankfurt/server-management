import logging
import os
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import HTTPException
from db.database import SessionLocal
from services.user_service import sync_disabled_users_local

logger = logging.getLogger(__name__)

DEFAULT_SYNC_INTERVAL_MINUTES = 15

scheduler = BackgroundScheduler()

# Shared between the scheduled job and the manual /api/restricted/sync endpoint
# so that two syncs never run concurrently within this process.
sync_lock = threading.Lock()


def run_sync_disabled_users_job():
    if not sync_lock.acquire(blocking=False):
        logger.warning("Skipping scheduled disabled-user sync: a sync is already in progress")
        return

    session = SessionLocal()
    try:
        result = sync_disabled_users_local(session)
        logger.info("Scheduled disabled-user sync finished: %s %s", result["message"], result["summary"])
    except HTTPException as e:
        session.rollback()
        logger.error("Scheduled disabled-user sync failed: %s", e.detail, exc_info=True)
    except Exception:
        session.rollback()
        logger.exception("Scheduled disabled-user sync failed with an unexpected error")
    finally:
        session.close()
        sync_lock.release()


def get_sync_interval_minutes():
    """
    Returns the sync interval in minutes from SYNC_INTERVAL_MINUTES,
    or None if the scheduled sync is disabled (value 0).
    """
    raw_value = os.getenv("SYNC_INTERVAL_MINUTES", str(DEFAULT_SYNC_INTERVAL_MINUTES)).strip()
    try:
        interval_minutes = int(raw_value)
    except ValueError:
        raise RuntimeError(
            f"Invalid SYNC_INTERVAL_MINUTES value '{raw_value}': expected a whole number of minutes (0 disables the sync)"
        )

    if interval_minutes < 0:
        raise RuntimeError(
            f"Invalid SYNC_INTERVAL_MINUTES value '{raw_value}': must not be negative (0 disables the sync)"
        )

    if interval_minutes == 0:
        logger.info("Scheduled disabled-user sync is disabled (SYNC_INTERVAL_MINUTES=0)")
        return None

    return interval_minutes


def start_scheduler():
    interval_minutes = get_sync_interval_minutes()
    if interval_minutes is None or scheduler.running:
        return

    scheduler.add_job(
        run_sync_disabled_users_job,
        "interval",
        minutes=interval_minutes,
        id="sync_disabled_users",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(scheduler.timezone),  # also run once right at startup
    )
    scheduler.start()
    logger.info("Scheduled disabled-user sync started (every %d minutes)", interval_minutes)


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
