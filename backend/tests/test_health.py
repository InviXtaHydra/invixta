from fastapi.testclient import TestClient


def test_health_reports_database_and_model_status(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "llm": "unreachable", "llm_model": "unavailable"}
