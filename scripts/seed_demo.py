"""Optional demo records. Requires an existing, explicitly selected student."""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

load_dotenv()
from app import create_app
from app.extensions import db
from app.models import Student, Course, Task, Deadline, now
from app.services.planning import lock_student


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    args = p.parse_args()
    app = create_app()
    with app.app_context():
        student = db.session.execute(
            db.select(Student).where(Student.email == args.email.lower())
        ).scalar_one_or_none()
        if not student:
            raise SystemExit("Register this account first.")
        lock_student(student.id)
        if db.session.execute(
            db.select(Task.id).where(Task.student_id == student.id)
        ).first():
            raise SystemExit(
                "Demo seeding requires an empty account, to prevent duplicate academic records."
            )
        for name, code, color in [
            ("Database Systems", "CS201", "#5366de"),
            ("Software Engineering", "SE301", "#3f9b82"),
            ("Research Methods", "RM102", "#cf9552"),
        ]:
            c = Course(
                student_id=student.id,
                name=name,
                code=code,
                color=color,
                semester="Semester 1",
            )
            db.session.add(c)
            db.session.flush()
            for title, hours, days, priority in [
                (f"{name}: weekly assignment", 3, 2, "high"),
                (f"{name}: chapter review", 1.5, 5, "medium"),
            ]:
                t = Task(
                    student_id=student.id,
                    course_id=c.id,
                    title=title,
                    estimated_hours=hours,
                    priority=priority,
                    task_type="assignment",
                )
                t.deadline = Deadline(due_at=now() + timedelta(days=days))
                db.session.add(t)
        db.session.commit()
        print(
            "Created 3 courses and 6 academic tasks. No credentials were created or changed."
        )


if __name__ == "__main__":
    main()
