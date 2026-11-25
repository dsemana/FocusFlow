# FocusFlow 1.0 — SQLite edition

A complete student productivity application for Divin Semana: private student accounts, courses, tasks, deadlines, explainable priorities, workload planning, calendar, dashboard and in-app reminders.

The database is a local SQLite file. SQLite is included with Python: there is no database server, database account, database password or database installation to configure. Existing features and the Flask/vanilla JavaScript stack are retained.

## Submission and public access

This README documents installation from a downloaded copy of the source. The public deployment URL, repository visibility, and shared video/SRS links still need to be published and verified for assessment. The loopback addresses below open a server running on the reader's own computer. A hosted application URL must be added here when the deployment is available. Hosting configuration is described in [Deployment](docs/DEPLOYMENT.md).

## Get the project

1. Install **Python 3.12 or newer** from the Python website or your operating system's package manager. This release was tested with **Python 3.14 on Windows**. On Windows, enable **Add python.exe to PATH** in the installer, then open a new PowerShell window.
2. On this GitHub repository page, choose **Code → Download ZIP**.
3. Extract the ZIP into a writable folder. Open the extracted project folder containing `run.py`, `run_demo.py`, `requirements-lock.txt`, and `app/`.
4. Open a terminal in that folder. On Windows, right-click inside the folder and choose **Open in Terminal**, then select PowerShell. All commands below run from this project folder.

An internet connection is needed to download Python and install packages. The application includes its frontend libraries. SQLite comes with Python, and the local startup needs only the Python packages installed below.

## First start on Windows

Run each command separately and wait for it to finish before continuing.

1. Check the Python version.

   ```powershell
   python --version
   ```

   It should report Python 3.12 or newer. If Windows recognizes `py` instead of `python`, use `py -3 --version` and `py -3 -m venv .venv` for these first two steps.

2. Create the project's Python environment.

   ```powershell
   python -m venv .venv
   ```

3. Install the exact dependency versions.

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
   ```

4. Start the application.

   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```

5. Keep that terminal open. When it prints `FocusFlow is ready at http://127.0.0.1:5000`, open [FocusFlow](http://127.0.0.1:5000) in Chrome, Edge, Firefox, or Safari.
6. Click **Create an account**, enter your full name, email address, and a password of **10–128 characters containing a letter and a number**, then confirm the password and submit the form.
7. In the student workspace, open **Courses** and add a course. Open **My tasks**, choose **Add task**, and save your first assignment. Use **Calendar** to schedule time or **Workload planner** to review suggestions.

The default workspace starts empty. For an already populated account, follow [Preloaded testing instance](#preloaded-testing-instance) below.

Startup creates `instance/focusflow.db`, generates a persistent signing key at `instance/secret.key`, and applies the migrations automatically. The virtual-environment commands above work without activating the environment or changing PowerShell's execution policy. Local use works with the default configuration.

## First start on Linux or macOS

Complete [Get the project](#get-the-project), then run these commands one at a time from the extracted project folder.

```sh
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python run.py
```

Use Python 3.12 or newer. On Debian/Ubuntu, if the environment creation command reports that `venv` or `ensurepip` is missing, install the venv package matching your Python installation, then repeat the environment creation command.

Keep the terminal open, visit [FocusFlow](http://127.0.0.1:5000), and follow the account creation and first-task steps above. The schema and signing key are created automatically.

## Stop and restart

Press **Ctrl+C** in the server terminal to stop it. Later, open a terminal in the same project folder and run only the startup command.

Windows PowerShell

```powershell
.\.venv\Scripts\python.exe run.py
```

Linux/macOS

```sh
.venv/bin/python run.py
```

Saved accounts and academic records persist across restarts. Keep `instance/` and any optional `.env` on your computer and excluded from Git. Dependency installation is needed on first setup and when a release changes the dependency list.

## Preloaded testing instance

After installing dependencies using the steps above, start the populated testing workspace from the same project folder.

Windows PowerShell

```powershell
.\.venv\Scripts\python.exe run_demo.py
```

Linux/macOS

```sh
.venv/bin/python run_demo.py
```

Keep the terminal open and visit [the testing workspace](http://127.0.0.1:5001). Sign in with **demo@focusflow.test** and **FocusFlowDemo2026!** (also shown on its login page).

It starts with 4 courses, 16 tasks, 8 sessions, deadlines, notifications and sample progress. Everything persists in `instance/demo/focusflow-demo.db`, with a separate secret and session cookie. Your normal `run.py` instance and its data are unaffected. Run both at the same time on ports 5000 and 5001. For another testing port, use `python run_demo.py --port 5002`.

The sample dates are relative to first creation. Restarts preserve your edits rather than duplicating/reseeding records or resetting the demo password. The testing banner identifies this workspace. These are public local-demo credentials, not a production account; the demo runner refuses production mode. See [testing workspace guide](docs/TESTING_INSTANCE.md).

## Setup troubleshooting

| What you see | What to do |
|---|---|
| `python` is unrecognized or opens the Microsoft Store | Use the installed Python launcher's `py -3` command, or rerun the Python installer with the PATH option and reopen PowerShell. |
| `requirements-lock.txt` or `run.py` cannot be found | Open the extracted folder containing those files and run the commands there. |
| A `ModuleNotFoundError` names Flask or another package | Repeat the dependency installation step using the same `.venv` Python executable used to start the app. |
| Port 5000 is already in use | In PowerShell, run `$env:PORT = "5002"`, then run the normal startup command and open `http://127.0.0.1:5002`. On Linux/macOS, run `PORT=5002 .venv/bin/python run.py`. |
| The browser says the site cannot be reached | Confirm the server terminal is still open and displays the ready message. Use its printed host and port. |
| A SQLite or configuration error appears after using an older copy | Review any existing `.env` and shell settings. This edition accepts SQLite database URLs. For a standard local start, use the defaults with `APP_ENV=development`. |
| Login works on one address but asks you to sign in on another | Continue using the same address, such as `127.0.0.1`, throughout the session. Browser cookies are tied to the host. |

To check that the server and its database respond, open [the local health endpoint](http://127.0.0.1:5000/health) while the default server is running. It should return `{"status":"ok"}`. Adjust the port if you changed it.

## Mobile use

The app adapts to phone screens with a navigation drawer, task cards, collapsible filters, a compact agenda/calendar selector, larger touch controls and keyboard-aware editor sheets. No separate mobile build is needed. See [mobile changes and verification](docs/MOBILE.md); real-device visual acceptance remains pending.

## Configuration and database

`DATABASE_URL` is optional and defaults to `sqlite:///focusflow.db`, which resolves under the Flask `instance/` directory, independent of the current working directory. Use `sqlite:///C:/absolute/path/focusflow.db` on Windows or `sqlite:////absolute/path/focusflow.db` on Linux for an alternate local file. Create its parent directory first. An old server-database URL is rejected: remove it from `.env` and your shell environment before starting this edition.

SQLite foreign keys are enabled on every connection. File databases use WAL mode and a 30-second busy timeout. Transactions acquire `BEGIN IMMEDIATE` before reading, so scheduling checks and writes cannot race, including across application processes. SQLite serializes these transactions; see [Technical design](docs/TECHNICAL.md) for limits.

Do not delete `instance/` to update the application: it contains both the database and the persistent signing secret. Startup applies versioned upgrades automatically. The migration command remains available for administrators:

```powershell
.venv\Scripts\python.exe -m flask --app run db upgrade
```

`docs/schema.sql` contains empty SQLite table/index definitions for inspection; migrations are the installation source. [Backup instructions](docs/DEPLOYMENT.md) cover safe SQLite backups, including WAL files. Existing server-database records are not automatically imported; this edition starts with a new SQLite file unless an existing SQLite database is selected.

## Test

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=docs/test-results.xml
```

All tests create their own temporary on-disk SQLite databases. No test database setup or environment variable is needed, and no existing student database is dropped. The suite includes thread/process scheduling contention, persistence, foreign keys, authentication, ownership, CSRF, deadlines, workload, reminders and migration rollback/reinstall.

See [QA results](docs/QA.md) for measured results and remaining verification. Browser visual testing and Linux deployment have not been verified.

To run the optional HTTP load test, use a disposable copy of the project, start `run.py`, then in another terminal run:

```powershell
.venv\Scripts\python.exe scripts/load_test.py --base-url http://127.0.0.1:5000 --users 50 --disposable-database
```

It creates temporary users outside the measured phase, sends real authenticated HTTP requests, then removes its records. Do not run load tests against real student data.

## Reminders and demo

```powershell
.venv\Scripts\python.exe -m flask --app run reminders
.venv\Scripts\python.exe -m flask --app run purge-sessions
.venv\Scripts\python.exe scripts/seed_demo.py --email your-registered-email@example.com
```

The seed command is optional and requires an existing empty account. Schedule reminders independently every five minutes using Task Scheduler or the included Linux timer; see [Deployment](docs/DEPLOYMENT.md). Local use needs no Redis service. A multi-worker HTTPS deployment retains the optional shared Redis rate-limiting requirement described there.

## Project and documentation

`app/` contains the factory, account/academic Blueprints, models, validators, SQLite transaction configuration, session storage, planning/reminder services, Jinja templates and local CSS/JS/vendor assets. `migrations/` contains schema history, `tests/` the regression suite, `scripts/` backup/demo/load helpers, and `deploy/` Linux deployment templates.

- [Requirements and decisions](docs/REQUIREMENTS.md)
- [Requirement traceability](docs/TRACEABILITY.md)
- [Technical design and algorithms](docs/TECHNICAL.md)
- [API reference](docs/API.md)
- [Student guide](docs/USER_GUIDE.md)
- [FAQ](docs/FAQ.md)
- [Deployment and backups](docs/DEPLOYMENT.md)
- [Demonstration](docs/DEMO.md)
- [QA and limitations](docs/QA.md)
- [Sprint plan](docs/SPRINTS.md)

No production deployment or remote GitHub repository is claimed.
