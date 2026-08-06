from datetime import datetime
from typing import TypeVar

from kubernetes.client import ApiException
from kubernetes.client.models import (
    CoreV1Event,
    V1Deployment,
    V1DeploymentCondition,
    V1DeploymentStatus,
    V1Namespace,
    V1ObjectMeta,
    V1ObjectReference,
    V1Pod,
    V1PodSpec,
    V1PodStatus,
)

from app.adapters.kubernetes.client import KubernetesClient
from app.core.settings import Settings
from app.models.kubernetes.models import (
    KubernetesClientError,
    Namespace,
    Pod,
    ResourceQuota,
    ResourceUsage,
)
from tests.adapters.kubernetes.conftest import KubernetesMocks

E = TypeVar("E", bound=BaseException, default=BaseException)


def test_initializes_clients(
    settings: Settings, mock_k8s_clients: KubernetesMocks
) -> None:
    KubernetesClient(settings)

    mock_k8s_clients.config.assert_called_once_with(settings)
    mock_k8s_clients.core.assert_called_once()
    mock_k8s_clients.apps.assert_called_once()


def test_list_namespaces(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    namespaces = [
        V1Namespace(metadata=V1ObjectMeta(name="default")),
        V1Namespace(metadata=V1ObjectMeta(name="kube-system")),
    ]

    core = mock_k8s_clients.core.return_value

    core.list_namespace.return_value.items = namespaces

    result = kubernetes_client.list_namespaces()

    assert result == [Namespace(name="default"), Namespace(name="kube-system")]

    core.list_namespace.assert_called_once_with()


def test_list_namespaces_error(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    client_error = KubernetesClientError(
        code=403,
        status="Failed",
        reason="Forbidden",
        message="User has no access to the resource",
        resource="Namespace",
    )

    core = mock_k8s_clients.core.return_value
    core.list_namespace.return_value = client_error

    result = kubernetes_client.list_namespaces()

    assert result.code == 403  # type: ignore[union-attr]
    assert result.status == "Failed"  # type: ignore[union-attr]
    assert result.reason == "Forbidden"  # type: ignore[union-attr]
    assert result.message == "User has no access to the resource"  # type: ignore[union-attr]
    assert result.resource == "Namespace"  # type: ignore[union-attr]


def test_list_pods(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    pods = [
        V1Pod(
            metadata=V1ObjectMeta(name="api", namespace="default"),
            status=V1PodStatus(phase="Running", pod_ip="some-ip"),
            spec=V1PodSpec(node_name="pod-wert", containers=""),
        )
    ]

    core = mock_k8s_clients.core.return_value

    core.list_namespaced_pod.return_value.items = pods

    result = kubernetes_client.list_pods("default")

    assert result == [
        Pod(
            name="api",
            namespace="default",
            phase="Running",
            node_name="pod-wert",
            pod_ip="some-ip",
        )
    ]

    core.list_namespaced_pod.assert_called_once_with("default")


def test_list_pods_error(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    client_error = KubernetesClientError(
        code=403,
        status="Failed",
        reason="Forbidden",
        message="User has no access to the resource",
        resource="Pod",
    )

    core = mock_k8s_clients.core.return_value
    core.list_namespaced_pod.return_value = client_error

    result = kubernetes_client.list_pods("default")

    assert result.code == 403  # type: ignore[union-attr]
    assert result.status == "Failed"  # type: ignore[union-attr]
    assert result.reason == "Forbidden"  # type: ignore[union-attr]
    assert result.message == "User has no access to the resource"  # type: ignore[union-attr]
    assert result.resource == "Pod"  # type: ignore[union-attr]


def test_describe_pod(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    pod = V1Pod(
        metadata=V1ObjectMeta(name="api", namespace="default"),
        status=V1PodStatus(phase="Running", pod_ip="some-ip"),
        spec=V1PodSpec(node_name="pod-wert", containers=""),
    )

    core = mock_k8s_clients.core.return_value

    core.read_namespaced_pod.return_value = pod

    result = kubernetes_client.describe_pod("default", "api")

    assert result.name == "api"
    assert result.phase == "Running"
    assert result.namespace == "default"

    core.read_namespaced_pod.assert_called_once_with(name="api", namespace="default")


def test_describe_pod_error(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    client_error = KubernetesClientError(
        code=403,
        status="Failed",
        reason="Forbidden",
        message="User has no access to the resource",
        resource="Pod",
    )

    core = mock_k8s_clients.core.return_value
    core.read_namespaced_pod.return_value = client_error

    result = kubernetes_client.describe_pod("api", "pod1")

    assert result.code == 403
    assert result.status == "Failed"
    assert result.reason == "Forbidden"
    assert result.message == "User has no access to the resource"
    assert result.resource == "Pod"


def test_list_pod_events(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    event = CoreV1Event(
        type="Warning",
        reason="BackOff",
        message="Back-off restarting failed container",
        count=3,
        involved_object=V1ObjectReference(kind="Pod", name="api", namespace="default"),
        metadata=V1ObjectMeta(name="api.123", namespace="default"),
    )
    core = mock_k8s_clients.core.return_value
    core.list_namespaced_event.return_value.items = [event]

    events = kubernetes_client.list_pod_events("default", "api")

    assert events[0].reason == "BackOff"
    assert events[0].count == 3
    core.list_namespaced_event.assert_called_once_with(
        "default", field_selector="involvedObject.kind=Pod,involvedObject.name=api"
    )


def test_list_pod_events_error(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    client_error = KubernetesClientError(
        code=403,
        status="Failed",
        reason="Forbidden",
        message="User has no access to the resource",
        resource="Pod",
    )

    core = mock_k8s_clients.core.return_value
    core.list_namespaced_event.return_value = client_error

    result = kubernetes_client.list_pod_events("api", "pod1")

    assert result.code == 403  # type: ignore[union-attr]
    assert result.status == "Failed"  # type: ignore[union-attr]
    assert result.reason == "Forbidden"  # type: ignore[union-attr]
    assert result.message == "User has no access to the resource"  # type: ignore[union-attr]
    assert result.resource == "Pod"  # type: ignore[union-attr]


def test_get_logs(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    core = mock_k8s_clients.core.return_value

    core.read_namespaced_pod_log.return_value = "hello"

    logs = kubernetes_client.get_pod_log("default", "api", tail_lines=50)

    assert logs == "hello"

    core.read_namespaced_pod_log.assert_called_once_with(
        name="api", namespace="default", tail_lines=50
    )


def test_list_deployments(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    deployments = [
        V1Deployment(
            metadata=(V1ObjectMeta(name="api-dep", namespace="default")),
            status=V1DeploymentStatus(
                replicas=1,
                available_replicas=1,
                unavailable_replicas=1,
                ready_replicas=1,
                conditions=[
                    V1DeploymentCondition(
                        last_transition_time=datetime.now(),
                        last_update_time=datetime.now(),
                        message="some message",
                        reason="some reason",
                        status="some status",
                        type="some type",
                    )
                ],
            ),
        )
    ]

    apps = mock_k8s_clients.apps.return_value

    apps.list_namespaced_deployment.return_value.items = deployments

    result = kubernetes_client.list_deployments("default")

    assert len(result) == 1
    assert result[0].name == "api-dep"
    assert result[0].namespace == "default"
    assert result[0].ready_replicas == 1
    assert result[0].conditions[0].message == "some message"

    apps.list_namespaced_deployment.assert_called_once_with("default")


def test_list_namespace_events(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    core = mock_k8s_clients.core.return_value
    core.list_namespaced_event.return_value.items = [
        CoreV1Event(
            type="Warning",
            reason="BackOff",
            message="message",
            count=2,
            involved_object=V1ObjectReference(
                kind="Pod", name="api", namespace="default"
            ),
            metadata=V1ObjectMeta(name="api.123", namespace="default"),
        )
    ]

    result = kubernetes_client.list_namespace_events("default")

    assert len(result) == 1
    assert result[0].reason == "BackOff"
    core.list_namespaced_event.assert_called_once_with("default")


def test_list_namespace_events_error(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    client_error = KubernetesClientError(
        code=403,
        status="Failed",
        reason="Forbidden",
        message="User has no access to the resource",
        resource="Namespace",
    )

    core = mock_k8s_clients.core.return_value
    core.list_namespaced_event.return_value = client_error

    result = kubernetes_client.list_namespace_events("api")

    assert result.code == 403  # type: ignore[union-attr]
    assert result.status == "Failed"  # type: ignore[union-attr]
    assert result.reason == "Forbidden"  # type: ignore[union-attr]
    assert result.message == "User has no access to the resource"  # type: ignore[union-attr]
    assert result.resource == "Namespace"  # type: ignore[union-attr]


def test_get_resource_usage(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    pod = V1Pod(
        metadata=V1ObjectMeta(name="api", namespace="default"),
        spec=V1PodSpec(
            node_name="node-a",
            containers=[
                type(
                    "Container",
                    (),
                    {
                        "name": "main",
                        "resources": type(
                            "Resources",
                            (),
                            {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "500m", "memory": "512Mi"},
                            },
                        )(),
                    },
                )()
            ],
        ),
    )
    core = mock_k8s_clients.core.return_value
    core.list_namespaced_pod.return_value.items = [pod]

    result = kubernetes_client.get_resource_usage("default")

    assert isinstance(result, ResourceUsage)
    assert result.namespace == "default"
    assert result.pod_count == 1
    assert result.cpu_requests == {"main": "100m"}
    assert result.memory_requests == {"main": "128Mi"}
    assert result.cpu_limits == {"main": "500m"}
    assert result.memory_limits == {"main": "512Mi"}


def test_list_resource_quotas(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    core = mock_k8s_clients.core.return_value
    core.list_namespaced_resource_quota.return_value.items = [
        type(
            "Quota",
            (),
            {
                "metadata": type(
                    "Meta", (), {"name": "quota", "namespace": "default"}
                )(),
                "spec": type("Spec", (), {"hard": {"cpu": "1"}})(),
                "status": type("Status", (), {"used": {"cpu": "500m"}})(),
            },
        )()
    ]

    result = kubernetes_client.list_resource_quotas("default")

    assert result == [
        ResourceQuota(
            name="quota",
            namespace="default",
            hard={"cpu": "1"},
            used={"cpu": "500m"},
        )
    ]


def test_list_nodes(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    core = mock_k8s_clients.core.return_value
    core.list_node.return_value.items = [
        type(
            "Node",
            (),
            {
                "metadata": type(
                    "Meta",
                    (),
                    {
                        "name": "node-1",
                        "labels": {"node-role.kubernetes.io/worker": "true"},
                    },
                )(),
                "status": type(
                    "Status",
                    (),
                    {
                        "conditions": [
                            type(
                                "Condition",
                                (),
                                {
                                    "type": "Ready",
                                    "status": "True",
                                    "last_transition_time": datetime.now(),
                                    "last_heartbeat_time": datetime.now(),
                                    "reason": "Pending",
                                    "message": "Pending",
                                },
                            )()
                        ],
                        "node_info": type(
                            "NodeInfo", (), {"kubelet_version": "v1.31.0"}
                        )(),
                    },
                )(),
            },
        )()
    ]

    result = kubernetes_client.list_nodes()

    assert result[0].name == "node-1"
    assert result[0].conditions[0].type == "Ready"
    assert result[0].roles == ["true"]


def test_execute_returns_client_error_on_api_exception(
    kubernetes_client: KubernetesClient, mock_k8s_clients: KubernetesMocks
) -> None:
    exc = ApiException(status=404, reason="Not Found")
    exc.body = type(
        "Body",
        (),
        {
            "status": "Failure",
            "message": "missing",
            "details": type("Details", (), {"kind": "Pod"})(),
        },
    )()

    def raise_exc() -> None:
        raise exc

    result = kubernetes_client._execute(raise_exc, "pod")

    assert isinstance(result, KubernetesClientError)
    assert result.code == 404
    assert result.reason == "Not Found"
    assert result.resource == "Pod"
