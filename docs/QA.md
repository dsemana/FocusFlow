# Quality assurance — SQLite edition

Latest regression date: 22 November 2026. This report replaces the previous database-server benchmark; all results below belong to the SQLite build.

## Executed checks

| Check | Actual result |
|---|---|
| Clean dependency installation | Installed requirements-lock.txt into a new virtual environment; no MySQL driver or cryptography package present; pip check passed |
| Automated regression | **71 passed in 33.79s**, no skips, failures or warnings; test-results.xml |
| Competing threads | Four simultaneous bookings: exactly one succeeded, three rejected |
| Competing processes | Four barrier-synchronized processes sharing one SQLite file: exactly one booking succeeded |
| SQLite integrity | Foreign keys enabled, WAL active, integrity_check returned ok |
| Fresh migrations | Upgrade → downgrade to base → reinstall passed in the automated suite |
| Schema drift | flask db check: no new upgrade operations detected |
| Fresh server start | python run.py created its secret and database without .env or any manual initialization |
| Server restart | Retained the self-registered account, task, session cookie and persistent signing key |
| Application workflow | Academic API regression passed; an actual server allowed HTTP self-registration and task creation without prior setup |
| Simultaneous first starts | Three processes initialized one shared schema and signing key safely |
| Entry point | Started from a different working directory; printed URL before serving; setup script absent |
| Persistence | Records available from a separately created application instance |
| Backup | SQLite backup API snapshot passed integrity and saved-record checks |
| Independent reminders/purge | Both CLI commands executed successfully |
| Source checks | JavaScript syntax and Python compilation passed |

Environment: Windows, Python 3.14, SQLite 3.50.4 (included with Python). Additional evidence: installation-results.json and migration-results.json. No database server or database credentials were used for these checks.

## Mobile update verification

Ten Node responsive-control tests passed on 21 November 2026. Public/private page rendering, self-registration, static assets and conditional library inclusion also passed. The tests simulate controls; they do not verify rendered layouts, physical touch targets or actual mobile keyboards. See MOBILE.md, mobile-results.json and mobile-test-results.xml. The prior SQLite HTTP benchmark below remains unchanged because the academic APIs were not modified.

## 50-user HTTP benchmark

The prior SQLite-only benchmark (the academic API is unchanged by the startup refinement) served real HTTP requests through Waitress (four threads). Fifty authenticated accounts each created, listed, updated and deleted a task and requested workload/dashboard summaries. Accounts were prepared outside the timed phase. This is a short local benchmark with small per-account datasets, not a sustained production test or a browser rendering measurement.

| Metric | Observed |
|---|---|
| Users / requests | 50 / 300 |
| Errors | 0 |
| Measured duration | 3.601s |
| Throughput | 83.31 requests/s |
| Median | 477.38ms |
| 95th percentile | 706.91ms |
| Slowest request | 2062.11ms (task creation) |
| Slowest dashboard | 1825.65ms |
| Slowest workload summary | 1484.31ms |

The slowest create slightly exceeded the original 2s CRUD target (2.062s); the other measured endpoint maxima were below their targets. This is reported as a performance limit rather than full compliance. SQLite serializes transactions, including session writes, so contention should be measured for the intended deployment. Complete grouped timings are in load-results.json. Concurrent login, WAN, TLS, large histories and browser rendering were not measured.

## Known limits

- Browser visual, responsive and cross-browser acceptance remains unverified because earlier local browser access was declined; it was not retried through another mechanism.
- Linux Gunicorn/Nginx/systemd/TLS deployment has not been executed. Templates were updated for writable SQLite storage and removal of the database service dependency.
- SQLite storage must be local to one host. Transactions use BEGIN IMMEDIATE for correctness across threads/processes, with a throughput tradeoff. No multi-host scaling claim is made.
- Shared Redis rate limiting remains a production-only requirement; local execution needs no Redis server.
- No existing server-database records are automatically imported. The included setup creates/preserves SQLite data only.
- Endpoints are unpaginated; study windows are same-day; workload is estimated rather than elapsed time; absent estimates use a stated 1h planning assumption.
- Completed calendar sessions remain historical until removed. Password recovery, email/push delivery and photo uploads remain outside this release.
- No production deployment, GitHub publication or uptime guarantee is claimed.

## Manual browser acceptance checklist

Run at desktop 1440×900, tablet 768×1024 and phone 390×844 in current Chrome, Firefox, Edge and Safari. Record browser/version and pass/fail evidence rather than assuming support.

- Register, reject duplicate email and weak/mismatched password, log out/in, and wait for inactivity expiry.
- Open the empty overview; verify no invented academic records or hardcoded statistics.
- Create/edit/delete courses; verify confirmation and preservation of tasks.
- Create/edit/delete tasks; try every type/status/priority, optional course/date/estimate, title search, each filter, sorts, cards/list, and detail dialogs.
- Complete/reopen work and verify real dashboard counts, progress, workload and notification badges after refresh.
- Set study hours/weekdays/timezone; test invalid preferences and reminder intervals.
- Generate a plan, discard it, generate again, select a subset and accept; verify persistence and rejection of stale/conflicting proposals.
- Navigate month/week/day/list calendar views; edit and remove a session; test deadlines, overlap, capacity and completed-session behavior.
- View in-app alerts, follow related tasks, mark one/all read, and verify repeated refresh creates no duplicates.
- Update name/email/password with current-password checks; verify other sessions end after a password change.
- Use keyboard only: skip link, navigation, form labels, focus indicators, dialog focus trapping/Escape, confirmations and toast feedback.
- Inspect overflow, chart labels, calendar controls and text at all viewport sizes; verify no clipped controls or inaccessible actions.
- Inspect browser console/network errors and accessible names; record and fix failures before presenting.

The definition of done's browser and deployed-environment verification items remain open. No production-ready or fully cross-browser-tested claim is made.


## Phone-preview login regression

Five new tests reproduced the previous failures before the fix (401 responses on browser identity changes and 302 redirects back to login after mobile sign-in). All five pass with application-scoped SESSION_PROTECTION=basic. The full suite passed 66 tests in 33.22s; the 10 responsive-control tests also passed. Current-password verification after an identity change, CSRF, logout revocation, password-change revocation and idle expiration remain covered. The active server was restarted and /health returned HTTP 200. Interactive Chrome/Edge testing was not performed by the agent; the regression tests simulate their desktop and mobile request headers.


## Preloaded testing instance

On 22 November 2026, the full Python suite passed 71 tests in 33.79s and the 10 responsive-control tests passed. Five new tests cover seeded academic data/login, restart idempotence and preservation of edits, separation from the ordinary database/secret/cookie, refusal to seed a normal workspace and refusal to run as production. Live HTTP checks on port 5001 verified login, 4 courses, 16 tasks (3 completed, 2 overdue), 8 sessions and 6 notifications. This workspace is stored only in instance/demo/ and uses focusflow_demo_session. See demo-instance-results.json and TESTING_INSTANCE.md. The main instance is not seeded or reset.
