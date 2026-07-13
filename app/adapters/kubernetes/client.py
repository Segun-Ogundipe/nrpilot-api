from collections.abc import Callable
from enum import StrEnum
from typing import Any, NoReturn, TypeVar

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from app.adapters.kubernetes.config import load_kubernetes_config
from app.adapters.kubernetes.exceptions import (
    DeploymentNotFoundError,
    KubernetesConnectionError,
    NamespaceNotFoundError,
    PodNotFoundError,
)
from app.core.logging import get_logger
from app.core.settings import Settings

logger = get_logger(__name__)

T = TypeVar("T")


class ResourceType(StrEnum):
    NAMESPACE = "namespace"
    POD = "pod"
    DEPLOYMENT = "deployment"


class KubernetesClient:
    def __init__(self, settings: Settings) -> None:
        load_kubernetes_config(settings)

        self._core = client.CoreV1Api()
        self._apps = client.AppsV1Api()

    def list_namespaces(self) -> Any:
        return self._execute(
            lambda: self._core.list_namespace().items, resource=ResourceType.NAMESPACE
        )

    def list_pods(self, namespace: str) -> Any:
        return self._execute(
            lambda: self._core.list_namespaced_pod(namespace).items,
            resource=ResourceType.NAMESPACE,
        )

    def describe_pod(self, namespace: str, pod_name: str) -> Any:
        return self._execute(
            lambda: self._core.read_namespaced_pod(name=pod_name, namespace=namespace),
            resource=ResourceType.POD,
        )

    def get_pod_logs(
        self, namespace: str, pod_name: str, tail_lines: int | None = None
    ) -> Any:
        return self._execute(
            lambda: self._core.read_namespaced_pod_log(
                namespace=namespace, name=pod_name, tail_lines=tail_lines
            ),
            resource=ResourceType.POD,
        )

    def list_deployments(self, namespace: str) -> Any:
        return self._execute(
            lambda: self._apps.list_namespaced_deployment(namespace).items,
            resource=ResourceType.DEPLOYMENT,
        )

    def _execute(self, operation: Callable[[], T], resource: str) -> T:
        try:
            return operation()
        except ApiException as exc:
            logger.exception("Kubernetes API request failed for %s", resource)
            self._translate_exception(exc, resource)

    @staticmethod
    def _translate_exception(exc: ApiException, resource: str) -> NoReturn:
        if exc.status == 404:
            match resource:
                case ResourceType.NAMESPACE:
                    raise NamespaceNotFoundError() from exc
                case ResourceType.POD:
                    raise PodNotFoundError() from exc
                case ResourceType.DEPLOYMENT:
                    raise DeploymentNotFoundError() from exc

        raise KubernetesConnectionError() from exc
