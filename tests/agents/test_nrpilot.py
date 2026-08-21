from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from app.agents.nrpilot import NRPilotAgent, build_nrpilot_agent
from app.core.settings import Settings
from app.models.agents.nrpilot import ConversationMessage
from app.services.documentation.service import DocumentationService
from app.services.kubernetes.service import KubernetesService


class FakeMessage:
    content = "The api pod is running."


class FakeDeepAgent:
    def invoke(self, request: object) -> dict[str, list[FakeMessage]]:
        assert request == {"messages": [{"role": "user", "content": "Is api healthy?"}]}
        return {"messages": [FakeMessage()]}


class FakeStreamingDeepAgent:
    async def astream(
        self, request: object, *, stream_mode: str
    ) -> AsyncIterator[dict[str, Any] | Any]:
        assert request == {"messages": [{"role": "user", "content": "Is api healthy?"}]}
        assert stream_mode == "messages"
        yield FakeMessage(), {}
        yield type("EmptyMessage", (), {"content": ""})(), {}


def test_nrpilot_agent_returns_final_message() -> None:
    agent = NRPilotAgent(FakeDeepAgent())

    assert agent.ask("Is api healthy?") == "The api pod is running."


def test_nrpilot_agent_includes_conversation_history() -> None:
    deep_agent = Mock()
    deep_agent.invoke.return_value = {"messages": [FakeMessage()]}
    agent = NRPilotAgent(deep_agent)

    agent.ask(
        "What should I check next?",
        [
            ConversationMessage(role="user", content="Is api healthy?"),
            ConversationMessage(role="assistant", content="The api pod is running."),
        ],
    )

    assert deep_agent.invoke.call_args.args[0] == {
        "messages": [
            {"role": "user", "content": "Is api healthy?"},
            {"role": "assistant", "content": "The api pod is running."},
            {"role": "user", "content": "What should I check next?"},
        ]
    }


@pytest.mark.asyncio
async def test_nrpilot_agent_streams_generated_message_chunks() -> None:
    agent = NRPilotAgent(FakeStreamingDeepAgent())

    assert [chunk async for chunk in agent.stream("Is api healthy?")] == [
        "The api pod is running."
    ]


@pytest.mark.asyncio
async def test_nrpilot_agent_stream_includes_conversation_history() -> None:
    deep_agent = Mock()

    async def astream(
        request: object, *, stream_mode: str
    ) -> AsyncIterator[dict[str, Any] | Any]:
        assert stream_mode == "messages"
        assert request == {
            "messages": [
                {"role": "user", "content": "Is api healthy?"},
                {"role": "assistant", "content": "The api pod is running."},
                {"role": "user", "content": "What should I check next?"},
            ]
        }
        yield FakeMessage(), {}

    deep_agent.astream = astream
    agent = NRPilotAgent(deep_agent)

    assert [
        chunk
        async for chunk in agent.stream(
            "What should I check next?",
            [
                ConversationMessage(role="user", content="Is api healthy?"),
                ConversationMessage(
                    role="assistant", content="The api pod is running."
                ),
            ],
        )
    ] == ["The api pod is running."]


def test_build_nrpilot_agent_raises_without_token() -> None:
    settings = Settings(
        kubernetes_host="http://localhost",
        nrp_llm_token=None,
        nrp_llm_base_url="http://localhost",
        model="qwen",
    )
    kubernetes_service = Mock(spec=KubernetesService)
    documentation_service = Mock(spec=DocumentationService)

    with pytest.raises(RuntimeError, match="NRP_LLM_TOKEN"):
        build_nrpilot_agent(kubernetes_service, documentation_service, settings)


def test_build_nrpilot_agent_constructs_chat_model_with_secret_token() -> None:
    settings = Settings(
        kubernetes_host="http://localhost",
        nrp_llm_token=SecretStr("supersecret"),
        nrp_llm_base_url="http://localhost",
        model="qwen",
    )
    kubernetes_service = Mock(spec=KubernetesService)
    documentation_service = Mock(spec=DocumentationService)

    with patch("app.agents.nrpilot.create_deep_agent") as mock_create:
        build_nrpilot_agent(kubernetes_service, documentation_service, settings)

    chat_model = mock_create.call_args.kwargs["model"]
    assert chat_model.model_name == "qwen"
    assert chat_model.openai_api_key.get_secret_value() == "supersecret"
