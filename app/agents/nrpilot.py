from typing import Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from app.core.logging import get_logger
from app.core.settings import Settings
from app.services.kubernetes.service import KubernetesService
from app.tools.kubernetes_diagnostics import build_diagnostics_tools

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are NRPilot, a Kubernetes diagnostics assistant.
Use the available Kubernetes tools to ground diagnostic answers in cluster data.
You have read-only access. Do not claim that you changed a cluster, and clearly
say when the available tools cannot answer a question. Be concise and include
the namespace and pod name for any resource you discuss."""


class NRPilotAgent:
    def __init__(self, agent: Any) -> None:
        self._agent = agent

    def ask(self, question: str) -> str:
        logger.info("nrpilot_agent_invoked")
        result = self._agent.invoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        messages = result["messages"]
        return _message_content(messages[-1].content)


def build_nrpilot_agent(service: KubernetesService, settings: Settings) -> NRPilotAgent:
    token = settings.nrp_llm_token.get_secret_value() if settings.nrp_llm_token else ""
    if not token:
        raise RuntimeError("NRP_LLM_TOKEN must be configured to use nrpilot")

    model = ChatOpenAI(
        model=settings.model,
        api_key=settings.nrp_llm_token,
        base_url=settings.nrp_llm_base_url,
    )
    agent = create_deep_agent(
        model=model,
        tools=build_diagnostics_tools(service),
        system_prompt=SYSTEM_PROMPT,
    )
    return NRPilotAgent(agent)


def _message_content(content: str | list[str | dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    return "".join(
        block if isinstance(block, str) else str(block.get("text", ""))
        for block in content
    )
