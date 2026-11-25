"""Initial FocusFlow schema

Revision ID: 384b7079d9de
Revises:
Create Date: 2026-11-20 23:10:27.281085

"""

from alembic import op
import sqlalchemy as sa

revision = "384b7079d9de"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "student",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student")),
        sa.UniqueConstraint("email", name=op.f("uq_student_email")),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "web_session",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("token_hash", name=op.f("pk_web_session")),
    )
    with op.batch_alter_table("web_session", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_web_session_expires_at"), ["expires_at"], unique=False
        )
    op.create_table(
        "course",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("instructor", sa.String(length=120), nullable=False),
        sa.Column("semester", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["student.id"],
            name=op.f("fk_course_student_id_student"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course")),
        sa.UniqueConstraint("id", "student_id", name=op.f("uq_course_id")),
        sa.UniqueConstraint("student_id", "code", name=op.f("uq_course_student_id")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("course", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_course_student_id"), ["student_id"], unique=False
        )
    op.create_table(
        "user_preference",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("daily_hours", sa.Float(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("study_start", sa.String(length=5), nullable=False),
        sa.Column("study_end", sa.String(length=5), nullable=False),
        sa.Column("study_days", sa.JSON(), nullable=False),
        sa.Column("reminder_hours", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "daily_hours > 0 AND daily_hours <= 16",
            name=op.f("ck_user_preference_hours_range"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["student.id"],
            name=op.f("fk_user_preference_student_id_student"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("student_id", name=op.f("pk_user_preference")),
    )
    op.create_table(
        "task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("estimated_hours", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "priority IN ('low','medium','high')", name=op.f("ck_task_priority_values")
        ),
        sa.CheckConstraint(
            "status IN ('pending','in_progress','completed')",
            name=op.f("ck_task_status_values"),
        ),
        sa.CheckConstraint(
            "task_type IN ('assignment','project','study_session','exam_preparation','reading','other')",
            name=op.f("ck_task_type_values"),
        ),
        sa.CheckConstraint(
            "estimated_hours IS NULL OR (estimated_hours > 0 AND estimated_hours <= 1000)",
            name=op.f("ck_task_effort_range"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["course.id"],
            name=op.f("fk_task_course_id_course"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["student.id"],
            name=op.f("fk_task_student_id_student"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("task", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_task_course_id"), ["course_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_task_student_id"), ["student_id"], unique=False
        )
        batch_op.create_index(
            "ix_task_student_status", ["student_id", "status"], unique=False
        )
    op.create_table(
        "deadline",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["task.id"],
            name=op.f("fk_deadline_task_id_task"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deadline")),
        sa.UniqueConstraint("task_id", name=op.f("uq_deadline_task_id")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("deadline", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_deadline_due_at"), ["due_at"], unique=False
        )
    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["student.id"],
            name=op.f("fk_notification_student_id_student"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["task.id"],
            name=op.f("fk_notification_task_id_task"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification")),
        sa.UniqueConstraint(
            "student_id", "dedupe_key", name=op.f("uq_notification_student_id")
        ),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("notification", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_notification_student_id"), ["student_id"], unique=False
        )
    op.create_table(
        "schedule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=12), nullable=False),
        sa.CheckConstraint(
            "end_at > start_at", name=op.f("ck_schedule_positive_duration")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["student.id"],
            name=op.f("fk_schedule_student_id_student"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["task.id"],
            name=op.f("fk_schedule_task_id_task"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schedule")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.create_index(
            "ix_schedule_student_time",
            ["student_id", "start_at", "end_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_schedule_task_id"), ["task_id"], unique=False
        )


def downgrade():
    for table in (
        "schedule",
        "notification",
        "deadline",
        "task",
        "user_preference",
        "course",
        "web_session",
        "student",
    ):
        op.drop_table(table)
