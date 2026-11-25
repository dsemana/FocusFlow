# Preloaded testing workspace

Start with `.venv\Scripts\python.exe run_demo.py`, then open http://127.0.0.1:5001. The runner initializes and seeds its own SQLite file automatically; no setup command is needed.

- Email: `demo@focusflow.test`
- Initial password: `FocusFlowDemo2026!`
- Storage: `instance/demo/focusflow-demo.db`
- Session cookie: `focusflow_demo_session`
- Alternate port: `python run_demo.py --port 5002`

The normal instance remains at port 5000 and uses its existing database and cookie. Cookies are not isolated by TCP port, so this runner deliberately uses a different cookie name as well as a different database and signing secret.

## Sample data

Four courses: Database Systems, Software Engineering, Discrete Mathematics and Research Methods. Sixteen academic tasks include pending/in-progress work, three completed tasks, two overdue tasks, several activity types/priorities, independent study and a missing estimate. Eight scheduled sessions populate the calendar and today's plan. Deadlines are relative to the first seed time.

The account has a 4h preferred daily limit. Today's pre-existing 5.5h allocation demonstrates the app's real behavior after a student reduces availability: existing sessions remain, while the planner and notification system flag overload. Sessions do not overlap or extend past their task deadlines. Deadline/overdue/overload notifications are generated through the normal service; one starts marked read to demonstrate history.

Try filters, priorities, completion/reopening, calendar editing, selected plan acceptance, preferences, notifications and mobile navigation. All operations use the actual backend and SQLite storage.

## Persistence and isolation

Only an empty, dedicated demo database is seeded. Subsequent starts retain your changes and never reset the account, password, task edits or schedule. Editing/deleting these examples does not affect your normal workspace. The testing banner and credentials appear only in demo mode. Ordinary self-registration remains available in both instances; newly registered accounts start empty.

If you change the demo credentials, use your updated credentials. The printed/login-page credentials are the initial values. A fresh reset can be arranged separately; restarting is intentionally not a destructive reset.

The demo ignores the ordinary DATABASE_URL and SECRET_KEY, binds to loopback and refuses APP_ENV=production. There is no authentication bypass or automatic sign-in. All sample credentials are for local testing only.
