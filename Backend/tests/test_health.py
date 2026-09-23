from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_without_credentials():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_cors():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        allowed = client.options("/health", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET",
        })
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
        denied = client.options("/health", headers={
            "Origin": "https://untrusted.invalid", "Access-Control-Request-Method": "GET",
        })
        assert "access-control-allow-origin" not in denied.headers
