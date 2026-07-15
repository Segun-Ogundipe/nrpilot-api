from datetime import datetime

from pydantic import BaseModel


class Namespace(BaseModel):
    name: str


class Pod(BaseModel):
    name: str
    namespace: str
    phase: str
    node_name: str | None = None
    pod_ip: str | None = None


class DeploymentCondition(BaseModel):
    last_transition_time: datetime
    last_update_time: datetime
    message: str
    reason: str
    status: str
    type: str


class Deployment(BaseModel):
    name: str
    namespace: str
    ready_replicas: int
    replicas: int
    available_replicas: int
    unavailable_replicas: int
    condition: DeploymentCondition
