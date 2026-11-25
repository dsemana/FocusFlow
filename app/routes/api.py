import re
from datetime import datetime, timedelta
from flask import Blueprint, request, current_app, session
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import (
    Student,
    Course,
    Task,
    Deadline,
    Schedule,
    Notification,
    UserPreference,
    WebSession,
    now,
    iso,
)
from ..validation import (
    body,
    text,
    number,
    identifier,
    choice,
    instant,
    email,
    password,
    timezone_name,
    ValidationError,
)
from ..services.planning import (
    owned,
    lock_student,
    tasks_for,
    ranked,
    rank,
    summary,
    suggestions,
    validate_session,
    local,
)
from ..services.reminders import generate
from .auth import ok

api = Blueprint("api", __name__, url_prefix="/api")


@api.before_request
@login_required
def authenticated():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        lock_student(current_user.id)


def confirmed():
    if request.args.get("confirm") != "true":
        raise ValidationError("confirm", "Confirm deletion using confirm=true.")


def course_values(data, course=None):
    values = {}
    for key, limit in (
        ("name", 160),
        ("code", 40),
        ("description", 5000),
        ("instructor", 120),
        ("semester", 80),
    ):
        if key in data or course is None:
            values[key] = text(data, key, limit, key in ("name", "code"))
    if "color" in data:
        if not isinstance(data["color"], str) or not re.fullmatch(
            r"#[0-9a-fA-F]{6}", data["color"]
        ):
            raise ValidationError("color", "Use a six-digit hex color.")
        values["color"] = data["color"]
    return values


def save():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValidationError("record", "That email or course code already exists.")


@api.route("/profile", methods=["GET", "PATCH"])
def profile():
    if request.method == "GET":
        return ok(current_user.public())
    data = body(request)
    if any(
        k in data for k in ("email", "password")
    ) and not current_user.check_password(
        data.get("current_password", "")
        if isinstance(data.get("current_password", ""), str)
        else ""
    ):
        raise ValidationError(
            "current_password", "Enter your current password to change credentials."
        )
    if "full_name" in data:
        current_user.full_name = text(data, "full_name", 120, True)
    if "email" in data:
        current_user.email = email(data["email"])
    if "password" in data:
        secret = password(data["password"])
        if secret != data.get("password_confirmation"):
            raise ValidationError("password_confirmation", "Passwords must match.")
        current_user.set_password(secret)
        # Revoke every other authenticated session after a password change.
        for record in db.session.execute(db.select(WebSession)).scalars():
            if str(record.data.get("_user_id")) == str(current_user.id):
                db.session.delete(record)
        current_app.session_interface.regenerate(session)
    save()
    return ok(current_user.public(), "Profile updated")


@api.route("/preferences", methods=["GET", "PATCH"])
def preferences():
    pref = db.session.get(UserPreference, current_user.id)
    if request.method == "GET":
        return ok(pref.public())
    data = body(request)
    values = {}
    if "daily_hours" in data:
        values["daily_hours"] = number(data["daily_hours"], "daily_hours", 0.25, 16)
    if "timezone" in data:
        values["timezone"] = timezone_name(data["timezone"])
    for key in ("study_start", "study_end"):
        if key in data:
            value = data[key]
            if not isinstance(value, str) or not re.fullmatch(
                r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value
            ):
                raise ValidationError(key, "Use HH:MM in 24-hour time.")
            values[key] = value
    start = values.get("study_start", pref.study_start)
    end = values.get("study_end", pref.study_end)
    if start >= end:
        raise ValidationError(
            "study_end", "Study end must be later than study start on the same day."
        )
    for key, low, high in (("study_days", 0, 6), ("reminder_hours", 1, 720)):
        if key in data:
            value = data[key]
            if (
                not isinstance(value, list)
                or not 1 <= len(value) <= 10
                or any(type(v) != int or not low <= v <= high for v in value)
            ):
                raise ValidationError(
                    key, f"Choose integer values from {low} to {high}."
                )
            values[key] = sorted(set(value))
    for k, v in values.items():
        setattr(pref, k, v)
    save()
    return ok(pref.public(), "Preferences saved; review any newly overloaded dates.")


@api.route("/courses", methods=["GET", "POST"])
def courses():
    if request.method == "GET":
        items = db.session.execute(
            db.select(Course)
            .where(Course.student_id == current_user.id)
            .order_by(Course.name)
            .options(db.selectinload(Course.tasks).selectinload(Task.deadline))
        ).scalars()
        return ok([c.public() for c in items])
    item = Course(student_id=current_user.id, **course_values(body(request)))
    db.session.add(item)
    save()
    return ok(item.public(), "Course created", 201)


@api.route("/courses/<int:ident>", methods=["GET", "PATCH", "DELETE"])
def course(ident):
    item = owned(Course, ident, current_user.id)
    if request.method == "GET":
        return ok(item.public())
    if request.method == "DELETE":
        confirmed()
        for task in item.tasks:
            task.course_id = None
        db.session.delete(item)
        save()
        return ok(
            message="Course deleted. All tasks were preserved as independent study."
        )
    for k, v in course_values(body(request), item).items():
        setattr(item, k, v)
    save()
    return ok(item.public(), "Course updated")


def update_task(item, data, creating=False):
    for key, limit in (("title", 200), ("description", 10000)):
        if key in data or creating:
            setattr(item, key, text(data, key, limit, key == "title"))
    for key, options in (
        ("priority", ("low", "medium", "high")),
        ("status", ("pending", "in_progress", "completed")),
        (
            "task_type",
            (
                "assignment",
                "project",
                "study_session",
                "exam_preparation",
                "reading",
                "other",
            ),
        ),
    ):
        if key in data:
            setattr(item, key, choice(data[key], key, options))
    if "course_id" in data:
        item.course_id = (
            owned(
                Course, identifier(data["course_id"], "course_id"), current_user.id
            ).id
            if data["course_id"] is not None
            else None
        )
    if "estimated_hours" in data:
        item.estimated_hours = (
            None
            if data["estimated_hours"] is None
            else number(data["estimated_hours"], "estimated_hours", 0.016666, 1000)
        )
        if (
            sum((s.end_at - s.start_at).total_seconds() / 3600 for s in item.schedules)
            > (item.estimated_hours or 1) + 0.0001
        ):
            raise ValidationError(
                "estimated_hours",
                "Remove planned sessions before reducing the estimate below allocated time.",
            )
    if "deadline" in data:
        due = (
            instant(data["deadline"], "deadline")
            if data["deadline"] is not None
            else None
        )
        if due and any(s.end_at > due for s in item.schedules):
            raise ValidationError(
                "deadline",
                "Reschedule existing sessions before moving the deadline earlier.",
            )
        if due:
            if item.deadline:
                item.deadline.due_at = due
            else:
                item.deadline = Deadline(due_at=due)
        elif item.deadline:
            item.deadline = None
    if item.status == "completed":
        item.completed_at = item.completed_at or now()
        if item.id:
            db.session.execute(
                db.update(Notification)
                .where(
                    Notification.task_id == item.id,
                    Notification.student_id == current_user.id,
                )
                .values(is_read=True)
            )
    else:
        item.completed_at = None
    item.updated_at = now()


@api.route("/tasks", methods=["GET", "POST"])
def tasks():
    if request.method == "POST":
        item = Task(
            student_id=current_user.id,
            title="",
            priority="medium",
            status="pending",
            task_type="assignment",
        )
        update_task(item, body(request), True)
        db.session.add(item)
        save()
        return ok(item.public(), "Task created", 201)
    items = tasks_for(current_user.id)
    args = request.args
    if args.get("q"):
        items = [t for t in items if args["q"].lower() in t.title.lower()]
    for key in ("course_id", "priority", "status"):
        if args.get(key):
            items = [t for t in items if str(getattr(t, key)) == args[key]]
    if args.get("deadline") == "overdue":
        items = [t for t in items if t.public()["overdue"]]
    if args.get("deadline") == "upcoming":
        items = [
            t
            for t in items
            if t.status != "completed" and t.deadline and t.deadline.due_at >= now()
        ]
    if args.get("due_before"):
        before = instant(args["due_before"], "due_before")
        items = [t for t in items if t.deadline and t.deadline.due_at <= before]
    sort = args.get("sort", "urgency")
    if sort == "due_date":
        items.sort(
            key=lambda t: (t.deadline.due_at if t.deadline else datetime.max, t.id)
        )
    elif sort == "priority":
        items.sort(key=lambda t: ({"high": 0, "medium": 1, "low": 2}[t.priority], t.id))
    else:
        items.sort(key=lambda t: (t.status == "completed", -rank(t)["score"], t.id))
    return ok([t.public() for t in items])


@api.route("/tasks/<int:ident>", methods=["GET", "PATCH", "DELETE"])
def task(ident):
    item = owned(Task, ident, current_user.id)
    if request.method == "GET":
        return ok(item.public())
    if request.method == "DELETE":
        confirmed()
        db.session.delete(item)
        save()
        return ok(message="Task and its planned sessions deleted.")
    update_task(item, body(request))
    save()
    return ok(item.public(), "Task updated")


@api.post("/tasks/<int:ident>/complete")
def complete(ident):
    item = owned(Task, ident, current_user.id)
    data = body(request)
    completed = data.get("completed", True)
    if type(completed) != bool:
        raise ValidationError("completed", "Use true or false.")
    update_task(item, {"status": "completed" if completed else "pending"})
    save()
    return ok(item.public(), "Task completed" if completed else "Task reopened")


@api.route("/deadlines", methods=["GET", "POST"])
@api.get("/deadlines/upcoming")
def deadlines():
    if request.method == "POST":
        data = body(request)
        item = owned(Task, identifier(data.get("task_id"), "task_id"), current_user.id)
        if not data.get("deadline"):
            raise ValidationError("deadline", "A deadline is required.")
        update_task(item, {"deadline": data["deadline"]})
        save()
        return ok(item.public(), "Deadline saved", 201)
    items = [
        t for t in tasks_for(current_user.id) if t.deadline and t.status != "completed"
    ]
    if request.path.endswith("upcoming"):
        items = [t for t in items if t.deadline.due_at >= now()]
    return ok([t.public() for t in sorted(items, key=lambda t: t.deadline.due_at)])


@api.patch("/deadlines/<int:task_id>")
def deadline(task_id):
    item = owned(Task, task_id, current_user.id)
    data = body(request)
    if "deadline" not in data:
        raise ValidationError("deadline", "A deadline field is required.")
    update_task(item, {"deadline": data["deadline"]})
    save()
    return ok(item.public(), "Deadline updated")


@api.get("/priorities/recommendations")
def priorities():
    return ok(ranked(current_user.id))


@api.get("/workload/summary")
def workload():
    start = None
    if request.args.get("start"):
        try:
            start = datetime.strptime(request.args["start"], "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("start", "Use YYYY-MM-DD.")
    return ok(summary(current_user.id, start))


@api.get("/workload/recommendations")
def planner():
    return ok(suggestions(current_user.id))


@api.post("/schedules/accept")
def accept():
    data = body(request)
    sessions = data.get("sessions")
    if not isinstance(sessions, list) or not 1 <= len(sessions) <= 500:
        raise ValidationError("sessions", "Choose 1-500 proposed sessions.")
    result = []
    for value in sessions:
        if not isinstance(value, dict):
            raise ValidationError("sessions", "Each session must be an object.")
        task, start, end = validate_session(current_user.id, value)
        s = Schedule(
            student_id=current_user.id,
            task_id=task.id,
            start_at=start,
            end_at=end,
            source="suggested",
        )
        db.session.add(s)
        db.session.flush()
        result.append(s)
    save()
    return ok([s.public() for s in result], "Suggested sessions accepted", 201)


@api.route("/schedules", methods=["GET", "POST"])
def schedules():
    if request.method == "POST":
        task, start, end = validate_session(current_user.id, body(request))
        s = Schedule(
            student_id=current_user.id, task_id=task.id, start_at=start, end_at=end
        )
        db.session.add(s)
        save()
        return ok(s.public(), "Session scheduled", 201)
    items = list(
        db.session.execute(
            db.select(Schedule)
            .where(Schedule.student_id == current_user.id)
            .order_by(Schedule.start_at)
            .options(db.joinedload(Schedule.task).joinedload(Task.course))
        ).scalars()
    )
    if request.args.get("start"):
        start = instant(request.args["start"], "start")
        items = [s for s in items if s.end_at > start]
    if request.args.get("end"):
        end = instant(request.args["end"], "end")
        items = [s for s in items if s.start_at < end]
    return ok([s.public() for s in items])


@api.route("/schedules/<int:ident>", methods=["GET", "PATCH", "DELETE"])
def schedule(ident):
    item = owned(Schedule, ident, current_user.id)
    if request.method == "GET":
        return ok(item.public())
    if request.method == "DELETE":
        confirmed()
        db.session.delete(item)
        save()
        return ok(message="Session removed; task preserved")
    task, start, end = validate_session(current_user.id, body(request), ident)
    item.task_id = task.id
    item.start_at = start
    item.end_at = end
    item.source = "manual"
    save()
    return ok(item.public(), "Session rescheduled")


@api.get("/dashboard/summary")
def dashboard():
    tasks = tasks_for(current_user.id)
    active = [t for t in tasks if t.status != "completed"]
    completed = len(tasks) - len(active)
    today = local(now(), current_user.preference).date()
    upcoming = sorted(
        [t for t in active if t.deadline and t.deadline.due_at >= now()],
        key=lambda t: t.deadline.due_at,
    )
    return ok(
        {
            "total": len(tasks),
            "pending": len(active),
            "completed": completed,
            "overdue": sum(t.public()["overdue"] for t in active),
            "completion_percent": (
                round(completed / len(tasks) * 100, 1) if tasks else 0
            ),
            "upcoming_count": len(upcoming),
            "deadlines": [t.public() for t in upcoming[:6]],
            "today": [
                s.public()
                for t in active
                for s in t.schedules
                if local(s.start_at, current_user.preference).date() == today
            ],
            "recommendations": ranked(current_user.id)[:4],
            "workload": summary(current_user.id),
        }
    )


@api.get("/notifications")
def notifications():
    items = list(
        db.session.execute(
            db.select(Notification)
            .where(Notification.student_id == current_user.id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
        ).scalars()
    )
    return ok(
        {
            "unread": sum(not n.is_read for n in items),
            "items": [n.public() for n in items],
        }
    )


@api.post("/notifications/refresh")
def refresh():
    return ok({"created": generate(current_user.id)}, "Reminders checked")


@api.post("/notifications/<int:ident>/read")
def read(ident):
    item = owned(Notification, ident, current_user.id)
    item.is_read = True
    save()
    return ok(item.public())


@api.post("/notifications/read-all")
def read_all():
    db.session.execute(
        db.update(Notification)
        .where(Notification.student_id == current_user.id)
        .values(is_read=True)
    )
    save()
    return ok(message="All notifications marked read")
