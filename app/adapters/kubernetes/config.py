from kubernetes.client import ApiClient, Configuration

from app.core.settings import Settings


def load_kubernetes_config(settings: Settings) -> ApiClient:
    configuration = Configuration(host=settings.kubernetes_host)

    if settings.kubernetes_api_key:
        configuration.api_key["BearerToken"] = (
            f"Bearer {settings.kubernetes_api_key.get_secret_value()}"
        )

    return ApiClient(configuration)
