from typing import Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from app.core.logging import get_logger
from app.core.settings import Settings
from app.models.agents.nrpilot import ConversationMessage
from app.services.documentation.service import DocumentationService
from app.services.kubernetes.service import KubernetesService
from app.tools.documentation import build_documentation_tools
from app.tools.kubernetes_diagnostics import build_diagnostics_tools

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are NRPilot, an assistant for the National Research Platform.
Use the available Kubernetes tools to ground diagnostic answers in cluster data.
Use the NRP documentation search tool for questions about NRP guidance, services,
policies, and tutorials. Cite documentation source URLs in those answers and do
not treat documentation as evidence of the user's live cluster state.
You have read-only access. Do not claim that you changed a cluster, and clearly
say when the available tools cannot answer a question. Be concise and include
the namespace and pod name for any resource you discuss."""


class NRPilotAgent:
    def __init__(self, agent: Any) -> None:
        self._agent = agent

    def ask(
        self, question: str, history: list[ConversationMessage] | None = None
    ) -> str:
        logger.info("nrpilot_agent_invoked")
        messages = [
            {"role": message.role, "content": message.content}
            for message in history or []
        ]
        messages.append({"role": "user", "content": question})
        result = self._agent.invoke({"messages": messages})
        response_messages = result["messages"]
        return _message_content(response_messages[-1].content)


def build_nrpilot_agent(
    kubernetes_service: KubernetesService,
    documentation_service: DocumentationService,
    settings: Settings,
) -> NRPilotAgent:
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
        tools=(
            *build_diagnostics_tools(kubernetes_service),
            *build_documentation_tools(documentation_service),
        ),
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
