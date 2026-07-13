import os
from apscheduler.schedulers.background import BackgroundScheduler
from db.database import SessionLocal
from services.user_service import sync_disabled_users_local

scheduler = BackgroundScheduler()


def run_sync_disabled_users_job():
    session = SessionLocal()
    try:
        sync_disabled_users_local(session)
    finally:
        session.close()


def start_scheduler():
    interval_minutes = int(os.getenv("SYNC_INTERVAL_MINUTES", "15"))
    scheduler.add_job(
        run_sync_disabled_users_job,
        "interval",
        minutes=interval_minutes,
        id="sync_disabled_users",
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
