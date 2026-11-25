# Deployment, SQLite storage and backups

The application now uses SQLite, included with Python. Local development requires no database server or database credentials. Production serving, Nginx/systemd/TLS execution and browser visual acceptance still require verification on the target host.

## Local installation

Follow README: create a virtual environment, install `requirements-lock.txt`, start `python run.py` and open the printed URL to register. Server startup creates the persistent secret, local database and schema automatically. Restarting preserves data. No database URL is required.

Default storage is `/PROJECT/instance/focusflow.db`. SQLite also creates `-wal` and `-shm` sidecar files. The application account must be able to write to the entire directory. Keep the database on one machine's local disk, never a network share or a multi-host replicated directory.

## Linux production

1. Put source in `/srv/focusflow`, owned by a dedicated service user. Create `.venv`, install dependencies and create `/srv/focusflow/instance` owned and writable by the service account (required by systemd ReadWritePaths). Starting the service initializes its database automatically.
2. Store production settings in a restricted `/etc/focusflow.env`:

```dotenv
APP_ENV=production
SECRET_KEY=YOUR_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS
DATABASE_URL=sqlite:////srv/focusflow/instance/focusflow.db
RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
SESSION_IDLE_MINUTES=30
TRUST_PROXY=1
WEB_CONCURRENCY=2
```

SQLite needs no service. Shared Redis rate limiting remains a production security requirement across workers; it is not needed for local use. Keep Redis local/private. `TRUST_PROXY=1` is only for exactly one trusted Nginx proxy with Gunicorn bound to loopback. The supplied Nginx file replaces incoming forwarded headers.

3. Server startup applies versioned upgrades under an operating-system file lock. Back up existing data before deploying a release with new migrations. Multiple workers serialize initialization and then use the same database. The administrative `flask db` commands remain available.
4. Review and copy `deploy/focusflow.service`, `deploy/focusflow-reminders.service` and `deploy/focusflow-reminders.timer` into `/etc/systemd/system/`. The services allow writes to `/srv/focusflow/instance` under their filesystem restrictions. If you change storage location, update `ReadWritePaths` too.
5. Run `sudo systemd-analyze verify /etc/systemd/system/focusflow*.service /etc/systemd/system/focusflow*.timer`, then `sudo systemctl daemon-reload` and `sudo systemctl enable --now focusflow.service focusflow-reminders.timer`.
6. Replace the sample domain and certificate paths in `deploy/nginx.conf`, obtain a valid certificate, install the block, run `sudo nginx -t`, then reload Nginx. Production cookies require HTTPS.
7. Verify `/health`, registration/login, persisted CRUD, planning, calendar, cookie flags and timer execution. Inspect `journalctl -u focusflow -u focusflow-reminders`. Do not declare deployment complete before these succeed.

SQLite serializes transactions across processes. The implementation uses WAL, foreign keys, a 30-second busy timeout and BEGIN IMMEDIATE before session/validation reads. This prevents scheduling races, with a throughput tradeoff: even authenticated GET requests save session data. Use one host and review measured workload before increasing workers. An overloaded writer queue or very large datasets require architectural review rather than simply adding servers.

## Reminders

The supplied systemd timer runs reminders every five minutes and purges expired sessions. On Windows, Task Scheduler can run the absolute `.venv\Scripts\python.exe` with arguments `-m flask --app run reminders`; set Start in to the project directory. Add a daily purge job with `-m flask --app run purge-sessions`. Verify last-run results. These jobs use the same local SQLite file and do not require an active browser.

## Safe backups and restoration

Use the supplied SQLite backup helper, which takes a consistent snapshot including committed WAL data and verifies database integrity:

```powershell
.venv\Scripts\python.exe scripts/backup.py --output backups/focusflow-2026-11-20.db
```

For a custom DATABASE_URL, pass its actual file as `--database`. Existing backup files are never overwritten. Do not copy just an active `.db` file while ignoring its WAL. Store backups and the separate secret/config securely; they contain private account data. Keep them out of Git. Preserve `instance/secret.key` (or your explicitly configured SECRET_KEY) across restarts; replacing it invalidates session/CSRF signatures.

To restore, stop the server and reminder jobs, preserve the current database and sidecars, restore the verified backup as the configured database, ensure ownership/write permissions, then restart and verify login and records. Never discard WAL/SHM files from an active database. Rehearse restoration on an isolated copy before a real incident.

Back up before schema changes. Use reviewed Alembic upgrades/downgrades; a downgrade to base deletes all tables. The automated suite checks fresh installation, rollback and reinstallation only on a disposable database. It does not claim every future data migration is reversible.

No server-database records are automatically imported by this change. Keep any previous records/backups until you have separately verified a data transfer, if needed.

## Release checks

Run pytest against its automatic temporary SQLite files, complete the browser matrix in QA.md, validate Nginx/systemd on Linux, verify TLS and reminders, test backups, and review rate limits for campus networks. No remote deployment, GitHub repository or uptime guarantee is claimed.
