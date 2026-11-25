import shutil
from pathlib import Path

import pytest

from app.demo import create_demo_app, seed_workspace, DEMO_EMAIL, DEMO_PASSWORD
from app.extensions import db
from app.models import Student, Course, Task, Schedule, Notification

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def demo_root(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    shutil.copytree(ROOT / "migrations", tmp_path / "migrations")
    return tmp_path


def close(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def count(model):
    return db.session.scalar(db.select(db.func.count()).select_from(model))


def test_demo_has_real_data_and_working_login(demo_root):
    app = create_demo_app(demo_root)
    client = app.test_client()
    with app.app_context():
        assert count(Student) == 1
        assert count(Course) == 4
        assert count(Task) == 16
        assert count(Schedule) == 8
        assert count(Notification) >= 4
        assert (
            db.session.execute(db.select(Student))
            .scalar_one()
            .check_password(DEMO_PASSWORD)
        )
        assert db.session.execute(db.text("PRAGMA foreign_key_check")).all() == []
    token = client.get("/api/auth/csrf").json["data"]["csrf_token"]
    assert (
        client.post(
            "/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            headers={"X-CSRFToken": token},
        ).status_code
        == 200
    )
    data = client.get("/api/dashboard/summary").json["data"]
    assert data["total"] == 16 and data["completed"] == 3 and data["overdue"] == 2
    assert len(data["today"]) == 3
    assert data["workload"]["overloaded_days"]
    assert client.get("/api/workload/recommendations").status_code == 200
    close(app)


def test_demo_restart_preserves_edits_and_does_not_duplicate(demo_root):
    app = create_demo_app(demo_root)
    with app.app_context():
        student = db.session.execute(db.select(Student)).scalar_one()
        student.full_name = "My testing edit"
        db.session.commit()
        assert seed_workspace() is False
    secret = app.secret_key
    close(app)
    restarted = create_demo_app(demo_root)
    assert restarted.secret_key == secret
    with restarted.app_context():
        assert count(Student) == 1 and count(Task) == 16 and count(Schedule) == 8
        assert (
            db.session.execute(db.select(Student)).scalar_one().full_name
            == "My testing edit"
        )
    close(restarted)


def test_demo_ignores_regular_database_and_uses_separate_cookie(demo_root, monkeypatch):
    normal = demo_root / "existing.db"
    normal.write_bytes(b"Existing database must not be opened by the demo")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + normal.as_posix())
    monkeypatch.setenv("SECRET_KEY", "normal-workspace-secret-" * 3)
    app = create_demo_app(demo_root)
    assert app.config["SESSION_COOKIE_NAME"] == "focusflow_demo_session"
    assert app.secret_key != "normal-workspace-secret-" * 3
    assert normal.read_bytes() == b"Existing database must not be opened by the demo"
    close(app)


def test_seeder_refuses_normal_workspace(app):
    with app.app_context():
        with pytest.raises(RuntimeError):
            seed_workspace()


def test_demo_runner_refuses_production(demo_root, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        create_demo_app(demo_root)
