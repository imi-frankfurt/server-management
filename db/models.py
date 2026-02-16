
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
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
    # m:n relationship with User
    users = relationship("User", secondary="user_cluster", back_populates="clusters")
    # 1:n relationship with HostAddress
    host_addresses = relationship("HostAddress", back_populates="cluster")
    # 1:n relationship with IgnoredUser
    ignored_users = relationship("IgnoredUser", back_populates="cluster")

class HostAddress(Base):
    __tablename__ = "host_address"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, unique=True, index=True)
    cluster_id = Column(Integer, ForeignKey("cluster.id"))
    cluster = relationship("Cluster", back_populates="host_addresses")

class IgnoredUser(Base):
    __tablename__ = "ignored_user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    cluster_id = Column(Integer, ForeignKey("cluster.id"))
    cluster = relationship("Cluster", back_populates="ignored_users")


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    clusters = relationship("Cluster", secondary="user_cluster", back_populates="users")
    public_keys = relationship("PublicKey", back_populates="user")

class PublicKey(Base):
    __tablename__ = "public_key"
    id = Column(Integer, primary_key=True, index=True)
    key_content = Column(Text, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="public_keys")

user_cluster = Table(
    'user_cluster',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('cluster_id', Integer, ForeignKey('cluster.id'), primary_key=True)
)

