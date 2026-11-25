import pytest
from app import create_app
from app.extensions import db


@pytest.fixture
def app(tmp_path):
    # Every test owns a disposable on-disk database; no user URL is accepted.
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-" * 8,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///"
            + (tmp_path / "focusflow-test.db").as_posix(),
            "RATELIMIT_ENABLED": False,
        }
    )
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


class Browser:
    def __init__(self, app):
        self.client = app.test_client()

    def request(self, path, method="GET", data=None):
        headers = {}
        if method != "GET":
            token = self.client.get("/api/auth/csrf").json["data"]["csrf_token"]
            headers["X-CSRFToken"] = token
        return self.client.open(
            "/api" + path, method=method, json=data, headers=headers
        )

    def register(self, email="student@example.com"):
        return self.request(
            "/auth/register",
            "POST",
            {
                "full_name": "Test Student",
                "email": email,
                "password": "StrongPassword123!",
                "password_confirmation": "StrongPassword123!",
            },
        )

    def course(self, **values):
        return self.request(
            "/courses", "POST", {"name": "Databases", "code": "CS201", **values}
        )

    def task(self, **values):
        return self.request(
            "/tasks",
            "POST",
            {"title": "Database assignment", "estimated_hours": 3, **values},
        )


@pytest.fixture
def browser(app):
    b = Browser(app)
    assert b.register().status_code == 201
    return b
