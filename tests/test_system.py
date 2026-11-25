from datetime import datetime, timedelta, timezone
import pytest
from app.extensions import db
from app.models import Student, Task, WebSession, UserPreference, now
from app.services.planning import rank, suggestions, summary
from app.services.reminders import generate
from conftest import Browser


def test_registration_hash_and_duplicate(browser, app):
    assert browser.register().status_code == 409
    with app.app_context():
        s = db.session.execute(db.select(Student)).scalar_one()
        assert s.password_hash != "StrongPassword123!"
        assert s.check_password("StrongPassword123!")
    assert "password_hash" not in browser.request("/auth/me").json["data"]


def test_login_logout_and_cookie(browser):
    cookie = browser.client.get_cookie("focusflow_session")
    assert cookie.http_only and cookie.same_site == "Lax"
    assert browser.request("/auth/logout", "POST", {}).status_code == 200
    assert browser.request("/auth/me").status_code == 401
    assert (
        browser.request(
            "/auth/login", "POST", {"email": "student@example.com", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        browser.request(
            "/auth/login",
            "POST",
            {"email": "student@example.com", "password": "StrongPassword123!"},
        ).status_code
        == 200
    )
    assert browser.client.get_cookie("focusflow_session").value != cookie.value


@pytest.mark.parametrize(
    "values",
    [
        {"password": "short", "password_confirmation": "short"},
        {"email": "invalid"},
        {"full_name": ""},
        {"password_confirmation": "does-not-match"},
        {"password": "a" * 129},
        {"email": ["not", "a", "string"]},
    ],
)
def test_registration_validation(app, values):
    b = Browser(app)
    data = {
        "full_name": "Student",
        "email": "new@example.com",
        "password": "StrongPassword123!",
        "password_confirmation": "StrongPassword123!",
    }
    assert b.request("/auth/register", "POST", {**data, **values}).status_code == 400


def test_csrf(app, browser):
    assert browser.client.post("/api/tasks", json={"title": "x"}).status_code == 400
    assert (
        browser.client.post(
            "/api/tasks", json={"title": "x"}, headers={"X-CSRFToken": "bad"}
        ).status_code
        == 400
    )


@pytest.mark.parametrize(
    "path",
    [
        "/tasks",
        "/courses",
        "/schedules",
        "/dashboard/summary",
        "/notifications",
        "/preferences",
        "/profile",
        "/deadlines",
        "/priorities/recommendations",
        "/workload/recommendations",
    ],
)
def test_authentication_required(app, path):
    assert Browser(app).request(path).status_code == 401


def test_session_expiration(browser, app):
    with app.app_context():
        db.session.execute(
            db.update(WebSession).values(expires_at=now() - timedelta(minutes=1))
        )
        db.session.commit()
    assert browser.request("/auth/me").status_code == 401


def test_revoked_cookie_cannot_replay(browser, app):
    old = browser.client.get_cookie("focusflow_session").value
    browser.request("/auth/logout", "POST", {})
    other = app.test_client()
    other.set_cookie("focusflow_session", old)
    assert other.get("/api/auth/me").status_code == 401


def test_profile_and_password_change(browser, app):
    second = Browser(app)
    assert (
        second.request(
            "/auth/login",
            "POST",
            {"email": "student@example.com", "password": "StrongPassword123!"},
        ).status_code
        == 200
    )
    assert (
        browser.request(
            "/profile", "PATCH", {"email": "changed@example.com"}
        ).status_code
        == 400
    )
    r = browser.request(
        "/profile",
        "PATCH",
        {
            "full_name": "Changed",
            "email": "changed@example.com",
            "current_password": "StrongPassword123!",
            "password": "NewStrongPassword123!",
            "password_confirmation": "NewStrongPassword123!",
        },
    )
    assert r.status_code == 200 and r.json["data"]["full_name"] == "Changed"
    assert second.request("/auth/me").status_code == 401
    assert browser.request("/auth/me").status_code == 200


def test_course_crud_and_safe_deletion(browser):
    c = browser.course().json["data"]
    cid = c["id"]
    assert browser.course().status_code == 400
    t = browser.task(course_id=cid, deadline="2020-01-01T12:00:00Z").json["data"]
    assert browser.request(f"/courses/{cid}").json["data"]["next_deadline"] is None
    assert (
        browser.request(
            f"/courses/{cid}", "PATCH", {"name": "Advanced databases"}
        ).status_code
        == 200
    )
    assert browser.request(f"/courses/{cid}").json["data"]["pending_count"] == 1
    assert browser.request(f"/courses/{cid}", "DELETE").status_code == 400
    assert browser.request(f"/courses/{cid}?confirm=true", "DELETE").status_code == 200
    assert browser.request("/tasks/" + str(t["id"])).json["data"]["course_id"] is None


def test_task_crud_complete_reopen_filters(browser):
    cid = browser.course().json["data"]["id"]
    t = browser.task(
        course_id=cid, priority="high", deadline="2030-01-03T12:00:00Z"
    ).json["data"]
    tid = t["id"]
    assert (
        browser.request(
            f"/tasks/{tid}", "PATCH", {"title": "Updated assignment"}
        ).status_code
        == 200
    )
    assert (
        len(
            browser.request("/tasks?q=updated&priority=high&sort=due_date").json["data"]
        )
        == 1
    )
    assert browser.request("/tasks?q=nothing").json["data"] == []
    assert browser.request(f"/tasks/{tid}/complete", "POST", {}).json["data"][
        "completed_at"
    ]
    assert browser.request("/workload/summary").json["data"]["remaining_hours"] == 0
    assert browser.request("/priorities/recommendations").json["data"] == []
    assert (
        browser.request(f"/tasks/{tid}/complete", "POST", {"completed": False}).json[
            "data"
        ]["completed_at"]
        is None
    )
    assert browser.request(f"/tasks/{tid}", "DELETE").status_code == 400
    assert browser.request(f"/tasks/{tid}?confirm=true", "DELETE").status_code == 200
    assert browser.request(f"/tasks/{tid}").status_code == 404


@pytest.mark.parametrize(
    "values",
    [
        {"title": ""},
        {"priority": "urgent"},
        {"status": "overdue"},
        {"estimated_hours": -1},
        {"estimated_hours": "nan"},
        {"estimated_hours": True},
        {"course_id": True},
        {"task_type": "arbitrary"},
        {"deadline": "2030-01-01T09:00"},
        {"description": ["x"]},
    ],
)
def test_task_validation(browser, values):
    assert browser.task(**values).status_code == 400
    assert browser.request("/tasks").json["data"] == []


def test_ownership_every_resource(browser, app):
    c = browser.course().json["data"]
    t = browser.task(course_id=c["id"]).json["data"]
    other = Browser(app)
    assert other.register("other@example.com").status_code == 201
    for path in (f"/tasks/{t['id']}", f"/courses/{c['id']}"):
        assert other.request(path).status_code == 404
        assert (
            other.request(
                path, "PATCH", {"title": "stolen", "name": "stolen"}
            ).status_code
            == 404
        )
        assert other.request(path + "?confirm=true", "DELETE").status_code == 404
    assert other.task(course_id=c["id"]).status_code == 404
    assert (
        other.request(
            f"/deadlines/{t['id']}", "PATCH", {"deadline": "2030-01-01T00:00:00Z"}
        ).status_code
        == 404
    )
    assert other.request("/tasks").json["data"] == []
    assert other.request("/courses").json["data"] == []


def test_deadlines_and_overdue(browser):
    t = browser.task().json["data"]
    tid = t["id"]
    assert (
        browser.request(
            "/deadlines", "POST", {"task_id": tid, "deadline": "2020-01-01T12:00:00Z"}
        ).status_code
        == 201
    )
    assert browser.request(f"/tasks/{tid}").json["data"]["overdue"]
    assert len(browser.request("/tasks?deadline=overdue").json["data"]) == 1
    assert browser.request("/deadlines/upcoming").json["data"] == []
    assert (
        browser.request(
            f"/deadlines/{tid}", "PATCH", {"deadline": "2030-01-01T12:00:00Z"}
        ).status_code
        == 200
    )
    assert len(browser.request("/deadlines/upcoming").json["data"]) == 1
    assert (
        browser.request(f"/deadlines/{tid}", "PATCH", {"deadline": None}).status_code
        == 200
    )
    assert browser.request("/deadlines").json["data"] == []


def test_priority_formula_and_missing_values(browser, app):
    a = browser.task(priority="high", deadline="2030-01-01T09:00:00Z").json["data"]
    b = browser.task(title="Reading", estimated_hours=None, priority="low").json["data"]
    with app.app_context():
        at = datetime(2030, 1, 1, 9)
        first = rank(db.session.get(Task, a["id"]), at)
        second = rank(db.session.get(Task, b["id"]), at)
        assert first["score"] == 100 and first["at_risk"]
        assert second["score"] == 6 and "assumption" in second["reason"]


def configure(browser):
    assert (
        browser.request(
            "/preferences",
            "PATCH",
            {
                "timezone": "UTC",
                "study_days": [0, 1, 2, 3, 4, 5, 6],
                "study_start": "09:00",
                "study_end": "18:00",
                "daily_hours": 4,
            },
        ).status_code
        == 200
    )


def session(task, start="2030-01-07T09:00:00Z", end="2030-01-07T10:00:00Z"):
    return {"task_id": task, "start": start, "end": end}


def test_schedule_crud_conflicts_ownership(browser, app):
    configure(browser)
    tid = browser.task(deadline="2030-01-07T17:00:00Z").json["data"]["id"]
    r = browser.request("/schedules", "POST", session(tid))
    assert r.status_code == 201
    sid = r.json["data"]["id"]
    assert browser.request("/schedules", "POST", session(tid)).status_code == 400
    assert (
        browser.request(
            "/schedules", "POST", session(tid, end="2030-01-07T19:00:00Z")
        ).status_code
        == 400
    )
    assert (
        browser.request(
            f"/schedules/{sid}",
            "PATCH",
            session(tid, "2030-01-07T11:00:00Z", "2030-01-07T12:00:00Z"),
        ).status_code
        == 200
    )
    assert browser.request(
        "/schedules?start=2030-01-07T10:00:00Z&end=2030-01-07T13:00:00Z"
    ).json["data"]
    other = Browser(app)
    other.register("other@example.com")
    assert other.request(f"/schedules/{sid}").status_code == 404
    assert other.request("/schedules", "POST", session(tid)).status_code == 404
    assert (
        browser.request(f"/schedules/{sid}?confirm=true", "DELETE").status_code == 200
    )


def test_scheduling_capacity_and_deadline_updates(browser):
    configure(browser)
    tid = browser.task(estimated_hours=8, deadline="2030-01-07T17:00:00Z").json["data"][
        "id"
    ]
    assert (
        browser.request(
            "/schedules", "POST", session(tid, end="2030-01-07T13:00:00Z")
        ).status_code
        == 201
    )
    assert (
        browser.request(
            "/schedules",
            "POST",
            session(tid, "2030-01-07T14:00:00Z", "2030-01-07T15:00:00Z"),
        ).status_code
        == 400
    )
    assert (
        browser.request(
            f"/tasks/{tid}", "PATCH", {"deadline": "2030-01-07T12:00:00Z"}
        ).status_code
        == 400
    )
    assert (
        browser.request(f"/tasks/{tid}", "PATCH", {"estimated_hours": 2}).status_code
        == 400
    )
    assert browser.request(f"/tasks/{tid}").json["data"]["estimated_hours"] == 8


def test_accept_is_atomic_and_rechecks(browser):
    configure(browser)
    tid = browser.task().json["data"]["id"]
    same = session(tid)
    assert (
        browser.request(
            "/schedules/accept", "POST", {"sessions": [same, same]}
        ).status_code
        == 400
    )
    assert browser.request("/schedules").json["data"] == []
    assert (
        browser.request("/schedules/accept", "POST", {"sessions": [same]}).status_code
        == 201
    )
    assert (
        browser.request("/schedules/accept", "POST", {"sessions": [same]}).status_code
        == 400
    )
    assert len(browser.request("/schedules").json["data"]) == 1


def test_planning_fits_capacity_and_preserves_manual(browser, app):
    configure(browser)
    tid = browser.task(estimated_hours=6, deadline="2030-01-08T12:00:00Z").json["data"][
        "id"
    ]
    r = browser.request("/schedules", "POST", session(tid))
    assert r.status_code == 201
    with app.app_context():
        plan = suggestions(1, datetime(2030, 1, 7, 8))
        assert len(plan["sessions"]) == 5 and not plan["unplaced"]
        sessions = plan["sessions"]
        assert all(
            datetime.fromisoformat(s["start"].replace("Z", ""))
            >= datetime(2030, 1, 7, 10)
            for s in sessions
        )
        assert all(s["end"] <= "2030-01-08T12:00:00Z" for s in sessions)
        assert (
            sum(s["hours"] for s in sessions if s["start"].startswith("2030-01-07"))
            <= 3
        )
    assert len(browser.request("/schedules").json["data"]) == 1


def test_planning_unplaceable_and_completed(browser, app):
    configure(browser)
    browser.task(estimated_hours=8, deadline="2030-01-07T10:00:00Z")
    tid = browser.task(title="Done").json["data"]["id"]
    browser.request(f"/tasks/{tid}/complete", "POST", {})
    with app.app_context():
        p = suggestions(1, datetime(2030, 1, 7, 9))
        assert p["unplaced"][0]["unallocated_hours"] == 7
        assert all(s["task_id"] != tid for s in p["sessions"])


def test_workload_and_completion_dashboard(browser, app):
    configure(browser)
    tid = browser.task().json["data"]["id"]
    browser.request("/schedules", "POST", session(tid))
    with app.app_context():
        w = summary(1, datetime(2030, 1, 7).date())
        assert w["weekly_hours"] == 1 and w["remaining_hours"] == 3
    browser.request(f"/tasks/{tid}/complete", "POST", {})
    d = browser.request("/dashboard/summary").json["data"]
    assert d["completed"] == 1 and d["completion_percent"] == 100 and d["pending"] == 0
    assert d["workload"]["remaining_hours"] == 0


def test_empty_dashboard(browser):
    d = browser.request("/dashboard/summary").json["data"]
    assert d["total"] == 0 and d["completion_percent"] == 0


def test_reminders_dedupe_overdue_and_overload(browser, app):
    configure(browser)
    tid = browser.task(deadline="2030-01-07T17:00:00Z").json["data"]["id"]
    browser.request("/schedules", "POST", session(tid))
    browser.request("/preferences", "PATCH", {"daily_hours": 0.5})
    with app.app_context():
        assert generate(1, datetime(2030, 1, 7, 8)) == 2
        assert generate(1, datetime(2030, 1, 7, 8)) == 0
        assert generate(1, datetime(2030, 1, 8, 8)) == 1
    data = browser.request("/notifications").json["data"]
    assert data["unread"] == 3
    ident = data["items"][0]["id"]
    other = Browser(app)
    other.register("other@example.com")
    assert other.request(f"/notifications/{ident}/read", "POST", {}).status_code == 404
    assert (
        browser.request(f"/notifications/{ident}/read", "POST", {}).status_code == 200
    )
    assert browser.request("/notifications/read-all", "POST", {}).status_code == 200
    assert browser.request("/notifications").json["data"]["unread"] == 0


@pytest.mark.parametrize(
    "data",
    [
        {"daily_hours": 0},
        {"timezone": "Bad/Zone"},
        {"study_days": []},
        {"reminder_hours": ["24"]},
        {"study_start": "19:00", "study_end": "09:00"},
    ],
)
def test_preferences_validation(browser, data):
    assert browser.request("/preferences", "PATCH", data).status_code == 400


def test_pages_and_security_headers(browser):
    for path in (
        "dashboard",
        "tasks",
        "courses",
        "deadlines",
        "calendar",
        "planner",
        "notifications",
        "profile",
        "settings",
    ):
        r = browser.client.get("/" + path)
        assert r.status_code == 200
        assert "default-src 'self'" in r.headers["Content-Security-Policy"]
        assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_rate_limit(app):
    app.config["RATELIMIT_ENABLED"] = True
    # Limiters read enabled at initialization; verify with an independent factory.
    from app import create_app

    limited = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "x" * 40,
            "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
            "RATELIMIT_ENABLED": True,
        }
    )
    b = Browser(limited)
    statuses = [
        b.request(
            "/auth/login", "POST", {"email": "none@example.com", "password": "wrong"}
        ).status_code
        for _ in range(11)
    ]
    assert statuses[-1] == 429
