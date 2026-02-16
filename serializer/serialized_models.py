from pydantic import BaseModel

class ClusterSerialized(BaseModel):
    alias: str

class HostAddressSerialized(BaseModel):
    address: str
    cluster_id: int