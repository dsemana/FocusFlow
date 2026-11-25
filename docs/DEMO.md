# University demonstration

Use a disposable demonstration account and future deadlines relative to the actual presentation date. The optional seed command can prepare an empty registered account; its records are real database rows.

1. Register a new student and show the empty overview. Sign out and back in to demonstrate authentication.
2. Add a course such as Database Systems, CS201. Show its detail card.
3. Add an assignment with high importance, a deadline tomorrow, and 3h estimated effort. Add a reading task with low importance and a later deadline.
4. Open the overview and compare their recommendation scores and explanations.
5. Set your current timezone, available weekdays, a 09:00–18:00 study window, and a 4h daily limit in Preferences.
6. Open Workload planner. Explain remaining estimated effort versus scheduled daily workload.
7. Generate suggestions. Review times, deselect one session, discard the proposal, then generate again and accept selected sessions. Verify that discarding did not save anything.
8. Open Calendar. Switch Month → Week → Day. Click a study session, reschedule it within availability, then try an overlapping or after-deadline time to show validation.
9. Complete a task in My tasks. Return to Overview and show updated completion percentage and reduced remaining effort. Reopen it and observe the change.
10. Open Notifications and Check reminders. A task due within 24h produces a reminder. Mark it read and refresh; it should not duplicate.
11. Run `flask --app run reminders` from a second terminal with the browser closed to demonstrate independent reminder generation.
12. Show the automated test results, SQLite migration, 50-user local benchmark, traceability matrix, and known verification limits. Do not claim production deployment or browser compatibility results that have not been verified.

Before presenting, complete the manual browser acceptance checklist in QA.md. Do not expose production credentials or personal student records during a screen share.
