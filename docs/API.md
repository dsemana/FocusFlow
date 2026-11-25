# FocusFlow JSON API

All paths below are relative to `/api`. Authentication uses the opaque `focusflow_session` cookie. All endpoints except CSRF bootstrap, registration and login require a signed-in student. Resources belonging to another student return 404. Send a JSON object for every POST/PATCH and preserve cookies. All mutations require the CSRF header, including login, registration and logout.

Success: `{"success":true,"message":"Success","data":...}`. Error: `{"success":false,"message":"...","errors":{"field":["..."]}}` (errors may be absent on authentication conflicts). Creation returns 201, other successful operations 200. Codes: 400 validation/CSRF, 401 sign-in required/invalid credentials, 404 unavailable resource, 409 duplicate registration email, 413 oversized body, 429 rate limit, 500 safe generic error. Duplicate course codes/profile emails return 400. Dates are ISO 8601 timestamps with explicit timezone; responses use UTC `Z`.

## Authentication flow

1. GET `/auth/csrf` → `{csrf_token}` and a session cookie.
2. POST `/auth/register` or `/auth/login` with `X-CSRFToken` and that cookie.
3. Successful authentication rotates the cookie and clears the old CSRF value. GET `/auth/csrf` again before the next mutation.

```json
{
  "full_name":"Student Name",
  "email":"student@example.com",
  "password":"YourStrongPassword123!",
  "password_confirmation":"YourStrongPassword123!"
}
```

Login uses `{email,password}`. Register returns the public student `{id,full_name,email}`. GET `/auth/me` returns the same shape. POST `/auth/logout` with `{}` signs out and revokes the cookie. Login is limited to 10/minute/IP; registration to 10/hour/IP; general default 600/minute/IP.

## Endpoint reference

| Method | Endpoint | Request / result |
|---|---|---|
| GET, PATCH | `/profile` | Public student; PATCH full_name, email, password, password_confirmation, current_password. Credential changes require current_password. |
| GET, PATCH | `/preferences` | daily_hours (0.25–16), timezone, study_start/end (`HH:MM`), study_days (0=Mon..6=Sun), reminder_hours (1–720) |
| GET, POST | `/courses` | List courses; create name, code, description, instructor, semester, color (`#RRGGBB`) |
| GET, PATCH, DELETE | `/courses/<id>` | Course details/update/delete; DELETE requires `?confirm=true`, preserves tasks |
| GET, POST | `/tasks` | List tasks; create fields below |
| GET, PATCH, DELETE | `/tasks/<id>` | Task details/update/delete; DELETE requires `?confirm=true` |
| POST | `/tasks/<id>/complete` | `{completed:true}` completes; false reopens; omitted defaults true |
| GET, POST | `/deadlines` | Chronological incomplete dated tasks, including overdue; POST `{task_id,deadline}` creates/updates the canonical deadline |
| GET | `/deadlines/upcoming` | Incomplete tasks with deadlines at/after now, chronological |
| PATCH | `/deadlines/<task_id>` | `{deadline:timestamp}` changes due date; null removes it |
| GET | `/priorities/recommendations` | Array of `{task,score,reason,at_risk,significant_effort}` |
| GET | `/workload/summary` | Summary below; optional `?start=YYYY-MM-DD` selects the first of seven local days |
| GET | `/workload/recommendations` | `{sessions,unplaced,horizon_days,assumed_hours_for_missing_estimate}`; no writes |
| GET, POST | `/schedules` | List sessions; optional start/end ISO range filters; POST `{task_id,start,end}` creates manual session |
| GET, PATCH, DELETE | `/schedules/<id>` | Session details; PATCH complete `{task_id,start,end}`; DELETE `?confirm=true` removes session only |
| POST | `/schedules/accept` | `{sessions:[{task_id,start,end},...]}` validates and accepts 1–500 sessions atomically |
| GET | `/dashboard/summary` | total, pending, completed, overdue, completion_percent, upcoming_count, deadlines, today, recommendations, workload |
| GET | `/notifications` | `{unread,items:[{id,task_id,kind,message,is_read,created_at}]}` |
| POST | `/notifications/refresh` | `{}` triggers idempotent generation for the current student |
| POST | `/notifications/<id>/read` | `{}` marks one notification read |
| POST | `/notifications/read-all` | `{}` marks all owned notifications read |

`GET /health` is outside `/api` and checks database connectivity.

## Task schema and querying

```json
{
  "title":"Database assignment",
  "description":"Normalize the library schema",
  "course_id":1,
  "task_type":"assignment",
  "priority":"high",
  "status":"pending",
  "estimated_hours":3,
  "deadline":"2030-01-07T17:00:00+02:00"
}
```

Only title is required. course_id, estimated_hours, deadline may be null. Estimated hours must be positive and ≤1000. Types: assignment, project, study_session, exam_preparation, reading, other. Importance: low, medium, high. Status: pending, in_progress, completed. Overdue cannot be assigned. Server-generated fields include id, completed_at, created_at, updated_at, overdue, course_name/color and scheduled_date (earliest allocation).

GET `/tasks` accepts `q` (title substring), `course_id`, `priority`, `status`, `deadline=overdue|upcoming`, `due_before` (ISO timestamp), and `sort=urgency|due_date|priority`. Combine filters as query parameters. The UI uses these endpoints for list/cards and the deadline page.

## Workload and planning response

```json
{
  "remaining_hours":3,
  "missing_estimates":0,
  "pending_count":1,
  "daily":[{"date":"2030-01-07","hours":1,"capacity":4}],
  "weekly_hours":1,
  "weekly_capacity":24,
  "by_course":{"Databases":3},
  "by_priority":{"high":3},
  "overloaded_days":[]
}
```

The actual daily array contains seven entries. Proposed sessions include task_id, title, start, end, hours; unplaced entries include task_id, title, unallocated_hours and reason. All accepted/manual sessions are revalidated against current ownership, status, estimate, deadline, availability, daily capacity and overlaps. Invalid selected batches return 400 and leave the schedule unchanged. Retrying an already accepted proposal produces a conflict validation error instead of duplicate sessions.

No pagination is implemented in this academic release; list endpoints return all owned records. Validate expected dataset sizes before a larger deployment.
