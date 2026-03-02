from pydantic import BaseModel

class ServerSerialized(BaseModel):
    ip: str
    name: str
    alias: list[str] = []

class UserSerialized(BaseModel):
    keycloak_id: str
    username: str

class UserAssignmentSerialized(BaseModel):
    user_id: int
    server_id: int
    primary_user: bool = False