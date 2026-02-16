
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base


Base = declarative_base()

class Base(Base):
    __abstract__ = True
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Cluster(Base):
    __tablename__ = "cluster"
    
    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String, unique=True, index=True)
