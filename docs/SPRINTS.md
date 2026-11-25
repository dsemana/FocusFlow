# Six-sprint Agile plan

These are recommended two-week planning increments for university review. They do not claim that twelve weeks of development, user feedback, or sprint ceremonies occurred during this implementation.

| Sprint | Scope | Review and acceptance |
|---|---|---|
| 1 / weeks 1–2 | Requirements, architecture, schema, migrations, registration/login/profile | Inspect traceability and schema; demonstrate account separation, CSRF, secure hashes and session expiration |
| 2 / weeks 3–4 | Course/task CRUD, deadlines, list/cards and filters | Demonstrate persisted edits, completion/reopening, safe deletion and chronological deadlines |
| 3 / weeks 5–6 | Explainable ranking, workload calculations, planning capacity | Review formula examples, missing estimates, overloads and impossible deadlines with student feedback |
| 4 / weeks 7–8 | Calendar, manual/suggested scheduling, dashboard | Validate month/week/day interactions, atomic acceptance, conflicting concurrent requests and live summaries |
| 5 / weeks 9–10 | Notifications, unattended job, responsive/accessibility refinement | Verify reminder idempotence, read history, mobile workflows and keyboard access; prioritize feedback |
| 6 / weeks 11–12 | Regression, load tests, documentation, deployment rehearsal, demo | Repeat tests against release SQLite, complete browser matrix, rehearse TLS/backups and present demo |

Each sprint should include backlog refinement, implementation, tests, a student-facing review, and a retrospective. Track issues in GitHub after the owner creates a repository; no remote repository was created during this build.
