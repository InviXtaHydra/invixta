from fastapi.testclient import TestClient


def test_health_reports_database_and_model_status(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "llm": "unreachable", "llm_model": "unavailable"}


def test_api_docs_are_switched_off_in_production() -> None:
    import importlib

    from fastapi.testclient import TestClient

    import app.main
    from app.core.config import get_settings

    settings = get_settings()
    original = settings.environment
    try:
        settings.environment = "production"
        production_app = importlib.reload(app.main).app
        with TestClient(production_app) as client:
            assert client.get("/docs").status_code == 404
            assert client.get("/openapi.json").status_code == 404
    finally:
        settings.environment = original
        importlib.reload(app.main)
