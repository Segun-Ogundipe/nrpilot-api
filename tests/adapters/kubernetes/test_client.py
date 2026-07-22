from datetime import datetime
from typing import TypeVar

import pytest
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
from app.adapters.kubernetes.exceptions import (
    DeploymentNotFoundError,
    KubernetesConnectionError,
    NamespaceNotFoundError,
    PodNotFoundError,
)
from app.core.settings import Settings
from app.models.kubernetes.models import Namespace, Pod
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
                conditions=V1DeploymentCondition(
                    last_transition_time=datetime.now(),
                    last_update_time=datetime.now(),
                    message="some message",
                    reason="some reason",
                    status="some status",
                    type="some type",
                ),
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
    assert result[0].condition.message == "some message"

    apps.list_namespaced_deployment.assert_called_once_with("default")


@pytest.mark.parametrize(
    ("resource", "exception"),
    [
        ("namespace", NamespaceNotFoundError),
        ("pod", PodNotFoundError),
        ("deployment", DeploymentNotFoundError),
    ],
)
def test_translate_404(resource: str, exception: type[E]) -> None:
    exc = ApiException(status=404)

    with pytest.raises(exception):
        KubernetesClient._translate_exception(exc, resource)


def test_translate_connection_error() -> None:
    exc = ApiException(status=500)

    with pytest.raises(KubernetesConnectionError):
        KubernetesClient._translate_exception(exc, "pod")
