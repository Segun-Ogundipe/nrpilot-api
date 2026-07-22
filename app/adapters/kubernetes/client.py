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
from app.domain.kubernetes.ports import KubernetesClientPort
from app.models.kubernetes.models import (
    Deployment,
    DeploymentCondition,
    KubernetesEvent,
    Namespace,
    Pod,
)

logger = get_logger(__name__)

T = TypeVar("T")


class ResourceType(StrEnum):
    NAMESPACE = "namespace"
    POD = "pod"
    DEPLOYMENT = "deployment"


class KubernetesClient(KubernetesClientPort):
    def __init__(self, settings: Settings) -> None:
        api_client = load_kubernetes_config(settings)

        self._core = client.CoreV1Api(api_client)
        self._apps = client.AppsV1Api(api_client)

    def list_namespaces(self) -> list[Namespace]:
        k8s_namespaces = self._execute(
            lambda: self._core.list_namespace(), resource=ResourceType.NAMESPACE
        )

        return [
            Namespace(name=namespace.metadata.name)
            for namespace in k8s_namespaces.items
        ]

    def list_pods(self, namespace: str) -> list[Pod]:
        k8s_pods = self._execute(
            lambda: self._core.list_namespaced_pod(namespace),
            resource=ResourceType.NAMESPACE,
        )

        return [
            Pod(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                phase=pod.status.phase,
                node_name=pod.spec.node_name,
                pod_ip=pod.status.pod_ip,
            )
            for pod in k8s_pods.items
        ]

    def describe_pod(self, namespace: str, pod_name: str) -> Pod:
        k8s_pod = self._execute(
            lambda: self._core.read_namespaced_pod(name=pod_name, namespace=namespace),
            resource=ResourceType.POD,
        )

        return Pod(
            name=k8s_pod.metadata.name,
            namespace=k8s_pod.metadata.namespace,
            phase=k8s_pod.status.phase,
            node_name=k8s_pod.spec.node_name,
            pod_ip=k8s_pod.status.pod_ip,
        )

    def list_pod_events(self, namespace: str, pod_name: str) -> list[KubernetesEvent]:
        k8s_events = self._execute(
            lambda: self._core.list_namespaced_event(
                namespace,
                field_selector=f"involvedObject.kind=Pod,involvedObject.name={pod_name}",
            ),
            resource=ResourceType.NAMESPACE,
        )

        return [
            KubernetesEvent(
                type=event.type,
                reason=event.reason,
                message=event.message,
                count=event.count,
                first_timestamp=event.first_timestamp,
                last_timestamp=event.last_timestamp,
            )
            for event in k8s_events.items
        ]

    def get_pod_log(
        self, namespace: str, pod_name: str, tail_lines: int | None = None
    ) -> Any:
        return self._execute(
            lambda: self._core.read_namespaced_pod_log(
                namespace=namespace, name=pod_name, tail_lines=tail_lines
            ),
            resource=ResourceType.POD,
        )

    def list_deployments(self, namespace: str) -> list[Deployment]:
        k8s_deployments = self._execute(
            lambda: self._apps.list_namespaced_deployment(namespace),
            resource=ResourceType.DEPLOYMENT,
        )

        return [
            Deployment(
                name=deployment.metadata.name,
                namespace=deployment.metadata.namespace,
                ready_replicas=deployment.status.ready_replicas,
                replicas=deployment.status.replicas,
                available_replicas=deployment.status.available_replicas,
                unavailable_replicas=deployment.status.unavailable_replicas,
                condition=DeploymentCondition(
                    last_transition_time=deployment.status.conditions.last_transition_time,
                    last_update_time=deployment.status.conditions.last_update_time,
                    message=deployment.status.conditions.message,
                    reason=deployment.status.conditions.reason,
                    status=deployment.status.conditions.status,
                    type=deployment.status.conditions.type,
                ),
            )
            for deployment in k8s_deployments.items
        ]

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
