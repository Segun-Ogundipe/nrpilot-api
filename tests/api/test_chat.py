from datetime import datetime
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.adapters.kubernetes.exceptions import (
    KubernetesConnectionError,
    NamespaceNotFoundError,
)
from app.dependencies import get_kubernetes_service, get_nrpilot_agent
from app.main import app
from app.models.kubernetes.models import KubernetesEvent, Pod


class FakeNRPilotAgent:
    def ask(self, question: str) -> str:
        assert question == "Why is api failing?"
        return "The api pod has restart warnings."


def test_nrpilot_endpoint() -> None:
    service = Mock()
    service.list_pods.return_value = [
        Pod(name="api", namespace="default", phase="Running")
    ]
    service.get_pod.return_value = Pod(name="api", namespace="default", phase="Running")
    service.list_pod_events.return_value = [
        KubernetesEvent(
            type="Warning",
            reason="BackOff",
            first_timestamp=datetime(2026, 7, 20),
        )
    ]
    app.dependency_overrides[get_kubernetes_service] = lambda: service
    app.dependency_overrides[get_nrpilot_agent] = lambda: FakeNRPilotAgent()

    try:
        with TestClient(app) as client:
            chat = client.post("/api/v1/chat", json={"question": "Why is api failing?"})
    finally:
        app.dependency_overrides.clear()

    assert chat.json() == {"answer": "The api pod has restart warnings."}


def test_nrpilot_endpoint_returns_503_on_connection_error() -> None:
    agent = Mock()
    agent.ask.side_effect = KubernetesConnectionError()

    app.dependency_overrides[get_nrpilot_agent] = lambda: agent

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat", json={"question": "Why is api failing?"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


def test_nrpilot_endpoint_returns_404_on_missing_resource() -> None:
    agent = Mock()
    agent.ask.side_effect = NamespaceNotFoundError()

    app.dependency_overrides[get_nrpilot_agent] = lambda: agent

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat", json={"question": "Why is api failing?"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
