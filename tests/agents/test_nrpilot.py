from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from app.agents.nrpilot import NRPilotAgent, build_nrpilot_agent
from app.core.settings import Settings
from app.services.kubernetes.service import KubernetesService


class FakeMessage:
    content = "The api pod is running."


class FakeDeepAgent:
    def invoke(self, request: object) -> dict[str, list[FakeMessage]]:
        assert request == {"messages": [{"role": "user", "content": "Is api healthy?"}]}
        return {"messages": [FakeMessage()]}


def test_nrpilot_agent_returns_final_message() -> None:
    agent = NRPilotAgent(FakeDeepAgent())

    assert agent.ask("Is api healthy?") == "The api pod is running."


def test_build_nrpilot_agent_raises_without_token() -> None:
    settings = Settings(
        kubernetes_host="http://localhost",
        nrp_llm_token=None,
        nrp_llm_base_url="http://localhost",
        model="qwen",
    )
    service = Mock(spec=KubernetesService)

    with pytest.raises(RuntimeError, match="NRP_LLM_TOKEN"):
        build_nrpilot_agent(service, settings)


def test_build_nrpilot_agent_constructs_chat_model_with_secret_token() -> None:
    settings = Settings(
        kubernetes_host="http://localhost",
        nrp_llm_token=SecretStr("supersecret"),
        nrp_llm_base_url="http://localhost",
        model="qwen",
    )
    service = Mock(spec=KubernetesService)

    with patch("app.agents.nrpilot.create_deep_agent") as mock_create:
        build_nrpilot_agent(service, settings)

    chat_model = mock_create.call_args.kwargs["model"]
    assert chat_model.model_name == "qwen"
    assert chat_model.openai_api_key.get_secret_value() == "supersecret"
