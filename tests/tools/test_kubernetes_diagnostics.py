from unittest.mock import Mock

from app.models.kubernetes.models import KubernetesEvent, Pod
from app.tools.kubernetes_diagnostics import build_diagnostics_tools


def test_diagnostics_tools_delegate_to_service() -> None:
    service = Mock()
    service.list_pods.return_value = [
        Pod(name="api", namespace="default", phase="Running")
    ]
    service.get_pod.return_value = Pod(name="api", namespace="default", phase="Running")
    service.list_pod_events.return_value = [KubernetesEvent(reason="BackOff")]
    tools = {tool.name: tool for tool in build_diagnostics_tools(service)}

    assert '"name":"api"' in tools["list_pods"].invoke({"namespace": "default"})
    assert '"reason":"BackOff"' in tools["list_pod_events"].invoke(
        {"namespace": "default", "pod_name": "api"}
    )
    tools["describe_pod"].invoke({"namespace": "default", "pod_name": "api"})

    service.list_pods.assert_called_once_with("default")
    service.get_pod.assert_called_once_with("default", "api")
    service.list_pod_events.assert_called_once_with("default", "api")
