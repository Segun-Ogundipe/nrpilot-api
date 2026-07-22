import pytest
from pydantic import SecretStr

from app.core.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        kubernetes_host="http://localhost",
        kubernetes_api_key=SecretStr("qwertyuiop"),
        nrp_llm_token=SecretStr("qwertyuiop"),
        nrp_llm_base_url="http://localhost",
        model="qwen",
    )
