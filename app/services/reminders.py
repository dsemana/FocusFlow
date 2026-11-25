from datetime import timedelta
from ..extensions import db
from ..models import Student, Notification, Task, now
from .planning import lock_student, tasks_for, summary, local


def generate(student_id, at=None):
    at = at or now()
    student = lock_student(student_id)
    count = 0
    existing = set(
        db.session.execute(
            db.select(Notification.dedupe_key).where(
                Notification.student_id == student_id
            )
        ).scalars()
    )

    def add(kind, message, key, task_id=None):
        nonlocal count
        if key not in existing:
            db.session.add(
                Notification(
                    student_id=student_id,
                    task_id=task_id,
                    kind=kind,
                    message=message[:500],
                    dedupe_key=key,
                )
            )
            existing.add(key)
            count += 1

    for task in tasks_for(student_id):
        if task.status == "completed" or not task.deadline:
            continue
        due = task.deadline.due_at
        hours = (due - at).total_seconds() / 3600
        base = f"{task.id}:{due.isoformat()}"
        if hours < 0:
            add(
                "overdue",
                f"{task.title} is overdue. Review its deadline and study plan.",
                "overdue:" + base,
                task.id,
            )
        else:
            # Emit the closest due interval only; each threshold is generated at most once.
            intervals = [h for h in student.preference.reminder_hours if hours <= h]
            if intervals:
                h = min(intervals)
                add(
                    "deadline",
                    f"{task.title} is due within {h} hours.",
                    f"deadline:{base}:{h}",
                    task.id,
                )
    workload = summary(student_id, days=30, start=local(at, student.preference).date())
    for day in workload["overloaded_days"]:
        add(
            "overload",
            f"{day['date']}: {day['hours']:g}h planned exceeds {day['capacity']:g}h available.",
            f"overload:{day['date']}:{day['hours']}:{day['capacity']}",
        )
    db.session.commit()
    return count
