from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from conftest import Browser
from test_system import configure, session


def test_competing_schedule_requests_are_serialized(browser, app):
    configure(browser)
    tid = browser.task().json["data"]["id"]
    clients = []
    for i in range(4):
        b = Browser(app)
        assert (
            b.request(
                "/auth/login",
                "POST",
                {"email": "student@example.com", "password": "StrongPassword123!"},
            ).status_code
            == 200
        )
        csrf = b.client.get("/api/auth/csrf").json["data"]["csrf_token"]
        clients.append((b, csrf))
    gate = Barrier(4)

    def compete(value):
        b, csrf = value
        gate.wait()
        return b.client.post(
            "/api/schedules", json=session(tid), headers={"X-CSRFToken": csrf}
        ).status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(compete, clients))
    assert statuses.count(201) == 1
    assert statuses.count(400) == 3
    assert len(browser.request("/schedules").json["data"]) == 1
