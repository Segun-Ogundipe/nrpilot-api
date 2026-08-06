from unittest.mock import Mock

from app.models.kubernetes.models import (
    KubernetesEvent,
    NodeStatus,
    Pod,
    ResourceQuota,
    ResourceUsage,
)
from app.tools.kubernetes_diagnostics import build_diagnostics_tools


def test_diagnostics_tools_delegate_to_service() -> None:
    service = Mock()
    service.list_pods.return_value = [
        Pod(name="api", namespace="default", phase="Running")
    ]
    service.get_pod.return_value = Pod(name="api", namespace="default", phase="Running")
    service.list_pod_events.return_value = [KubernetesEvent(reason="BackOff")]
    service.list_namespace_events.return_value = [KubernetesEvent(reason="Scheduled")]
    service.list_resource_quotas.return_value = [
        ResourceQuota(
            name="compute", namespace="default", hard={"cpu": "2"}, used={"cpu": "1"}
        )
    ]
    service.get_resource_usage.return_value = ResourceUsage(
        namespace="default",
        pod_count=2,
        cpu_requests={"cpu": "200m"},
        memory_requests={"memory": "256Mi"},
    )
    service.list_nodes.return_value = [NodeStatus(name="node-1", conditions=[])]

    tools = {tool.name: tool for tool in build_diagnostics_tools(service)}

    assert '"name":"api"' in tools["list_pods"].invoke({"namespace": "default"})
    assert '"reason":"BackOff"' in tools["list_pod_events"].invoke(
        {"namespace": "default", "pod_name": "api"}
    )
    assert '"reason":"Scheduled"' in tools["list_namespace_events"].invoke(
        {"namespace": "default"}
    )
    assert '"name":"compute"' in tools["list_resource_quotas"].invoke(
        {"namespace": "default"}
    )
    assert '"pod_count":2' in tools["get_resource_usage"].invoke(
        {"namespace": "default"}
    )
    assert '"name":"node-1"' in tools["list_nodes"].invoke({})

    tools["describe_pod"].invoke({"namespace": "default", "pod_name": "api"})

    service.list_pods.assert_called_once_with("default")
    service.get_pod.assert_called_once_with("default", "api")
    service.list_pod_events.assert_called_once_with("default", "api")
    service.list_namespace_events.assert_called_once_with("default")
    service.list_resource_quotas.assert_called_once_with("default")
    service.get_resource_usage.assert_called_once_with("default")
    service.list_nodes.assert_called_once_with()
