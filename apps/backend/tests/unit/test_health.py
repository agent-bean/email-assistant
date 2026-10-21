import pytest
from fastapi.testclient import TestClient

from email_assistant.api.main import app

pytestmark = pytest.mark.unit


def test_liveness_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    schema = app.openapi()
    assert schema["components"]["schemas"]["Health"]["properties"]["status"]["const"] == "ok"
