from fastapi.testclient import TestClient
from httpx2 import Response

from app.main import app

client = TestClient(app)


def test_health() -> None:
    """Test health check endpoint returns 200 and includes request ID."""
    response: Response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "x-request-id" in response.headers
    request_id = response.headers["x-request-id"]
    assert len(request_id) == 36
    assert request_id.count("-") == 4
