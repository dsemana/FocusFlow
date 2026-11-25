-- SQLite schema, no student records or credentials. Prefer Alembic migrations.
PRAGMA foreign_keys=ON;

CREATE TABLE course (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
	student_id INTEGER NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	description TEXT NOT NULL, 
	instructor VARCHAR(120) NOT NULL, 
	semester VARCHAR(80) NOT NULL, 
	color VARCHAR(7) NOT NULL, 
	CONSTRAINT fk_course_student_id_student FOREIGN KEY(student_id) REFERENCES student (id) ON DELETE CASCADE, 
	CONSTRAINT uq_course_id UNIQUE (id, student_id), 
	CONSTRAINT uq_course_student_id UNIQUE (student_id, code)
);

CREATE TABLE deadline (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
	task_id INTEGER NOT NULL, 
	due_at DATETIME NOT NULL, 
	CONSTRAINT fk_deadline_task_id_task FOREIGN KEY(task_id) REFERENCES task (id) ON DELETE CASCADE, 
	CONSTRAINT uq_deadline_task_id UNIQUE (task_id)
);

CREATE TABLE notification (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
	student_id INTEGER NOT NULL, 
	task_id INTEGER, 
	kind VARCHAR(24) NOT NULL, 
	message VARCHAR(500) NOT NULL, 
	dedupe_key VARCHAR(200) NOT NULL, 
	is_read BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT fk_notification_student_id_student FOREIGN KEY(student_id) REFERENCES student (id) ON DELETE CASCADE, 
	CONSTRAINT fk_notification_task_id_task FOREIGN KEY(task_id) REFERENCES task (id) ON DELETE SET NULL, 
	CONSTRAINT uq_notification_student_id UNIQUE (student_id, dedupe_key)
);

CREATE TABLE schedule (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
	student_id INTEGER NOT NULL, 
	task_id INTEGER NOT NULL, 
	start_at DATETIME NOT NULL, 
	end_at DATETIME NOT NULL, 
	source VARCHAR(12) NOT NULL, 
	CONSTRAINT ck_schedule_positive_duration CHECK (end_at > start_at), 
	CONSTRAINT fk_schedule_student_id_student FOREIGN KEY(student_id) REFERENCES student (id) ON DELETE CASCADE, 
	CONSTRAINT fk_schedule_task_id_task FOREIGN KEY(task_id) REFERENCES task (id) ON DELETE CASCADE
);

CREATE TABLE student (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT uq_student_email UNIQUE (email)
);

CREATE TABLE task (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
	student_id INTEGER NOT NULL, 
	course_id INTEGER, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	task_type VARCHAR(32) NOT NULL, 
	priority VARCHAR(10) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	estimated_hours FLOAT, 
	completed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	CONSTRAINT ck_task_priority_values CHECK (priority IN ('low','medium','high')), 
	CONSTRAINT ck_task_status_values CHECK (status IN ('pending','in_progress','completed')), 
	CONSTRAINT ck_task_type_values CHECK (task_type IN ('assignment','project','study_session','exam_preparation','reading','other')), 
	CONSTRAINT ck_task_effort_range CHECK (estimated_hours IS NULL OR (estimated_hours > 0 AND estimated_hours <= 1000)), 
	CONSTRAINT fk_task_course_id_course FOREIGN KEY(course_id) REFERENCES course (id) ON DELETE SET NULL, 
	CONSTRAINT fk_task_student_id_student FOREIGN KEY(student_id) REFERENCES student (id) ON DELETE CASCADE
);

CREATE TABLE user_preference (
	student_id INTEGER NOT NULL, 
	daily_hours FLOAT NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	study_start VARCHAR(5) NOT NULL, 
	study_end VARCHAR(5) NOT NULL, 
	study_days JSON NOT NULL, 
	reminder_hours JSON NOT NULL, 
	CONSTRAINT pk_user_preference PRIMARY KEY (student_id), 
	CONSTRAINT ck_user_preference_hours_range CHECK (daily_hours > 0 AND daily_hours <= 16), 
	CONSTRAINT fk_user_preference_student_id_student FOREIGN KEY(student_id) REFERENCES student (id) ON DELETE CASCADE
);

CREATE TABLE web_session (
	token_hash VARCHAR(64) NOT NULL, 
	data JSON NOT NULL, 
	expires_at DATETIME NOT NULL, 
	CONSTRAINT pk_web_session PRIMARY KEY (token_hash)
);

CREATE INDEX ix_course_student_id ON course (student_id);

CREATE INDEX ix_deadline_due_at ON deadline (due_at);

CREATE INDEX ix_notification_student_id ON notification (student_id);

CREATE INDEX ix_schedule_student_time ON schedule (student_id, start_at, end_at);

CREATE INDEX ix_schedule_task_id ON schedule (task_id);

CREATE INDEX ix_task_course_id ON task (course_id);

CREATE INDEX ix_task_student_id ON task (student_id);

CREATE INDEX ix_task_student_status ON task (student_id, status);

CREATE INDEX ix_web_session_expires_at ON web_session (expires_at);
