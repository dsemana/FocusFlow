# FocusFlow working directory

This folder, D:/Workspace/FocusFlow, is the user-selected working copy for all future FocusFlow updates. Apply changes directly here rather than only updating an exported archive or another copy.

Preserve instance/, .env and .venv when editing or synchronizing source. They hold the local SQLite database, persistent signing secret, configuration and Python environment.

The app starts with python run.py. Startup initializes SQLite and applies migrations automatically. Public self-registration is supported; there is no separate setup script or seeded account in the normal app. The optional run_demo.py testing instance has its own seeded account, database, secret and session cookie under instance/demo/.

Run Python checks from this directory: .venv/Scripts/python.exe -m pytest -q. Optional responsive behavior tests: node --test tests/frontend/mobile.test.mjs. These are behavioral unit checks, not a substitute for rendered mobile-device verification.
