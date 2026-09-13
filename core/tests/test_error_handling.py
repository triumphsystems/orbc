from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from core.app import app


def test_global_500_exception_handler_sanitizes_errors():
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/test-internal-error")
    def route_raising_error():
        raise RuntimeError("Secret DB Password exposed: postgres://user:secret@db:5432/orbit")

    response = client.get("/test-internal-error")
    assert response.status_code == 500
    data = response.json()
    assert "secret" not in data["detail"].lower()
    assert "postgres" not in data["detail"].lower()
    assert "unexpected error occurred" in data["detail"]


def test_sqlalchemy_error_handler_sanitizes_db_errors():
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/test-db-error")
    def route_raising_db_error():
        raise OperationalError("SELECT * FROM sensitive_table", {}, Exception("Connection timeout"))

    response = client.get("/test-db-error")
    assert response.status_code == 500
    data = response.json()
    assert "sensitive_table" not in data["detail"]
    assert "SELECT" not in data["detail"]
    assert "database" not in data["detail"].lower()
    assert "operation could not be completed" in data["detail"]
