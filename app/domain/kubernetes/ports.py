from abc import ABC, abstractmethod
from typing import Any

from app.models.kubernetes.models import (
    Deployment,
    KubernetesClientError,
    KubernetesEvent,
    Namespace,
    NodeStatus,
    Pod,
    ResourceQuota,
    ResourceUsage,
)


class KubernetesClientPort(ABC):
    @abstractmethod
    def list_namespaces(self) -> list[Namespace] | KubernetesClientError:
        pass

    @abstractmethod
    def list_pods(self, namespace: str) -> list[Pod] | KubernetesClientError:
        pass

    @abstractmethod
    def describe_pod(
        self, namespace: str, pod_name: str
    ) -> Pod | KubernetesClientError:
        pass

    @abstractmethod
    def list_pod_events(
        self, namespace: str, pod_name: str
    ) -> list[KubernetesEvent] | KubernetesClientError:
        pass

    @abstractmethod
    def list_namespace_events(
        self, namespace: str
    ) -> list[KubernetesEvent] | KubernetesClientError:
        pass

    @abstractmethod
    def list_resource_quotas(
        self, namespace: str
    ) -> list[ResourceQuota] | KubernetesClientError:
        pass

    @abstractmethod
    def get_resource_usage(
        self, namespace: str
    ) -> ResourceUsage | KubernetesClientError:
        pass

    @abstractmethod
    def list_nodes(self) -> list[NodeStatus] | KubernetesClientError:
        pass

    @abstractmethod
    def get_pod_log(
        self, namespace: str, pod_name: str, tail_lines: int | None = None
    ) -> Any:
        pass

    @abstractmethod
    def list_deployments(
        self, namespace: str
    ) -> list[Deployment] | KubernetesClientError:
        pass
