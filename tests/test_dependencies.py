from unittest.mock import MagicMock, patch

from app.core.settings import Settings
from app.dependencies import (
    get_documentation_service,
    get_kubernetes_client,
    get_kubernetes_service,
    get_nrpilot_agent,
    get_settings,
)
from app.services.documentation.service import DocumentationService
from app.services.kubernetes.service import KubernetesService


def test_get_settings_is_cached(settings: Settings) -> None:
    first = get_settings()
    second = get_settings()

    assert first is second


def test_get_kubernetes_client_and_service(settings: Settings) -> None:
    with patch("app.dependencies.KubernetesClient") as client_cls:
        client = MagicMock()
        client_cls.return_value = client

        resolved_client = get_kubernetes_client(settings)
        resolved_service = get_kubernetes_service(resolved_client)

    assert resolved_client is client
    assert isinstance(resolved_service, KubernetesService)


def test_get_documentation_service() -> None:
    with patch("app.dependencies.NRPDocumentationClient") as client_cls:
        client = MagicMock()
        client_cls.return_value = client

        service = get_documentation_service()

    assert isinstance(service, DocumentationService)


def test_get_nrpilot_agent(settings: Settings) -> None:
    kubernetes_service = MagicMock()
    documentation_service = MagicMock()

    with patch("app.dependencies.build_nrpilot_agent") as build_agent:
        agent = MagicMock()
        build_agent.return_value = agent

        resolved_agent = get_nrpilot_agent(
            kubernetes_service,
            documentation_service,
            settings,
        )

    assert resolved_agent is agent
