from fastapi.testclient import TestClient
from httpx2 import Response

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response: Response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
