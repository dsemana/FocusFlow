import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from app import create_app
from app.extensions import db
from flask_migrate import upgrade, downgrade
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[1]


def test_deleted_task_ids_are_not_reused(browser):
    first = browser.task().json["data"]["id"]
    assert browser.request(f"/tasks/{first}?confirm=true", "DELETE").status_code == 200
    second = browser.task().json["data"]["id"]
    assert second > first


def test_foreign_keys_wal_and_integrity(app):
    with app.app_context():
        assert db.session.execute(db.text("PRAGMA foreign_keys")).scalar() == 1
        assert db.session.execute(db.text("PRAGMA journal_mode")).scalar() == "wal"
        assert db.session.execute(db.text("PRAGMA integrity_check")).scalar() == "ok"


def test_fresh_migration_rollback_and_reinstall(tmp_path):
    application = create_app(
        {
            "SECRET_KEY": "s" * 40,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///"
            + (tmp_path / "migrations.db").as_posix(),
            "RATELIMIT_ENABLED": False,
        }
    )
    with application.app_context():
        directory = str(ROOT / "migrations")
        upgrade(directory=directory)
        assert len(inspect(db.engine).get_table_names()) == 9
        downgrade(directory=directory, revision="base")
        assert inspect(db.engine).get_table_names() == ["alembic_version"]
        upgrade(directory=directory)
        assert len(inspect(db.engine).get_table_names()) == 9
        db.session.remove()
        db.engine.dispose()


def _schedule_in_process(arguments):
    url, cookie, csrf, gate = arguments
    application = create_app(
        {
            "SECRET_KEY": "test-key-" * 8,
            "SQLALCHEMY_DATABASE_URI": url,
            "RATELIMIT_ENABLED": False,
        }
    )
    client = application.test_client()
    client.set_cookie("focusflow_session", cookie)
    gate.wait(timeout=30)
    response = client.post(
        "/api/schedules",
        json={
            "task_id": 1,
            "start": "2030-01-07T09:00:00Z",
            "end": "2030-01-07T10:00:00Z",
        },
        headers={"X-CSRFToken": csrf},
    )
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
    return response.status_code


def test_competing_processes_share_database_lock(browser, app):
    from conftest import Browser
    from test_system import configure

    configure(browser)
    assert browser.task().status_code == 201
    arguments = []
    for _ in range(4):
        other = Browser(app)
        assert (
            other.request(
                "/auth/login",
                "POST",
                {"email": "student@example.com", "password": "StrongPassword123!"},
            ).status_code
            == 200
        )
        csrf = other.client.get("/api/auth/csrf").json["data"]["csrf_token"]
        arguments.append(
            (
                app.config["SQLALCHEMY_DATABASE_URI"],
                other.client.get_cookie("focusflow_session").value,
                csrf,
            )
        )
    with multiprocessing.Manager() as manager:
        gate = manager.Barrier(4)
        with ProcessPoolExecutor(max_workers=4) as pool:
            statuses = list(
                pool.map(_schedule_in_process, [(*value, gate) for value in arguments])
            )
    assert statuses.count(201) == 1
    assert statuses.count(400) == 3
    assert len(browser.request("/schedules").json["data"]) == 1


def test_data_persists_between_application_instances(browser, app):
    task = browser.task().json["data"]
    another = create_app(
        {
            "SECRET_KEY": "test-key-" * 8,
            "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
            "RATELIMIT_ENABLED": False,
        }
    )
    from conftest import Browser

    client = Browser(another)
    assert (
        client.request(
            "/auth/login",
            "POST",
            {"email": "student@example.com", "password": "StrongPassword123!"},
        ).status_code
        == 200
    )
    assert client.request(f"/tasks/{task['id']}").json["data"]["title"] == task["title"]
    with another.app_context():
        db.session.remove()
        db.engine.dispose()
