import json
from typing import Any, List

from pydantic import BaseModel, field_validator

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
    
class QueryTimestampResponse(BaseModel):
    id: int
    class Config:
        from_attributes = True

class AnsibleContentGroupResponse(BaseModel):
    id: int
    content_hash: str
    json_data: Any
    queries: List[QueryTimestampResponse] 

    @field_validator('json_data', mode='before')
    def parse_json_string(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {} 
        return value

    class Config:
        from_attributes = True

