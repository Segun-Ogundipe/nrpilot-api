import json
from collections.abc import Sequence
from typing import Any

from langchain.tools import tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.kubernetes.service import KubernetesService

logger = get_logger(__name__)


def build_diagnostics_tools(service: KubernetesService) -> Sequence[BaseTool]:
    """Create the read-only Kubernetes tools available to the agent."""

    @tool
    def list_namespaces() -> str:
        """List namespaces in a Kubernetes cluster."""
        logger.info("kubernetes_tool_invoked", tool="list_namespaces")
        return _as_json(service.list_namespaces())

    @tool
    def list_pods(namespace: str) -> str:
        """List pods in a Kubernetes namespace and their current status."""
        logger.info("kubernetes_tool_invoked", tool="list_pods", namespace=namespace)
        return _as_json(service.list_pods(namespace))

    @tool
    def describe_pod(namespace: str, pod_name: str) -> Any:
        """Get the status, node, and IP address for one Kubernetes pod."""
        logger.info(
            "kubernetes_tool_invoked",
            tool="describe_pod",
            namespace=namespace,
            pod_name=pod_name,
        )
        return _as_json(service.get_pod(namespace, pod_name))

    @tool
    def list_pod_events(namespace: str, pod_name: str) -> str:
        """List recent Kubernetes warning and normal events for one pod."""
        logger.info(
            "kubernetes_tool_invoked",
            tool="list_pod_events",
            namespace=namespace,
            pod_name=pod_name,
        )
        return _as_json(service.list_pod_events(namespace, pod_name))

    @tool
    def list_namespace_events(namespace: str) -> str:
        """List recent Kubernetes events for a namespace that can reveal scheduling, image pull, and crash-loop issues."""
        logger.info(
            "kubernetes_tool_invoked",
            tool="list_namespace_events",
            namespace=namespace,
        )
        return _as_json(service.list_namespace_events(namespace))

    @tool
    def list_resource_quotas(namespace: str) -> str:
        """List resource quotas and their current usage for a namespace."""
        logger.info(
            "kubernetes_tool_invoked",
            tool="list_resource_quotas",
            namespace=namespace,
        )
        return _as_json(service.list_resource_quotas(namespace))

    @tool
    def get_resource_usage(namespace: str) -> str:
        """Summarize current pod counts and requested/limited CPU and memory usage for a namespace."""
        logger.info(
            "kubernetes_tool_invoked",
            tool="get_resource_usage",
            namespace=namespace,
        )
        return _as_json(service.get_resource_usage(namespace))

    @tool
    def list_nodes() -> str:
        """List node readiness and status information for the cluster."""
        logger.info("kubernetes_tool_invoked", tool="list_nodes")
        return _as_json(service.list_nodes())

    @tool
    def get_pod_log(namespace: str, pod_name: str, tail_lines: int) -> Any:
        """Get the log for one Kubernetes pod."""
        logger.info(
            "kubernetes_tool_invoked",
            tool="get_pod_log",
            namespace=namespace,
            pod_name=pod_name,
            tail_lines=tail_lines,
        )
        return service.get_pod_log(namespace, pod_name, tail_lines)

    @tool
    def list_deployments(namespace: str) -> str:
        """List the deployments in a Kubernetes cluster."""
        logger.info(
            "kubernetes_tool_invoked",
            tool="list_deployments",
            namespace=namespace,
        )
        return _as_json(service.list_deployments(namespace))

    return (
        list_namespaces,
        list_pods,
        describe_pod,
        list_pod_events,
        list_namespace_events,
        list_resource_quotas,
        get_resource_usage,
        list_nodes,
        get_pod_log,
        list_deployments,
    )


def _as_json(items: Sequence[BaseModel] | BaseModel) -> str:
    if isinstance(items, BaseModel):
        return str(items.model_dump_json())

    if isinstance(items, Sequence) and not isinstance(items, (str, bytes, bytearray)):
        return "[" + ",".join(_as_json(item) for item in items) + "]"

    return json.dumps(items)
