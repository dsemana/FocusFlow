"""Opt-in local testing workspace, completely separate from normal app data."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from flask_migrate import upgrade
from flask import current_app

from . import create_app
from .extensions import db
from .models import (
    Student,
    UserPreference,
    Course,
    Task,
    Deadline,
    Schedule,
    Notification,
    now,
)
from .services.reminders import generate
from .startup import startup_lock

DEMO_EMAIL = "demo@focusflow.test"
DEMO_PASSWORD = "FocusFlowDemo2026!"


def seed_workspace(at=None):
    """Seed an empty demo database once; keep subsequent testing edits."""
    if not current_app.config.get(
        "DEMO_MODE"
    ) or not db.session.get_bind().engine.url.database.endswith("focusflow-demo.db"):
        raise RuntimeError(
            "Demo seeding requires its dedicated focusflow-demo.db file."
        )
    if db.session.execute(db.select(Student.id).limit(1)).first():
        return False
    at = at or now()
    student = Student(full_name="Alex — Demo Student", email=DEMO_EMAIL)
    student.set_password(DEMO_PASSWORD)
    student.preference = UserPreference(
        daily_hours=6,
        timezone="Africa/Kigali",
        study_start="08:00",
        study_end="20:00",
        study_days=list(range(7)),
        reminder_hours=[24, 72],
    )
    db.session.add(student)
    db.session.flush()
    courses = []
    for name, code, color, description in [
        (
            "Database Systems",
            "CS201",
            "#5366de",
            "Relational design, SQL and transaction processing.",
        ),
        (
            "Software Engineering",
            "SE301",
            "#3f9b82",
            "Requirements, testing and collaborative development.",
        ),
        (
            "Discrete Mathematics",
            "MTH202",
            "#cf9552",
            "Logic, graphs and mathematical reasoning.",
        ),
        (
            "Research Methods",
            "RM102",
            "#9d69c1",
            "Academic writing and research design.",
        ),
    ]:
        course = Course(
            student_id=student.id,
            name=name,
            code=code,
            color=color,
            description=description,
            instructor="Sample instructor",
            semester="Demo semester",
        )
        db.session.add(course)
        courses.append(course)
    db.session.flush()
    # title, course index (None = independent), type, priority, status, hours, due-days
    examples = [
        ("Normalize the library database", 0, "assignment", "high", "pending", 2, 1),
        ("Build the team project prototype", 1, "project", "high", "in_progress", 6, 5),
        (
            "Prepare for the graph theory exam",
            2,
            "exam_preparation",
            "high",
            "pending",
            4,
            3,
        ),
        ("Read qualitative research chapter", 3, "reading", "low", "pending", 1.5, 7),
        ("Submit the research proposal", 3, "assignment", "high", "pending", 2, -1),
        ("Draw the initial ER diagram", 0, "assignment", "medium", "completed", 2, -3),
        (
            "Practice the Git review workflow",
            1,
            "study_session",
            "low",
            "completed",
            1,
            -2,
        ),
        (
            "Practice joins and subqueries",
            0,
            "study_session",
            "medium",
            "in_progress",
            3,
            2,
        ),
        ("Review proofs and induction", 2, "study_session", "medium", "pending", 1, 4),
        ("Organize semester notes", None, "other", "low", "pending", None, None),
        ("Write the software test plan", 1, "assignment", "medium", "pending", 2, 6),
        (
            "Finish the probability worksheet",
            2,
            "assignment",
            "medium",
            "pending",
            1.5,
            -2,
        ),
        ("Review database indexing", 0, "reading", "low", "pending", 1, 8),
        ("Prepare the project presentation", 1, "project", "high", "pending", 3, 10),
        (
            "Summarize the literature review",
            3,
            "reading",
            "medium",
            "completed",
            1.5,
            -4,
        ),
        (
            "Plan next week's independent study",
            None,
            "other",
            "low",
            "pending",
            0.5,
            None,
        ),
    ]
    tasks = []
    for index, (title, course, kind, priority, status, hours, days) in enumerate(
        examples
    ):
        task = Task(
            student_id=student.id,
            course_id=courses[course].id if course is not None else None,
            title=title,
            description="Sample academic work for trying FocusFlow. You can edit, complete or delete this task.",
            task_type=kind,
            priority=priority,
            status=status,
            estimated_hours=hours,
            created_at=at - timedelta(days=7, minutes=index),
            completed_at=at - timedelta(days=1) if status == "completed" else None,
        )
        if days is not None:
            task.deadline = Deadline(due_at=at + timedelta(days=days))
        db.session.add(task)
        tasks.append(task)
    db.session.flush()
    zone = ZoneInfo(student.preference.timezone)
    today = at.replace(tzinfo=timezone.utc).astimezone(zone).date()

    def instant(day, hour, minute=0):
        date = today + timedelta(days=day)
        return (
            datetime(date.year, date.month, date.day, hour, minute, tzinfo=zone)
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )

    for task_index, day, hour, minute, duration in [
        (0, 0, 9, 0, 2),
        (7, 0, 11, 0, 1.5),
        (2, 0, 14, 0, 2),
        (7, 1, 9, 0, 1.5),
        (2, 1, 11, 0, 2),
        (1, 2, 9, 0, 2),
        (3, 2, 11, 0, 1.5),
        (1, 3, 9, 0, 2),
    ]:
        start = instant(day, hour, minute)
        db.session.add(
            Schedule(
                student_id=student.id,
                task_id=tasks[task_index].id,
                start_at=start,
                end_at=start + timedelta(hours=duration),
                source="manual",
            )
        )
    # Simulate a real workflow: reducing availability preserves an existing plan
    # and creates an overload warning for today's 5.5h allocation.
    student.preference.daily_hours = 4
    db.session.commit()
    generate(student.id, at)
    oldest = (
        db.session.execute(
            db.select(Notification)
            .where(Notification.student_id == student.id)
            .order_by(Notification.id)
        )
        .scalars()
        .first()
    )
    if oldest:
        oldest.is_read = True
        db.session.commit()
    return True


def create_demo_app(project_root=None):
    if os.getenv("APP_ENV") == "production":
        raise RuntimeError("The demo runner is for local testing, not production.")
    root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
    instance = root / "instance" / "demo"
    instance.mkdir(parents=True, exist_ok=True)
    with startup_lock(instance / "startup.lock"):
        key_file = instance / "secret.key"
        if not key_file.exists():
            descriptor = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                stream.write(secrets.token_hex(32))
        app = create_app(
            {
                "SECRET_KEY": key_file.read_text(encoding="ascii").strip(),
                "SQLALCHEMY_DATABASE_URI": "sqlite:///"
                + (instance / "focusflow-demo.db").as_posix(),
                "SESSION_COOKIE_NAME": "focusflow_demo_session",
                "RATELIMIT_STORAGE_URI": "memory://",
                "DEMO_MODE": True,
                "DEMO_EMAIL": DEMO_EMAIL,
                "DEMO_PASSWORD": DEMO_PASSWORD,
            },
            instance_path=str(instance),
        )
        with app.app_context():
            upgrade(directory=str(root / "migrations"))
            seed_workspace()
        return app
