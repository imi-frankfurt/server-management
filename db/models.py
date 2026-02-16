
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

class Base(Base):
    __abstract__ = True
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Cluster(Base):
    __tablename__ = "cluster"
    
    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String, unique=True, index=True)

class HostAdress(Base):
    __tablename__ = "host_address"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, unique=True, index=True)
    cluster = relationship("Cluster", back_populates="host_addresses")



