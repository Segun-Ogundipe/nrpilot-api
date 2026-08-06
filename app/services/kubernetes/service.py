from typing import Any

from app.domain.kubernetes.ports import KubernetesClientPort
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


class KubernetesService:
    def __init__(self, client: KubernetesClientPort) -> None:
        self._client = client

    def list_namespaces(self) -> list[Namespace] | KubernetesClientError:
        return self._client.list_namespaces()

    def list_pods(self, namespace: str) -> list[Pod] | KubernetesClientError:
        return self._client.list_pods(namespace)

    def get_pod(self, namespace: str, pod_name: str) -> Pod | KubernetesClientError:
        return self._client.describe_pod(namespace, pod_name)

    def list_pod_events(
        self, namespace: str, pod_name: str
    ) -> list[KubernetesEvent] | KubernetesClientError:
        return self._client.list_pod_events(namespace, pod_name)

    def list_namespace_events(
        self, namespace: str
    ) -> list[KubernetesEvent] | KubernetesClientError:
        return self._client.list_namespace_events(namespace)

    def list_resource_quotas(
        self, namespace: str
    ) -> list[ResourceQuota] | KubernetesClientError:
        return self._client.list_resource_quotas(namespace)

    def get_resource_usage(
        self, namespace: str
    ) -> ResourceUsage | KubernetesClientError:
        return self._client.get_resource_usage(namespace)

    def list_nodes(self) -> list[NodeStatus] | KubernetesClientError:
        return self._client.list_nodes()

    def get_pod_log(
        self, namespace: str, pod_name: str, tail_lines: int | None = None
    ) -> Any:
        return self._client.get_pod_log(namespace, pod_name, tail_lines)

    def list_deployments(
        self, namespace: str
    ) -> list[Deployment] | KubernetesClientError:
        return self._client.list_deployments(namespace)
