from datetime import datetime

from pydantic import BaseModel, Field


class Namespace(BaseModel):
    name: str


class Pod(BaseModel):
    name: str
    namespace: str
    phase: str
    node_name: str | None = None
    pod_ip: str | None = None


class KubernetesEvent(BaseModel):
    type: str | None = None
    reason: str | None = None
    message: str | None = None
    count: int | None = None
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None


class ResourceQuota(BaseModel):
    name: str
    namespace: str
    hard: dict[str, str] = Field(default_factory=dict)
    used: dict[str, str] = Field(default_factory=dict)


class ResourceUsage(BaseModel):
    namespace: str
    pod_count: int
    cpu_requests: dict[str, str] = Field(default_factory=dict)
    memory_requests: dict[str, str] = Field(default_factory=dict)
    cpu_limits: dict[str, str] = Field(default_factory=dict)
    memory_limits: dict[str, str] = Field(default_factory=dict)


class NodeCondition(BaseModel):
    last_transition_time: datetime
    last_heartbeat_time: datetime
    message: str
    reason: str
    status: str
    type: str


class NodeStatus(BaseModel):
    name: str
    roles: list[str] = Field(default_factory=list)
    version: str | None = None
    conditions: list[NodeCondition]


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
    conditions: list[DeploymentCondition]


class KubernetesClientError(BaseModel):
    code: int | None = None
    status: str | None = None
    reason: str | None = None
    message: str | None = None
    resource: str | None = None
