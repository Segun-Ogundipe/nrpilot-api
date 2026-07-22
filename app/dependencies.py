from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.adapters.kubernetes.client import KubernetesClient
from app.agents.nrpilot import NRPilotAgent, build_nrpilot_agent
from app.core.settings import Settings
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


def get_nrpilot_agent(
    service: Annotated[KubernetesService, Depends(get_kubernetes_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NRPilotAgent:
    return build_nrpilot_agent(service, settings)
