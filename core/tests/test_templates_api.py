import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.app import create_app
from core.api.dependencies import get_db
from core.db.orm import Template
from core.db.session import Base

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_and_list_templates(client):
    payload = {
        "name": "Executive Opportunity Briefing",
        "description": "Visual PDF template for grants and fellowships",
        "format": "pdf",
        "schema_definition": {
            "title": "Scholarship Opportunity Dossier",
            "theme_color": "#00F2FE",
            "columns": ["title", "amount", "deadline", "status"],
            "show_summary": True,
        },
        "is_default": True,
    }

    res = client.post("/api/v1/templates", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Executive Opportunity Briefing"
    assert data["is_default"] is True
    template_id = data["id"]

    # List templates
    list_res = client.get("/api/v1/templates")
    assert list_res.status_code == 200
    templates = list_res.json()
    assert len(templates) == 1
    assert templates[0]["id"] == template_id

    # Get single template
    get_res = client.get(f"/api/v1/templates/{template_id}")
    assert get_res.status_code == 200
    assert get_res.json()["format"] == "pdf"


def test_update_and_delete_template(client):
    payload = {"name": "Old Template", "format": "html"}
    create_res = client.post("/api/v1/templates", json=payload)
    tpl_id = create_res.json()["id"]

    # Update template
    update_res = client.put(f"/api/v1/templates/{tpl_id}", json={"name": "New Template Name", "is_default": True})
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "New Template Name"

    # Delete template
    del_res = client.delete(f"/api/v1/templates/{tpl_id}")
    assert del_res.status_code == 204

    # Confirm 404
    get_res = client.get(f"/api/v1/templates/{tpl_id}")
    assert get_res.status_code == 404


def test_template_preview_rendering(client):
    preview_payload = {
        "schema_definition": {
            "title": "Autonomous Defense Intelligence",
            "theme_color": "#38BDF8",
            "columns": ["satellite", "orbit_altitude", "status"],
        },
        "sample_data": [
            {"satellite": "Orbit-Alpha-1", "orbit_altitude": "550 km", "status": "nominal"},
            {"satellite": "Orbit-Beta-2", "orbit_altitude": "620 km", "status": "active"},
        ],
    }

    res = client.post("/api/v1/templates/preview", json=preview_payload)
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text
    assert "Autonomous Defense Intelligence" in html
    assert "Orbit-Alpha-1" in html
    assert "550 km" in html
