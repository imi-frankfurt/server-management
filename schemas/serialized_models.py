from pydantic import BaseModel

class ServerSerialized(BaseModel):
    alias: str

class HostAddressSerialized(BaseModel):
    address: str
    server_id: int