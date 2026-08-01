from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["application"] == "Chatbot Layanan Akademik"


def test_readiness_does_not_expose_credentials() -> None:
    response = client.get("/readiness")

    assert response.status_code == 200
    body = response.json()
    serialized = str(body).lower()

    assert "mysql+pymysql://" not in serialized
    assert body["status"] in {"ready", "not_ready"}
