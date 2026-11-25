"""Authenticated HTTP load against a disposable database only; never production."""

import argparse
import json
import re
import os
import sys
import threading
import time
import uuid
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

load_dotenv()
from app import create_app
from app.extensions import db
from app.models import Student, UserPreference, WebSession
from werkzeug.security import generate_password_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5050")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--output", default="docs/load-results.json")
    parser.add_argument("--disposable-database", action="store_true", required=True)
    args = parser.parse_args()
    app = create_app({"RATELIMIT_ENABLED": False})
    if app.config["PRODUCTION"]:
        raise RuntimeError("Load fixture must not run in production.")
    batch = uuid.uuid4().hex[:10]
    password = "LoadTestPassword123!"
    hashed = generate_password_hash(password)
    ids = []
    clients = []
    with app.app_context():
        for i in range(args.users):
            s = Student(
                full_name=f"Load student {i}",
                email=f"load-{batch}-{i}@example.test",
                password_hash=hashed,
            )
            s.preference = UserPreference()
            db.session.add(s)
            db.session.flush()
            ids.append(s.id)
        db.session.commit()
    try:
        for i in range(args.users):
            c = app.test_client()
            csrf = c.get("/api/auth/csrf").json["data"]["csrf_token"]
            r = c.post(
                "/api/auth/login",
                json={"email": f"load-{batch}-{i}@example.test", "password": password},
                headers={"X-CSRFToken": csrf},
            )
            assert r.status_code == 200
            csrf = c.get("/api/auth/csrf").json["data"]["csrf_token"]
            clients.append((c.get_cookie("focusflow_session").value, csrf))
        gate = threading.Barrier(args.users)

        def worker(index):
            cookie, csrf = clients[index]
            samples = []

            def request(path, method="GET", payload=None):
                data = json.dumps(payload).encode() if payload is not None else None
                req = urllib.request.Request(
                    args.base_url + "/api" + path,
                    data=data,
                    method=method,
                    headers={
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf,
                        "Cookie": "focusflow_session=" + cookie,
                        "User-Agent": "Werkzeug/"
                        + __import__(
                            "importlib.metadata", fromlist=["version"]
                        ).version("werkzeug"),
                    },
                )
                started = time.perf_counter()
                try:
                    with urllib.request.urlopen(req, timeout=30) as response:
                        value = json.load(response)
                        status = response.status
                except urllib.error.HTTPError as error:
                    value = json.loads(error.read())
                    status = error.code
                samples.append(
                    {
                        "endpoint": re.sub(r"/\d+", "/<id>", path.split("?")[0]),
                        "method": method,
                        "status": status,
                        "ms": round((time.perf_counter() - started) * 1000, 2),
                    }
                )
                if not 200 <= status < 300:
                    raise RuntimeError(f"{status}: {value}")
                return value["data"]

            gate.wait()
            task = request(
                "/tasks", "POST", {"title": f"Load task {index}", "estimated_hours": 2}
            )
            request("/tasks")
            request("/tasks/" + str(task["id"]), "PATCH", {"status": "in_progress"})
            request("/workload/summary")
            request("/dashboard/summary")
            request("/tasks/" + str(task["id"]) + "?confirm=true", "DELETE")
            return samples

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.users) as pool:
            groups = list(pool.map(worker, range(args.users)))
        elapsed = time.perf_counter() - started
        samples = [s for group in groups for s in group]
        timings = sorted(s["ms"] for s in samples)

        def stats(values):
            values = sorted(values)
            return {
                "count": len(values),
                "median_ms": values[len(values) // 2],
                "p95_ms": values[min(len(values) - 1, int(len(values) * 0.95))],
                "max_ms": values[-1],
            }

        result = {
            "users": args.users,
            "requests": len(samples),
            "elapsed_seconds": round(elapsed, 3),
            "requests_per_second": round(len(samples) / elapsed, 2),
            "errors": 0,
            "overall": stats(timings),
            "groups": {},
            "scope": "Authenticated local HTTP benchmark. Accounts prepared outside measured phase. No WAN, TLS, production proxy, or browser rendering.",
        }
        for method, path in sorted(set((s["method"], s["endpoint"]) for s in samples)):
            result["groups"][method + " " + path] = stats(
                [
                    s["ms"]
                    for s in samples
                    if s["method"] == method and s["endpoint"] == path
                ]
            )
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        with app.app_context():
            for record in db.session.execute(db.select(WebSession)).scalars().all():
                if record.data.get("_user_id") in [str(i) for i in ids]:
                    db.session.delete(record)
            for ident in ids:
                student = db.session.get(Student, ident)
                if student:
                    db.session.delete(student)
            db.session.commit()


if __name__ == "__main__":
    main()
