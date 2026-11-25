import multiprocessing
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import inspect

from app.extensions import db
from app.startup import create_server_app
from conftest import Browser

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fresh_project(tmp_path, monkeypatch):
    for name in ("SECRET_KEY", "DATABASE_URL", "APP_ENV", "RATELIMIT_STORAGE_URI"):
        monkeypatch.delenv(name, raising=False)
    shutil.copytree(ROOT / "migrations", tmp_path / "migrations")
    return tmp_path


def test_first_start_allows_registration_without_setup(fresh_project):
    app = create_server_app(fresh_project)
    assert not (fresh_project / ".env").exists()
    assert (fresh_project / "instance/focusflow.db").is_file()
    assert len((fresh_project / "instance/secret.key").read_text()) == 64
    browser = Browser(app)
    assert browser.client.get("/register").status_code == 200
    assert browser.register().status_code == 201
    task = browser.task().json["data"]
    original_cookie = browser.client.get_cookie("focusflow_session").value
    original_key = app.secret_key
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    restarted = create_server_app(fresh_project)
    assert restarted.secret_key == original_key
    client = restarted.test_client()
    client.set_cookie("focusflow_session", original_cookie)
    assert client.get("/api/auth/me").status_code == 200
    assert client.get(f"/api/tasks/{task['id']}").json["data"]["title"] == task["title"]
    with restarted.app_context():
        db.session.remove()
        db.engine.dispose()


def _competing_start(arguments):
    project, gate = arguments
    gate.wait(timeout=30)
    app = create_server_app(project)
    with app.app_context():
        count = len(inspect(db.engine).get_table_names())
        db.session.remove()
        db.engine.dispose()
    return app.secret_key, count


def test_simultaneous_first_starts_share_key_and_schema(fresh_project):
    with multiprocessing.Manager() as manager:
        gate = manager.Barrier(3)
        with ProcessPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(_competing_start, [(str(fresh_project), gate)] * 3))
    assert len({key for key, count in results}) == 1
    assert all(count == 9 for key, count in results)


def test_existing_explicit_secret_is_preserved(fresh_project, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "provided-secret-" * 4)
    app = create_server_app(fresh_project)
    assert app.secret_key == "provided-secret-" * 4
    assert not (fresh_project / "instance/secret.key").exists()
    with app.app_context():
        db.engine.dispose()
