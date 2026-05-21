from pydantic import BaseModel

class ServerSerialized(BaseModel):
    ip: str
    name: str
    alias: list[str] = []

class UserSerialized(BaseModel):
    keycloak_id: str
    username: str

class UserAssignmentSerialized(BaseModel):
    user_id: str | int
    server_id: int
    primary_user: bool = False

class UserUnassignmentSerialized(BaseModel):
    user_id: str | int
    server_id: int

class UserUpdateSerialized(BaseModel):
    server_id: int
    primary_user: bool = False

class IgnoreListEntrySerialized(BaseModel):
    username: str
    server_id: int

class IgnoreListUnassignSerialized(BaseModel):
    server_id: int
    username: str

