from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.adapters.kubernetes.exceptions import (
    KubernetesConnectionError,
    NamespaceNotFoundError,
)
from app.dependencies import (
    get_conversation_service,
    get_kubernetes_service,
    get_nrpilot_agent,
)
from app.main import app
from app.models.agents.nrpilot import ConversationMessage
from app.models.kubernetes.models import KubernetesEvent, Pod
from app.services.conversations.service import ConversationService


class FakeNRPilotAgent:
    def ask(self, question: str, history: object = None) -> str:
        assert question == "Why is api failing?"
        return "The api pod has restart warnings."

    async def stream(self, question: str, history: object = None) -> AsyncIterator[str]:
        assert question == "Why is api failing?"
        yield "The api pod "
        yield "has restart warnings."


class FollowUpAgent:
    def __init__(self) -> None:
        self.histories: list[list[ConversationMessage] | None] = []

    def ask(
        self, question: str, history: list[ConversationMessage] | None = None
    ) -> str:
        self.histories.append(history)
        return f"answer to {question}"

    async def stream(
        self, question: str, history: list[ConversationMessage] | None = None
    ) -> AsyncIterator[str]:
        self.histories.append(history)
        yield f"answer to {question}"


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

    assert chat.json()["answer"] == "The api pod has restart warnings."
    assert "conversation_id" in chat.json()


def test_nrpilot_stream_endpoint_returns_sse_chunks() -> None:
    app.dependency_overrides[get_nrpilot_agent] = lambda: FakeNRPilotAgent()

    try:
        with TestClient(app) as client:
            with client.stream(
                "POST", "/api/v1/chat/stream", json={"question": "Why is api failing?"}
            ) as response:
                body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.clear()

    assert response.headers["content-type"].startswith("text/event-stream")
    assert body.startswith('event: conversation\ndata: {"conversation_id": "')
    assert 'event: message\ndata: {"answer": "The api pod "}\n\n' in body
    assert 'event: message\ndata: {"answer": "has restart warnings."}\n\n' in body
    assert body.endswith("event: done\ndata: {}\n\n")


def test_nrpilot_endpoint_streams_when_sse_is_accepted() -> None:
    app.dependency_overrides[get_nrpilot_agent] = lambda: FakeNRPilotAgent()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat",
                headers={"Accept": "text/event-stream"},
                json={"question": "Why is api failing?"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: message\ndata: {"answer": "The api pod "}' in response.text
    assert response.text.endswith("event: done\ndata: {}\n\n")


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


def test_nrpilot_endpoint_preserves_context_for_follow_up() -> None:
    agent = FollowUpAgent()
    conversation_service = ConversationService()
    app.dependency_overrides[get_nrpilot_agent] = lambda: agent
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service

    try:
        with TestClient(app) as client:
            first_response = client.post(
                "/api/v1/chat", json={"question": "Why is api failing?"}
            )
            second_response = client.post(
                "/api/v1/chat",
                json={
                    "question": "What should I check next?",
                    "conversation_id": first_response.json()["conversation_id"],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert (
        second_response.json()["conversation_id"]
        == first_response.json()["conversation_id"]
    )
    assert agent.histories[1] == [
        ConversationMessage(role="user", content="Why is api failing?"),
        ConversationMessage(role="assistant", content="answer to Why is api failing?"),
    ]
