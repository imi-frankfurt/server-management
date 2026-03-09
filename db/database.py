import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from db.models import Base

load_dotenv()

DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_DOCKER_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Increase pool size and add connection pool settings
engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # Increase from default 5
    max_overflow=20,       # Increase from default 10
    pool_pre_ping=True,    # Test connections before using
    pool_recycle=3600      # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    Base.metadata.create_all(bind=engine)

def getSession():
    """
    Dependency that provides a database session and ensures it's closed properly.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
