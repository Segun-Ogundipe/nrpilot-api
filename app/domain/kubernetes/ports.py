from abc import ABC, abstractmethod
from typing import Any

from app.models.kubernetes.models import Deployment, KubernetesEvent, Namespace, Pod


class KubernetesClientPort(ABC):
    @abstractmethod
    def list_namespaces(self) -> list[Namespace]:
        pass

    @abstractmethod
    def list_pods(self, namespace: str) -> list[Pod]:
        pass

    @abstractmethod
    def describe_pod(self, namespace: str, pod_name: str) -> Pod:
        pass

    @abstractmethod
    def list_pod_events(self, namespace: str, pod_name: str) -> list[KubernetesEvent]:
        pass

    @abstractmethod
    def get_pod_log(
        self, namespace: str, pod_name: str, tail_lines: int | None = None
    ) -> Any:
        pass

    @abstractmethod
    def list_deployments(self, namespace: str) -> list[Deployment]:
        pass
