from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    return value.isoformat(timespec="seconds") + "Z" if value else None


class Student(UserMixin, db.Model):
    __table_args__ = {"sqlite_autoincrement": True}
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    preference = db.relationship(
        "UserPreference",
        uselist=False,
        back_populates="student",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def public(self):
        return {"id": self.id, "full_name": self.full_name, "email": self.email}


class UserPreference(db.Model):
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), primary_key=True
    )
    daily_hours = db.Column(db.Float, default=4, nullable=False)
    timezone = db.Column(db.String(64), default="Africa/Kigali", nullable=False)
    study_start = db.Column(db.String(5), default="09:00", nullable=False)
    study_end = db.Column(db.String(5), default="18:00", nullable=False)
    study_days = db.Column(db.JSON, default=lambda: [0, 1, 2, 3, 4, 5], nullable=False)
    reminder_hours = db.Column(db.JSON, default=lambda: [24, 72], nullable=False)
    student = db.relationship("Student", back_populates="preference")
    __table_args__ = (
        db.CheckConstraint("daily_hours > 0 AND daily_hours <= 16", name="hours_range"),
    )

    def public(self):
        return {
            k: getattr(self, k)
            for k in (
                "daily_hours",
                "timezone",
                "study_start",
                "study_end",
                "study_days",
                "reminder_hours",
            )
        }


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(160), nullable=False)
    code = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    instructor = db.Column(db.String(120), default="", nullable=False)
    semester = db.Column(db.String(80), default="", nullable=False)
    color = db.Column(db.String(7), default="#5366de", nullable=False)
    tasks = db.relationship("Task", back_populates="course", passive_deletes=True)
    __table_args__ = (
        db.UniqueConstraint("student_id", "code"),
        db.UniqueConstraint("id", "student_id"),
        {"sqlite_autoincrement": True},
    )

    def public(self):
        data = {
            k: getattr(self, k)
            for k in (
                "id",
                "name",
                "code",
                "description",
                "instructor",
                "semester",
                "color",
            )
        }
        active = [t for t in self.tasks if t.status != "completed"]
        dates = [
            t.deadline.due_at
            for t in active
            if t.deadline and t.deadline.due_at >= now()
        ]
        data.update(
            task_count=len(self.tasks),
            pending_count=len(active),
            completed_count=len(self.tasks) - len(active),
            next_deadline=iso(min(dates)) if dates else None,
        )
        return data


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id = db.Column(
        db.Integer, db.ForeignKey("course.id", ondelete="SET NULL"), index=True
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    task_type = db.Column(db.String(32), default="assignment", nullable=False)
    priority = db.Column(db.String(10), default="medium", nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    estimated_hours = db.Column(db.Float, nullable=True)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    course = db.relationship("Course", back_populates="tasks")
    deadline = db.relationship(
        "Deadline", uselist=False, back_populates="task", cascade="all, delete-orphan"
    )
    schedules = db.relationship(
        "Schedule", back_populates="task", cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification", back_populates="task", passive_deletes=True
    )
    __table_args__ = (
        db.CheckConstraint(
            "priority IN ('low','medium','high')", name="priority_values"
        ),
        db.CheckConstraint(
            "status IN ('pending','in_progress','completed')", name="status_values"
        ),
        db.CheckConstraint(
            "estimated_hours IS NULL OR (estimated_hours > 0 AND estimated_hours <= 1000)",
            name="effort_range",
        ),
        db.CheckConstraint(
            "task_type IN ('assignment','project','study_session','exam_preparation','reading','other')",
            name="type_values",
        ),
        db.Index("ix_task_student_status", "student_id", "status"),
        {"sqlite_autoincrement": True},
    )

    def public(self):
        data = {
            k: getattr(self, k)
            for k in (
                "id",
                "course_id",
                "title",
                "description",
                "task_type",
                "priority",
                "status",
                "estimated_hours",
            )
        }
        data.update(
            deadline=iso(self.deadline.due_at) if self.deadline else None,
            overdue=bool(
                self.status != "completed"
                and self.deadline
                and (self.deadline.due_at < now())
            ),
            completed_at=iso(self.completed_at),
            created_at=iso(self.created_at),
            updated_at=iso(self.updated_at),
            course_name=self.course.name if self.course else "Independent study",
            course_color=self.course.color if self.course else "#5366de",
            scheduled_date=(
                iso(min((s.start_at for s in self.schedules)))
                if self.schedules
                else None
            ),
        )
        return data


class Deadline(db.Model):
    __table_args__ = {"sqlite_autoincrement": True}
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    due_at = db.Column(db.DateTime, nullable=False, index=True)
    task = db.relationship("Task", back_populates="deadline")


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), nullable=False
    )
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    source = db.Column(db.String(12), default="manual", nullable=False)
    task = db.relationship("Task", back_populates="schedules")
    __table_args__ = (
        db.CheckConstraint("end_at > start_at", name="positive_duration"),
        db.Index("ix_schedule_student_time", "student_id", "start_at", "end_at"),
        {"sqlite_autoincrement": True},
    )

    def public(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.task.title,
            "start": iso(self.start_at),
            "end": iso(self.end_at),
            "source": self.source,
            "color": self.task.course.color if self.task.course else "#5366de",
            "completed": self.task.status == "completed",
        }


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id = db.Column(db.Integer, db.ForeignKey("task.id", ondelete="SET NULL"))
    kind = db.Column(db.String(24), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    dedupe_key = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    task = db.relationship("Task", back_populates="notifications")
    __table_args__ = (
        db.UniqueConstraint("student_id", "dedupe_key"),
        {"sqlite_autoincrement": True},
    )

    def public(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "kind": self.kind,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": iso(self.created_at),
        }


class WebSession(db.Model):
    token_hash = db.Column(db.String(64), primary_key=True)
    data = db.Column(db.JSON, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
