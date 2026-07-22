from pydantic import SecretStr

from app.adapters.kubernetes.config import load_kubernetes_config
from app.core.settings import Settings


def test_load_local(settings: Settings) -> None:
    api_client = load_kubernetes_config(settings)

    assert api_client.configuration.api_key == {"BearerToken": "Bearer qwertyuiop"}
    assert api_client.configuration.host == "http://localhost"


def test_load_local_without_api_key() -> None:
    settings = Settings(kubernetes_host="http://localhost")

    api_client = load_kubernetes_config(settings)

    assert "BearerToken" not in api_client.configuration.api_key


def test_secret_value_is_not_leaked_through_repr() -> None:
    settings = Settings(
        kubernetes_host="http://localhost",
        kubernetes_api_key=SecretStr("qwertyuiop"),
        nrp_llm_token=SecretStr("supersecret"),
    )

    assert "supersecret" not in repr(settings)
    assert "qwertyuiop" not in repr(settings)
