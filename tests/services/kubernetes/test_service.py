from datetime import datetime
from unittest.mock import Mock

from app.models.kubernetes.models import (
    Deployment,
    DeploymentCondition,
    KubernetesEvent,
    Namespace,
    NodeCondition,
    NodeStatus,
    Pod,
    ResourceQuota,
    ResourceUsage,
)
from app.services.kubernetes.service import KubernetesService


def test_list_namespaces() -> None:
    client = Mock()

    client.list_namespaces.return_value = [
        Namespace(name="default"),
        Namespace(name="kube-system"),
    ]

    service = KubernetesService(client)

    namespaces = service.list_namespaces()

    assert len(namespaces) == 2
    assert namespaces[0].name == "default"

    client.list_namespaces.assert_called_once()


def test_list_pods() -> None:
    client = Mock()

    client.list_pods.return_value = [
        Pod(name="api", namespace="default", phase="Running")
    ]

    service = KubernetesService(client)

    pods = service.list_pods("default")

    assert pods[0].name == "api"

    client.list_pods.assert_called_once_with("default")


def test_get_pod() -> None:
    client = Mock()

    client.describe_pod.return_value = Pod(
        name="api", namespace="default", phase="Running"
    )

    service = KubernetesService(client)

    pod = service.get_pod("default", "api")

    assert pod.name == "api"
    assert pod.phase == "Running"

    client.describe_pod.assert_called_once_with("default", "api")


def test_list_pod_events() -> None:
    client = Mock()
    client.list_pod_events.return_value = [
        KubernetesEvent(
            reason="BackOff", message="Back-off restarting failed container"
        )
    ]
    service = KubernetesService(client)

    events = service.list_pod_events("default", "api")

    assert events[0].reason == "BackOff"
    client.list_pod_events.assert_called_once_with("default", "api")


def test_list_namespace_events() -> None:
    client = Mock()
    client.list_namespace_events.return_value = [
        KubernetesEvent(
            reason="BackOff", message="Back-off restarting failed container"
        )
    ]
    service = KubernetesService(client)

    events = service.list_namespace_events("default")

    assert events[0].reason == "BackOff"
    client.list_namespace_events.assert_called_once_with("default")


def test_list_resource_quotas() -> None:
    client = Mock()
    client.list_resource_quotas.return_value = [
        ResourceQuota(name="Pod", namespace="default", hard={}, used={})
    ]
    service = KubernetesService(client)

    quotas = service.list_resource_quotas("default")

    assert quotas[0].name == "Pod"
    assert quotas[0].namespace == "default"
    client.list_resource_quotas.assert_called_once_with("default")


def test_get_resource_usage() -> None:
    client = Mock()
    client.get_resource_usage.return_value = ResourceUsage(
        namespace="default",
        pod_count=2,
        cpu_requests={},
        memory_requests={},
        cpu_limits={},
        memory_limits={},
    )
    service = KubernetesService(client)

    usage = service.get_resource_usage("default")

    assert usage.namespace == "default"
    assert usage.pod_count == 2
    assert usage.cpu_requests == {}
    client.get_resource_usage.assert_called_once_with("default")


def test_list_nodes() -> None:
    client = Mock()
    client.list_nodes.return_value = [
        NodeStatus(
            name="pod",
            roles=[],
            version="V1",
            conditions=[
                NodeCondition(
                    last_transition_time=datetime.now(),
                    last_heartbeat_time=datetime.now(),
                    message="Pending",
                    reason="Pending",
                    status="True",
                    type="Waiting",
                )
            ],
        )
    ]
    service = KubernetesService(client)

    nodes = service.list_nodes()

    assert nodes[0].name == "pod"
    assert nodes[0].conditions[0].message == "Pending"
    assert nodes[0].conditions[0].type == "Waiting"
    client.list_nodes.assert_called_once()


def test_get_pod_log_without_tail_lines() -> None:
    client = Mock()

    client.get_pod_log.return_value = "A very long log of pod-1234"

    service = KubernetesService(client)

    pod_log = service.get_pod_log("default", "pod_name")

    assert pod_log == "A very long log of pod-1234"

    client.get_pod_log.assert_called_once_with("default", "pod_name", None)


def test_get_pod_log_with_tail_lines() -> None:
    client = Mock()

    client.get_pod_log.return_value = "A very long log of pod-1234"

    service = KubernetesService(client)

    pod_log = service.get_pod_log("default", "pod_name", 50)

    assert pod_log == "A very long log of pod-1234"

    client.get_pod_log.assert_called_once_with("default", "pod_name", 50)


def test_list_deployments() -> None:
    client = Mock()

    client.list_deployments.return_value = [
        Deployment(
            name="dep-123",
            namespace="default",
            ready_replicas=1,
            replicas=1,
            available_replicas=1,
            unavailable_replicas=1,
            conditions=[
                DeploymentCondition(
                    last_transition_time=datetime.now(),
                    last_update_time=datetime.now(),
                    message="some message",
                    reason="some reason",
                    status="some status",
                    type="some type",
                )
            ],
        )
    ]

    service = KubernetesService(client)

    deployments = service.list_deployments("default")

    assert len(deployments) == 1
    assert deployments[0].name == "dep-123"
    assert deployments[0].namespace == "default"
    assert deployments[0].replicas == 1
    assert deployments[0].conditions[0].message == "some message"
