
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

class Base(Base):
    __abstract__ = True
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Server(Base):
    __tablename__ = "server"
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    # m:n relationship with User
    users = relationship("User", secondary="user_server", back_populates="servers")
    # 1:n relationship with Alias
    alias = relationship("Alias", back_populates="server", cascade="all, delete-orphan")
    # 1:n relationship with IgnoredUser
    ignored_users = relationship("IgnoredUser", back_populates="server", cascade="all, delete-orphan")

class Alias(Base):
    __tablename__ = "alias"
    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String, unique=True, index=True)
    server_id = Column(Integer, ForeignKey("server.id", ondelete="CASCADE"))
    server = relationship("Server", back_populates="alias")

class IgnoredUser(Base):
    __tablename__ = "ignored_user"
    __table_args__ = (
        UniqueConstraint('username', 'server_id', name='uq_ignored_user_username_server'),
    )
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    server_id = Column(Integer, ForeignKey("server.id", ondelete="CASCADE"))
    server = relationship("Server", back_populates="ignored_users")

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    keycloak_id = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    enabled = Column(Boolean, default=True)
    servers = relationship("Server", secondary="user_server", back_populates="users")
    public_keys = relationship("PublicKey", back_populates="user", cascade="all, delete-orphan")

class PublicKey(Base):
    __tablename__ = "public_key"
    id = Column(Integer, primary_key=True, index=True)
    key_content = Column(Text, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="public_keys")
    
class AnsibleContent(Base):
    __tablename__ = "ansible_content"
    id = Column(Integer, primary_key=True, index=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    json_data = Column(Text, nullable=False)
    queries = relationship("AnsibleQuery", back_populates="content")


class AnsibleQuery(Base):
    __tablename__ = "ansible_queries"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String, nullable=False, index=True)
    ansible_content_id = Column(Integer, ForeignKey("ansible_content.id", ondelete="RESTRICT"), nullable=False)
    content = relationship("AnsibleContent", back_populates="queries")

class ActivityLog(Base):
    __tablename__ = "activity_log"
    __table_args__ = (
        Index("ix_activity_log_action_created_at", "action", "created_at"),
        Index("ix_activity_log_resource_created_at", "resource", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False, index=True)  # post | put | sync
    actor = Column(String, nullable=True, index=True) # User performing the action
    resource = Column(String, nullable=False, index=True)
    details = Column(Text, nullable=True)

user_server = Table(
    'user_server',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), primary_key=True),
    Column('server_id', Integer, ForeignKey('server.id', ondelete="CASCADE"), primary_key=True),
    Column('primary_user', Boolean, default=False),
    Column('created_at', DateTime, default=datetime.now),
    Column('updated_at', DateTime, default=datetime.now, onupdate=datetime.now)
)

