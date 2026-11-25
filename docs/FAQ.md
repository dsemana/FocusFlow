# FAQ and troubleshooting

**Why was my session rejected?** Check your saved study weekdays/window, daily limit, task estimate, deadline, and overlapping events. Planned sessions cannot exceed the task estimate. Set a realistic estimate before allocating more time.

**Why is some work unallocated?** The engine could not fit it before the deadline within your availability and the next 30 days. Increase realistic availability, reduce scope, or revisit the deadline. It never silently moves existing sessions.

**Why is my work remaining lower than expected?** Missing estimates are unknown and are excluded from the sum. Their count is shown; add estimates. The planner uses a stated 1h assumption for those tasks.

**Does completion automatically remove calendar sessions?** Sessions remain as historical records and display muted. They do not contribute to active workload. Remove a future session if you want to free its calendar slot. Existing calendar activities remain protected from overlaps.

**Do reminders work when the browser is closed?** Yes, when `flask --app run reminders` is scheduled independently. The application stores in-app messages; it does not deliver email or push notifications. Check the systemd timer or Windows Task Scheduler history.

**I changed my availability but existing sessions exceed it.** They are preserved intentionally. The planner and reminders warn about overloaded days so you can reschedule them.

**Why are displayed times different from planning hours?** Calendar and editable dates use device time. The planner checks availability in your saved timezone. Choose the timezone where you study, and verify your device clock.

**Where is the database?** By default, `instance/focusflow.db` inside the project. After installing dependencies, just run `python run.py`: the database and persistent secret are created automatically. SQLite ships with Python; there is no database account or server to install. If DATABASE_URL still points to a server database, remove that override from `.env` and your shell.

**The database is locked or read-only.** Keep the file on a local disk, allow the application to write to the database and its directory (including WAL/SHM sidecar files), and stop external tools holding long write transactions. Requests wait up to 30 seconds for the writer slot. Use the documented backup API rather than copying an active database file.

**Do I need to configure SECRET_KEY?** No: by default the server generates and retains `instance/secret.key`. If you explicitly set SECRET_KEY in an optional `.env` or environment, it must be at least 32 random characters; the example placeholder is rejected. Remove an unwanted override to use the generated key. Preserve the instance directory between restarts.

**I receive a CSRF error.** Reload the page and submit again. Your browser must permit same-origin cookies. The app deliberately requires CSRF tokens even for login and registration.

**I receive 429 Too Many Requests.** Wait for the rate-limit window to expire. Production must use Redis for shared limits across workers. The per-IP defaults may need tuning for students behind a shared campus network.

**I cannot sign in over HTTP in production.** Production cookies require HTTPS. Configure TLS at Nginx and use the HTTPS URL. Do not disable secure cookies to bypass this.

**Do tests need a database?** No setup is needed: each test creates its own temporary SQLite file. Tests do not read TEST_DATABASE_URL or drop an existing student database.

**Where is password recovery?** This release supports authenticated password change only. Email verification and forgotten-password recovery are future enhancements and were not mandatory in the supplied requirements.

**Does it work in all browsers?** It uses standard APIs and responsive CSS, but cross-browser and visual acceptance have not been executed in this environment. See QA.md and run the supplied manual checklist before presenting or deploying.


**Phone preview logged me out or kept sending me back to login.** Older builds revoked sessions whenever the browser User-Agent changed. Device emulation can change that header. The updated build retains the login while marking the session non-fresh, and still checks your current password before credential changes. After updating/restarting the server, refresh and sign in once if the old session was already revoked. Keep using the same hostname (for example 127.0.0.1 rather than switching to localhost), since browser cookies are scoped to a host.
