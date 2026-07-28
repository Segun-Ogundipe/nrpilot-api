from collections.abc import Callable
from enum import StrEnum
from typing import Any, TypeVar

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from app.adapters.kubernetes.config import load_kubernetes_config
from app.core.logging import get_logger
from app.core.settings import Settings
from app.domain.kubernetes.ports import KubernetesClientPort
from app.models.kubernetes.models import (
    Deployment,
    DeploymentCondition,
    KubernetesClientError,
    KubernetesEvent,
    Namespace,
    NodeCondition,
    NodeStatus,
    Pod,
    ResourceQuota,
    ResourceUsage,
)

logger = get_logger(__name__)

T = TypeVar("T")


class ResourceType(StrEnum):
    NAMESPACE = "namespace"
    POD = "pod"
    DEPLOYMENT = "deployment"
    NODE = "node"


class KubernetesClient(KubernetesClientPort):
    def __init__(self, settings: Settings) -> None:
        api_client = load_kubernetes_config(settings)

        self._core = client.CoreV1Api(api_client)
        self._apps = client.AppsV1Api(api_client)

    def list_namespaces(self) -> list[Namespace] | KubernetesClientError:
        k8s_namespaces = self._execute(
            lambda: self._core.list_namespace(), resource=ResourceType.NAMESPACE
        )

        if isinstance(k8s_namespaces, KubernetesClientError):
            return k8s_namespaces

        return [
            Namespace(name=namespace.metadata.name)
            for namespace in k8s_namespaces.items
        ]

    def list_pods(self, namespace: str) -> list[Pod] | KubernetesClientError:
        k8s_pods = self._execute(
            lambda: self._core.list_namespaced_pod(namespace),
            resource=ResourceType.NAMESPACE,
        )

        if isinstance(k8s_pods, KubernetesClientError):
            return k8s_pods

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

    def describe_pod(
        self, namespace: str, pod_name: str
    ) -> Pod | KubernetesClientError:
        k8s_pod = self._execute(
            lambda: self._core.read_namespaced_pod(name=pod_name, namespace=namespace),
            resource=ResourceType.POD,
        )

        if isinstance(k8s_pod, KubernetesClientError):
            return k8s_pod

        return Pod(
            name=k8s_pod.metadata.name,
            namespace=k8s_pod.metadata.namespace,
            phase=k8s_pod.status.phase,
            node_name=k8s_pod.spec.node_name,
            pod_ip=k8s_pod.status.pod_ip,
        )

    def list_pod_events(
        self, namespace: str, pod_name: str
    ) -> list[KubernetesEvent] | KubernetesClientError:
        k8s_events = self._execute(
            lambda: self._core.list_namespaced_event(
                namespace,
                field_selector=f"involvedObject.kind=Pod,involvedObject.name={pod_name}",
            ),
            resource=ResourceType.NAMESPACE,
        )

        if isinstance(k8s_events, KubernetesClientError):
            return k8s_events

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

    def list_namespace_events(
        self, namespace: str
    ) -> list[KubernetesEvent] | KubernetesClientError:
        k8s_events = self._execute(
            lambda: self._core.list_namespaced_event(namespace),
            resource=ResourceType.NAMESPACE,
        )

        if isinstance(k8s_events, KubernetesClientError):
            return k8s_events

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

    def list_resource_quotas(
        self, namespace: str
    ) -> list[ResourceQuota] | KubernetesClientError:
        k8s_quotas = self._execute(
            lambda: self._core.list_namespaced_resource_quota(namespace),
            resource=ResourceType.NAMESPACE,
        )

        if isinstance(k8s_quotas, KubernetesClientError):
            return k8s_quotas

        return [
            ResourceQuota(
                name=quota.metadata.name,
                namespace=quota.metadata.namespace,
                hard=dict(getattr(getattr(quota, "spec", None), "hard", None) or {}),
                used=dict(getattr(getattr(quota, "status", None), "used", None) or {}),
            )
            for quota in k8s_quotas.items
        ]

    def get_resource_usage(
        self, namespace: str
    ) -> ResourceUsage | KubernetesClientError:
        k8s_pods = self._execute(
            lambda: self._core.list_namespaced_pod(namespace),
            resource=ResourceType.NAMESPACE,
        )

        if isinstance(k8s_pods, KubernetesClientError):
            return k8s_pods

        cpu_requests: dict[str, str] = {}
        memory_requests: dict[str, str] = {}
        cpu_limits: dict[str, str] = {}
        memory_limits: dict[str, str] = {}

        for pod in k8s_pods.items:
            for container in getattr(pod.spec, "containers", None) or []:
                self._merge_resource_usage(
                    container,
                    cpu_requests,
                    memory_requests,
                    cpu_limits,
                    memory_limits,
                )

        return ResourceUsage(
            namespace=namespace,
            pod_count=len(k8s_pods.items),
            cpu_requests=cpu_requests,
            memory_requests=memory_requests,
            cpu_limits=cpu_limits,
            memory_limits=memory_limits,
        )

    def list_nodes(self) -> list[NodeStatus] | KubernetesClientError:
        k8s_nodes = self._execute(
            lambda: self._core.list_node(), resource=ResourceType.NODE
        )

        if isinstance(k8s_nodes, KubernetesClientError):
            return k8s_nodes

        return [
            NodeStatus(
                name=node.metadata.name,
                roles=self._node_roles(node),
                version=node.status.node_info.kubelet_version,
                conditions=[
                    NodeCondition(
                        last_transition_time=condition.last_transition_time,
                        last_heartbeat_time=condition.last_heartbeat_time,
                        message=condition.message,
                        reason=condition.reason,
                        status=condition.status,
                        type=condition.type,
                    )
                    for condition in node.status.conditions or []
                ],
            )
            for node in k8s_nodes.items
        ]

    def get_pod_log(
        self, namespace: str, pod_name: str, tail_lines: int | None = None
    ) -> Any:
        log = self._execute(
            lambda: self._core.read_namespaced_pod_log(
                namespace=namespace, name=pod_name, tail_lines=tail_lines
            ),
            resource=ResourceType.POD,
        )

        return log

    def list_deployments(
        self, namespace: str
    ) -> list[Deployment] | KubernetesClientError:
        k8s_deployments = self._execute(
            lambda: self._apps.list_namespaced_deployment(namespace),
            resource=ResourceType.DEPLOYMENT,
        )

        if isinstance(k8s_deployments, KubernetesClientError):
            return k8s_deployments

        return [
            Deployment(
                name=deployment.metadata.name,
                namespace=deployment.metadata.namespace,
                ready_replicas=deployment.status.ready_replicas,
                replicas=deployment.status.replicas,
                available_replicas=deployment.status.available_replicas,
                unavailable_replicas=deployment.status.unavailable_replicas,
                conditions=[
                    DeploymentCondition(
                        last_transition_time=condition.last_transition_time,
                        last_update_time=condition.last_update_time,
                        message=condition.message,
                        reason=condition.reason,
                        status=condition.status,
                        type=condition.type,
                    )
                    for condition in deployment.status.conditions or []
                ],
            )
            for deployment in k8s_deployments.items
        ]

    @staticmethod
    def _merge_resource_usage(
        container: Any,
        cpu_requests: dict[str, str],
        memory_requests: dict[str, str],
        cpu_limits: dict[str, str],
        memory_limits: dict[str, str],
    ) -> None:
        container_requests = getattr(container.resources, "requests", None) or {}
        container_limits = getattr(container.resources, "limits", None) or {}

        if "cpu" in container_requests:
            cpu_requests[container.name] = container_requests["cpu"]
        if "memory" in container_requests:
            memory_requests[container.name] = container_requests["memory"]

        if "cpu" in container_limits:
            cpu_limits[container.name] = container_limits["cpu"]
        if "memory" in container_limits:
            memory_limits[container.name] = container_limits["memory"]

    @staticmethod
    def _node_roles(node: Any) -> list[str]:
        labels = getattr(node.metadata, "labels", None) or {}
        role_labels = [
            value
            for key, value in labels.items()
            if key == "kubernetes.io/role" or key.startswith("node-role.kubernetes.io/")
        ]
        if not role_labels:
            return []
        return [role for role in role_labels if role]

    def _execute(
        self, operation: Callable[[], T], resource: str
    ) -> T | KubernetesClientError:
        try:
            return operation()
        except ApiException as exc:
            reason = exc.reason
            body = exc.body or str(exc)
            logger.exception(
                "Kubernetes API request failed for resource: %s, reason: %s, response body: %s",
                resource,
                reason,
                body,
            )
            code = exc.status
            status = getattr(exc.body, "status", None)
            message = getattr(exc.body, "message", None)
            kind = getattr(getattr(exc.body, "details", None), "kind", None)
            return KubernetesClientError(
                code=code,
                status=status,
                reason=exc.reason,
                message=message,
                resource=kind,
            )
