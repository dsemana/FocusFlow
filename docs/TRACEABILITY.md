# Requirement traceability

Test names below are in `tests/test_system.py` unless otherwise indicated. SQLite-specific migration, persistence, integrity and cross-process contention tests are in `tests/test_sqlite.py`; the threaded contention test is in `tests/test_concurrency.py`. Implementation exists for all 34 functional requirements; browser acceptance is pending and listed separately in QA.md. A test mapping indicates the behavior exercised, not proof of every visual or operational attribute.

| ID | Requirement | Implementation | Automated evidence |
|---|---|---|---|
| FR 1.1 | Register | routes/auth.py register, auth.html | test_registration_hash_and_duplicate; test_registration_validation |
| FR 1.2 | Login | routes/auth.py login, session.py | test_login_logout_and_cookie; test_rate_limit |
| FR 1.3 | Logout | routes/auth.py logout, server session deletion | test_revoked_cookie_cannot_replay |
| FR 1.4 | Profile | routes/api.py profile, profilePage | test_profile_and_password_change |
| FR 2.1 | Create course | courses POST, courseEditor | test_course_crud_and_safe_deletion |
| FR 2.2 | View courses | courses GET, coursesPage/cards | test_course_crud_and_safe_deletion; test_ownership_every_resource |
| FR 2.3 | Edit course | course PATCH | test_course_crud_and_safe_deletion |
| FR 2.4 | Delete course | course DELETE, confirmation dialog | test_course_crud_and_safe_deletion |
| FR 3.1 | Create task | tasks POST, taskEditor | test_task_crud_complete_reopen_filters; test_task_validation |
| FR 3.2 | View tasks | tasks GET, list/cards, taskDetails | test_task_crud_complete_reopen_filters |
| FR 3.3 | Edit task | task PATCH | test_task_crud_complete_reopen_filters |
| FR 3.4 | Delete task | task DELETE, confirmation dialog | test_task_crud_complete_reopen_filters |
| FR 3.5 | Complete task | complete endpoint, completion action | test_task_crud_complete_reopen_filters; test_workload_and_completion_dashboard |
| FR 4.1 | Add deadline | Deadline model, deadlines POST/task editor | test_deadlines_and_overdue |
| FR 4.2 | Upcoming deadlines | deadlines/upcoming, dashboard, deadlines page | test_deadlines_and_overdue |
| FR 4.3 | Edit deadline | deadline PATCH/update_task | test_deadlines_and_overdue; test_scheduling_capacity_and_deadline_updates |
| FR 5.1 | Set importance | task priority field/validator | test_task_crud_complete_reopen_filters; test_task_validation |
| FR 5.2 | Recommend priority | planning.rank and ranked | test_priority_formula_and_missing_values |
| FR 5.3 | Order priorities | recommendation API, urgency sort, dashboard | test_priority_formula_and_missing_values; test_task_crud_complete_reopen_filters |
| FR 6.1 | Estimate duration | estimated_hours field/editor | test_task_validation; test_scheduling_capacity_and_deadline_updates |
| FR 6.2 | Calculate workload | planning.summary | test_workload_and_completion_dashboard |
| FR 6.3 | Warn about overload | summary.overloaded_days; reminders.generate | test_reminders_dedupe_overdue_and_overload |
| FR 6.4 | Distribute tasks | planning.suggestions; selected acceptance | test_planning_fits_capacity_and_preserves_manual; test_accept_is_atomic_and_rechecks |
| FR 7.1 | View calendar | calendarPage, FullCalendar, schedules/deadlines API | test_pages_and_security_headers; API schedule/deadline tests; browser pending |
| FR 7.2 | Daily schedule | timeGridDay, schedule range filters | test_schedule_crud_conflicts_ownership; browser pending |
| FR 7.3 | Weekly schedule | timeGridWeek/listWeek, workload chart | test_workload_and_completion_dashboard; browser pending |
| FR 7.4 | Schedule tasks | manual sessions and suggested acceptance | test_schedule_crud_conflicts_ownership; tests/test_concurrency.py; tests/test_sqlite.py |
| FR 8.1 | Dashboard | dashboard summary, dashboard() | test_empty_dashboard; test_workload_and_completion_dashboard |
| FR 8.2 | Upcoming work | dashboard deadlines/today/recommendations | test_deadlines_and_overdue; test_pages_and_security_headers |
| FR 8.3 | Progress | live completed/pending/overdue and completion percent | test_workload_and_completion_dashboard; test_empty_dashboard |
| FR 8.4 | Workload summary | dashboard workload, bar/doughnut charts | test_workload_and_completion_dashboard; browser charts pending |
| FR 9.1 | Deadline reminders | reminders.generate, CLI/timer | test_reminders_dedupe_overdue_and_overload |
| FR 9.2 | Overdue alerts | reminders.generate | test_reminders_dedupe_overdue_and_overload |
| FR 9.3 | Workload alerts | overload dedupe keys | test_reminders_dedupe_overdue_and_overload |

| ID | Implementation/evidence | Verification limit |
|---|---|---|
| NFR 1.1 | 50-user HTTP dashboard/task reads; docs/load-results.json | Browser rendering/WAN not measured |
| NFR 1.2 | HTTP create/update/delete timings | Local disposable database only |
| NFR 1.3 | HTTP workload timing; summary recomputed after writes | Browser chart redraw pending |
| NFR 1.4 | 50 distinct students, 300 requests, barrier-synchronized workers | Short local benchmark, not endurance testing |
| NFR 2.1 | FK policies, transactional API writes, preservation tests | Backup restore drill pending |
| NFR 2.2 | validation.py and parameterized validation tests | Browser validation UX pending |
| NFR 2.3 | confirm=true enforcement, confirmation dialog | Dialog interaction pending |
| NFR 2.4 | safe HTTP/exception handlers and UI error surfaces | Production fault injection pending |
| NFR 3.1 | login_required and test_authentication_required | Verified API enforcement |
| NFR 3.2 | Werkzeug scrypt, test_registration_hash_and_duplicate | Independent penetration test pending |
| NFR 3.3 | owned() and test_ownership_every_resource | Direct SQL users must preserve tenant relationships |
| NFR 3.4 | production secure cookies/HSTS; Nginx TLS config | No deployed certificate/TLS handshake verified |
| NFR 3.5 | WebSession expires_at and expiry/replay tests | Verified server enforcement |
| NFR 4.1 | sidebar, forms, feedback, empty states, guides | Usability sessions pending |
| NFR 4.2 | SQLite transactions, re-query tests, migrations | Long-duration retention not measured |
| NFR 4.3 | health endpoint, service restart policy, timer | No uptime SLA or deployment measured |
| NFR 4.4 | factory/Blueprints/services, documented algorithms, tests | Code review recommended before production |
| NFR 4.5 | standard browser APIs, local JS libraries | Chrome/Firefox/Edge/Safari acceptance pending |
| NFR 4.6 | media queries, collapsible navigation, responsive grids | Mobile/tablet visual testing pending |
| NFR 4.7 | Windows execution; Linux/macOS instructions | Linux/macOS/mobile execution pending |
| NFR 5.1 | private authenticated account data | ownership tests |
| NFR 5.2 | owner-scoped task operations and linked-ID validation | ownership tests |
| NFR 5.3 | owner-scoped course operations | ownership tests |
| NFR 5.4 | calculations use persisted data; no dashboard fixtures | priority/workload/planning tests |
| NFR 5.5 | completed-task filters in ranking/workload/planning/reminders | completion and unplaceable/completed tests |

Automatic startup and self-registration are additionally verified in tests/test_startup.py (first start, restart persistence, simultaneous worker initialization and explicit-secret preservation) and docs/installation-results.json (real HTTP server run).

Mobile navigation, focus containment, filter disclosure, calendar layout configuration and viewport changes have behavioral coverage in tests/frontend/mobile.test.mjs. Physical-device rendering and touch acceptance for NFR 4.5–4.7 remain pending; see docs/MOBILE.md.
