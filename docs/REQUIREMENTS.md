# Requirements analysis

Source: the supplied 19-page FocusFlow proposal/SRS, including the requirements tables on PDF pages 9–14 and the four UML diagrams on pages 16–19. The pasted development request supplies implementation details. Instructions inside the PDF are treated as requirements evidence, not independent authority to operate external services.

## Functional scope

The only actor is **Student**. Each student owns private academic information. There is no administrator portal, university integration, email delivery, machine learning, or payment system.

| Module | Requirements | Required behavior |
|---|---|---|
| Accounts | FR 1.1–1.4 | Register, securely authenticate, log out, view and update profile |
| Courses | FR 2.1–2.4 | Create, list, edit, delete courses |
| Tasks | FR 3.1–3.5 | Create, list, edit, delete, complete academic tasks |
| Deadlines | FR 4.1–4.3 | Record assignment/project/examination deadlines, chronological upcoming list, edit dates |
| Priorities | FR 5.1–5.3 | Low/medium/high importance, deterministic recommendations, urgency ordering |
| Workload | FR 6.1–6.4 | Estimate effort, calculate workload, warn about overload, suggest distribution |
| Calendar | FR 7.1–7.4 | Calendar, daily view, weekly view, scheduled sessions |
| Dashboard | FR 8.1–8.4 | Live summaries, upcoming work, task progress, daily/weekly effort |
| Reminders | FR 9.1–9.3 | Upcoming deadlines, overdue tasks, workload warnings |

The request additionally specifies search and filtering, task reopening, optional instructors/course colors, configurable study availability and reminder intervals, selected-session acceptance/rejection, month calendar view, in-app read history, and Windows/Linux installation.

## Non-functional requirements and business rules

- NFR 1.1–1.4: normal page actions within 3s, CRUD within 2s, workload updates within 3s, at least 50 concurrent students. These are measured targets, not guarantees for every deployment.
- NFR 2.1–2.4: preserve student records, validate inputs, confirm destructive changes, return understandable errors.
- NFR 3.1–3.5: authentication, hashed passwords, account privacy, deployed HTTPS, inactivity expiration.
- NFR 4.1–4.7: clear navigation, persistent data, operational availability, modular maintainability, modern-browser portability, responsive desktop/tablet/mobile use, common OS support.
- NFR 5.1–5.5: individual accounts, task/course ownership, calculations based on stored student inputs, completed tasks excluded from remaining workload.

## Architecture and schema decisions

The three tiers are Jinja/HTML/CSS/ES modules; Flask JSON APIs and planning services; relational SQLite storage. See TECHNICAL.md for the schema and algorithms.

1. A task has zero or one Deadline row. Title, activity type, course, and student are reached through Task. This avoids storing two copies of a deadline. The class diagram's many-to-many task/deadline association is refined into one task/one canonical deadline, as explicitly permitted by the request's normalization guidance. `/api/deadlines/<id>` uses the **task ID**.
2. Pending, in_progress, and completed are persisted states. Overdue is calculated from incomplete status and the deadline. The diagram's OVERDUE enum is represented as a derived property, following the request's explicit instruction.
3. Students may create independent-study tasks without a course. A course deletion sets its tasks' course to null; task deletion removes its deadline and schedules, while notification history remains with a null task link. Both APIs require `confirm=true` and the UI asks for confirmation.
4. One task can have many study sessions. The scheduled date is derived from its earliest session. Estimates represent total effort, not tracked elapsed study time. No separate time-tracking feature is assumed.
5. The student preference table stores daily hours, study window, weekdays, timezone, and reminder thresholds. A WebSession table supports server-side sessions and logout revocation.
6. All timestamps are stored as UTC. Incoming API datetimes require a timezone. Planning uses the saved IANA timezone. Calendar display and date inputs use device time and say so explicitly.
7. Missing effort remains unknown in total workload, with a visible missing-estimate count. Planning and ranking assume one hour and explain that assumption. Missing deadlines use a 30-day planning horizon.
8. Sessions use same-day availability windows. Long tasks are split into sessions up to one hour, and unschedulable effort is reported. Manual sessions are never overwritten by suggestions.
9. Notifications are in-app. A CLI job can generate them independently of a browser; deployment scheduling is supplied. Email and push are future enhancements, as allowed by the request.
10. The request asks for deployment preparation, not deployment. Flask/SQLite source stays local; no incompatible hosted runtime is substituted.

The owner explicitly authorized replacing the original MySQL requirement with SQLite on 20 November 2026. This revision removes database-server setup and drivers. The SRS revision table names a different contributor and uses September dates while the filename references October. Authorship displayed by the application follows the user's explicit project owner, Divin Semana; the source document is left unchanged.

## UML correspondence

The use-case diagram maps to the nine navigation modules and APIs. The class diagram maps to Student, Course, Task, Deadline, Schedule, Notification and the supporting preference/session tables. The activity diagram maps login, validation failure, task creation, completion, and refreshed progress to real requests. The sequence diagram maps browser → Flask → SQLite and the independent reminders service; completed task alerts are marked read and future generation excludes completed tasks. Optional profile-picture storage in the class illustration is not implemented because the explicit profile requirements do not require uploads.

## Automatic startup refinement

The owner subsequently requested removal of the setup script. Starting run.py now initializes local storage and schema automatically, while retaining public self-registration. No default account or password is seeded. Startup is serialized across workers, and restarts preserve the database and signing secret.
