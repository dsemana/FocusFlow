"""Deterministic ranking and capacity-constrained, explicit-acceptance planning."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from flask import current_app
from ..models import Task, Schedule, Student, UserPreference, now, iso
from ..extensions import db
from ..validation import ValidationError, instant, identifier


def owned(model, ident, student_id):
    item = db.session.execute(
        db.select(model).where(model.id == ident, model.student_id == student_id)
    ).scalar_one_or_none()
    if not item:
        from werkzeug.exceptions import NotFound

        raise NotFound("Record not found.")
    return item


def lock_student(student_id):
    # SQLite transactions already hold a database-wide writer reservation.
    return db.session.execute(
        db.select(Student).where(Student.id == student_id)
    ).scalar_one()


def tasks_for(student_id):
    return list(
        db.session.execute(
            db.select(Task)
            .where(Task.student_id == student_id)
            .options(
                db.selectinload(Task.deadline),
                db.selectinload(Task.course),
                db.selectinload(Task.schedules),
            )
        ).scalars()
    )


def rank(task, at=None):
    at = at or now()
    due = task.deadline.due_at if task.deadline else None
    hours = (due - at).total_seconds() / 3600 if due else None
    urgency = 0 if hours is None else 1 if hours <= 0 else 1 / (1 + hours / 24)
    importance = {"low": 0.2, "medium": 0.6, "high": 1}[task.priority]
    effort = task.estimated_hours or 1
    pressure = 0 if hours is None else min(1, effort / max(hours, 1))
    weights = current_app.config.get("PRIORITY_WEIGHTS", (0.55, 0.30, 0.15))
    score = round(
        100 * sum(a * b for a, b in zip(weights, (urgency, importance, pressure))), 2
    )
    reason = (
        "Overdue"
        if hours is not None and hours < 0
        else f"Due in {max(0,hours):.0f} hours" if hours is not None else "No deadline"
    )
    reason += f"; {task.priority} importance; {effort:g}h estimated effort"
    if task.estimated_hours is None:
        reason += " (1h planning assumption: add an estimate)"
    return {
        "task": task.public(),
        "score": score,
        "reason": reason,
        "at_risk": hours is not None and effort > max(0, hours),
        "significant_effort": effort >= 4,
    }


def ranked(student_id, at=None):
    return sorted(
        (rank(t, at) for t in tasks_for(student_id) if t.status != "completed"),
        key=lambda v: (-v["score"], v["task"]["deadline"] or "9999", v["task"]["id"]),
    )


def local(value, pref):
    return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(pref.timezone))


def utc(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def interval_hours(start, end):
    return (end - start).total_seconds() / 3600


def daily_allocations(schedules, pref):
    totals = defaultdict(float)
    for s in schedules:
        start, end = local(s.start_at, pref), local(s.end_at, pref)
        while start < end:
            stop = min(
                end,
                datetime.combine(
                    start.date() + timedelta(days=1),
                    time(),
                    tzinfo=ZoneInfo(pref.timezone),
                ),
            )
            totals[start.date()] += interval_hours(utc(start), utc(stop))
            start = stop
    return totals


def summary(student_id, start=None, days=7):
    pref = db.session.get(UserPreference, student_id)
    today = local(now(), pref).date()
    start = start or today - timedelta(days=today.weekday())
    tasks = tasks_for(student_id)
    active = [t for t in tasks if t.status != "completed"]
    schedules = [s for t in active for s in t.schedules]
    totals = daily_allocations(schedules, pref)
    daily = [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "hours": round(totals[start + timedelta(days=i)], 2),
            "capacity": (
                pref.daily_hours
                if (start + timedelta(days=i)).weekday() in pref.study_days
                else 0
            ),
        }
        for i in range(days)
    ]
    by_course = defaultdict(float)
    by_priority = defaultdict(float)
    unknown = 0
    for t in active:
        by_course[t.course.name if t.course else "Independent study"] += (
            t.estimated_hours or 0
        )
        by_priority[t.priority] += t.estimated_hours or 0
        unknown += t.estimated_hours is None
    return {
        "remaining_hours": round(sum(t.estimated_hours or 0 for t in active), 2),
        "missing_estimates": unknown,
        "pending_count": len(active),
        "daily": daily,
        "weekly_hours": round(sum(d["hours"] for d in daily), 2),
        "weekly_capacity": sum(d["capacity"] for d in daily),
        "by_course": dict(by_course),
        "by_priority": dict(by_priority),
        "overloaded_days": [d for d in daily if d["hours"] > d["capacity"]],
    }


def suggestions(student_id, at=None, horizon=30):
    at = at or now()
    pref = db.session.get(UserPreference, student_id)
    tasks = tasks_for(student_id)
    existing = [s for t in tasks for s in t.schedules]
    busy = [(s.start_at, s.end_at) for s in existing]
    used = daily_allocations(
        [s for s in existing if s.task.status != "completed"], pref
    )
    first = local(at, pref).date()
    zone = ZoneInfo(pref.timezone)
    proposals = []
    unplaced = []
    active = sorted(
        [t for t in tasks if t.status != "completed"],
        key=lambda t: (-rank(t, at)["score"], t.id),
    )
    for t in active:
        allocated = sum(interval_hours(s.start_at, s.end_at) for s in t.schedules)
        remaining = max(0, (t.estimated_hours or 1) - allocated)
        due = t.deadline.due_at if t.deadline else at + timedelta(days=horizon)
        for i in range(horizon):
            if remaining < 0.001:
                break
            day = first + timedelta(days=i)
            if day.weekday() not in pref.study_days:
                continue
            cursor = max(
                at,
                utc(
                    datetime.combine(
                        day, time.fromisoformat(pref.study_start), tzinfo=zone
                    )
                ),
            )
            # Slots use an absolute 15-minute grid, including on DST transition days.
            cursor = cursor.replace(second=0, microsecond=0)
            if cursor < at:
                cursor += timedelta(minutes=1)
            if cursor.minute % 15:
                cursor += timedelta(minutes=15 - cursor.minute % 15)
            stop = min(
                due,
                utc(
                    datetime.combine(
                        day, time.fromisoformat(pref.study_end), tzinfo=zone
                    )
                ),
            )
            while (
                cursor < stop
                and remaining > 0.001
                and used[day] < pref.daily_hours - 0.001
            ):
                blockers = sorted((a, b) for a, b in busy if a < stop and b > cursor)
                overlap = next(((a, b) for a, b in blockers if a <= cursor < b), None)
                if overlap:
                    cursor = overlap[1]
                    continue
                free_end = min([a for a, b in blockers if a > cursor] + [stop])
                hours = min(
                    1,
                    remaining,
                    pref.daily_hours - used[day],
                    interval_hours(cursor, free_end),
                )
                if hours < 1 / 60:
                    cursor = free_end
                    continue
                end = cursor + timedelta(hours=hours)
                proposals.append(
                    {
                        "task_id": t.id,
                        "title": t.title,
                        "start": iso(cursor),
                        "end": iso(end),
                        "hours": round(hours, 2),
                    }
                )
                busy.append((cursor, end))
                used[day] += hours
                remaining -= hours
                cursor = end
        if remaining > 0.001:
            unplaced.append(
                {
                    "task_id": t.id,
                    "title": t.title,
                    "unallocated_hours": round(remaining, 2),
                    "reason": "Insufficient availability before deadline or within the 30-day planning horizon.",
                }
            )
    return {
        "sessions": proposals,
        "unplaced": unplaced,
        "horizon_days": horizon,
        "assumed_hours_for_missing_estimate": 1,
    }


def validate_session(student_id, data, exclude_id=None):
    task = owned(Task, identifier(data.get("task_id"), "task_id"), student_id)
    if task.status == "completed":
        raise ValidationError("task_id", "Reopen the task before scheduling.")
    start, end = instant(data.get("start"), "start"), instant(data.get("end"), "end")
    if end <= start:
        raise ValidationError("end", "End must be after start.")
    if task.deadline and end > task.deadline.due_at:
        raise ValidationError("end", "A session cannot end after its task deadline.")
    pref = db.session.get(UserPreference, student_id)
    a, b = local(start, pref), local(end, pref)
    if (
        a.date() != b.date()
        or a.weekday() not in pref.study_days
        or a.time().replace(tzinfo=None) < time.fromisoformat(pref.study_start)
        or b.time().replace(tzinfo=None) > time.fromisoformat(pref.study_end)
    ):
        raise ValidationError(
            "start", "Choose a session inside your available study days and hours."
        )
    existing = list(
        db.session.execute(
            db.select(Schedule).where(
                Schedule.student_id == student_id,
                Schedule.id != exclude_id if exclude_id else db.true(),
            )
        ).scalars()
    )
    if any(s.start_at < end and s.end_at > start for s in existing):
        raise ValidationError("start", "This session overlaps an existing activity.")
    daily = daily_allocations(
        [s for s in existing if s.task.status != "completed"], pref
    )
    if daily[a.date()] + interval_hours(start, end) > pref.daily_hours + 0.0001:
        raise ValidationError(
            "end",
            "Daily workload limit exceeded. Change your availability or choose another day.",
        )
    total = sum(
        interval_hours(s.start_at, s.end_at) for s in existing if s.task_id == task.id
    )
    if total + interval_hours(start, end) > (task.estimated_hours or 1) + 0.0001:
        raise ValidationError(
            "end",
            "Scheduled effort exceeds the task estimate (default 1h). Update the estimate first.",
        )
    return task, start, end
