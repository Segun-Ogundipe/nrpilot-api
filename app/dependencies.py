from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.adapters.documentation.client import NRPDocumentationClient
from app.adapters.kubernetes.client import KubernetesClient
from app.agents.nrpilot import NRPilotAgent, build_nrpilot_agent
from app.core.settings import Settings
from app.services.conversations.service import ConversationService
from app.services.documentation.service import DocumentationService
from app.services.kubernetes.service import KubernetesService


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_kubernetes_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> KubernetesClient:
    return KubernetesClient(settings)


def get_kubernetes_service(
    client: Annotated[KubernetesClient, Depends(get_kubernetes_client)],
) -> KubernetesService:
    return KubernetesService(client)


@lru_cache
def get_documentation_service() -> DocumentationService:
    settings = get_settings()
    client = NRPDocumentationClient(
        documentation_url=settings.nrp_documentation_url,
        timeout_seconds=settings.nrp_documentation_timeout_seconds,
        max_results=settings.nrp_documentation_max_results,
    )
    return DocumentationService(client)


def get_nrpilot_agent(
    kubernetes_service: Annotated[KubernetesService, Depends(get_kubernetes_service)],
    documentation_service: Annotated[
        DocumentationService, Depends(get_documentation_service)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NRPilotAgent:
    return build_nrpilot_agent(kubernetes_service, documentation_service, settings)


@lru_cache
def get_conversation_service() -> ConversationService:
    return ConversationService()
