from typing import Any

from app.domain.kubernetes.ports import KubernetesClientPort
from app.models.kubernetes.models import Deployment, Namespace, Pod


class KubernetesService:
    def __init__(self, client: KubernetesClientPort) -> None:
        self._client = client

    def list_namespaces(self) -> list[Namespace]:
        return self._client.list_namespaces()

    def list_pods(self, namespace: str) -> list[Pod]:
        return self._client.list_pods(namespace)

    def get_pod(self, namespace: str, pod_name: str) -> Pod:
        return self._client.describe_pod(namespace, pod_name)

    def get_pod_log(
        self, namespace: str, pod_name: str, tail_lines: int | None = None
    ) -> Any:
        return self._client.get_pod_log(namespace, pod_name, tail_lines)

    def list_deployments(self, namespace: str) -> list[Deployment]:
        return self._client.list_deployments(namespace)
