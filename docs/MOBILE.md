# Mobile improvements

Updated 21 November 2026. The application still starts with `python run.py`, initializes SQLite automatically, and allows self-registration.

## Changes

- At widths up to 760px, navigation uses a scrollable drawer with a close button and backdrop. Opening it makes background controls inert and contains keyboard focus; closing with the button, backdrop, or Escape returns focus. Resizing to desktop restores normal navigation.
- Tasks start in cards on small screens. The optional list view becomes labeled, stacked records rather than a wide table. Completion, editing, deletion, dates, course, priority, status and effort remain available.
- Search stays visible. Filters and sorting sit behind a disclosure button on phones, with an active-filter count. Desktop filters remain visible. Changing layouts retains the selected filter values.
- The calendar starts in agenda view on phones. A labeled selector offers Month, Week, Day and Agenda, with compact date navigation. Desktop keeps its full toolbar.
- Mobile form fields use 16px text, with larger buttons, checkboxes and icon targets. Weekday selection, notifications, course cards, chart legends and summary cards wrap for narrow screens.
- Task/course/session editors become bottom sheets with sticky headings and actions. VisualViewport changes adjust available space when the keyboard opens; browser zoom remains enabled.
- Sticky top navigation, safe-area padding, independent drawer scrolling, wrapped long text and small-screen progress layouts reduce crowding. The viewport does not impose zoom limits.
- Authentication and task/course pages no longer include chart/calendar library downloads. Charts load only on Overview/Planner; FullCalendar loads only on Calendar.

## Executed verification

- 61 Python tests passed, including authentication, ownership, scheduling, SQLite persistence and automatic startup.
- 10 Node behavioral tests passed: inert/focus behavior, menu closing methods, Tab wrapping, desktop/mobile transitions, filter toggling and listener cleanup, calendar configuration, and keyboard/zoom viewport calculations.
- All public and private page templates rendered; authenticated registration and static asset requests succeeded. Page-specific script inclusion and JavaScript syntax were checked.

Run optional frontend behavior tests with Node 20+:

```sh
node --test tests/frontend/mobile.test.mjs
```

Node is only needed for these development checks; the app itself still runs on Python. Results are in `mobile-test-results.xml` and `mobile-results.json`.

These tests use simulated DOM controls and do not render a mobile browser. Actual layout, touch/keyboard behavior, screenshots and iOS/Android browser compatibility remain unverified. Earlier browser access was declined, and the browser tool is currently unavailable. No alternate browser-control mechanism was used.

## Device acceptance checklist

Check portrait widths 320, 360, 390 and 430px, phone landscape, tablet 768px and desktop 1440px. Use real Safari/iOS and Chrome/Android where possible.

1. Register and sign in; focus every field, zoom text and rotate the device. Confirm no field or submission action becomes unreachable.
2. Open/close navigation using all controls; scroll to Preferences/Sign out, use keyboard Tab/Escape, and resize across 760px with the drawer open and closed.
3. Create tasks with long titles/descriptions and course names. Use cards/list, complete/reopen, edit/delete, and confirm every task field remains readable without page-wide horizontal scrolling.
4. Expand filters, apply several, collapse and reopen, then rotate. Check the count, preserved values and result updates.
5. Open task/course/session editors with the keyboard displayed. Scroll to every field and action; check safe areas and closing/confirmation behavior.
6. Switch every calendar view, navigate dates, and open/edit events. Check the agenda, long titles and week/day time grids.
7. Inspect dashboard/planner charts, legends, progress rings, notifications, course cards and weekday preferences for clipping, overlapping text and inaccessible controls.
8. Confirm the desktop layout and all original workflows still function after returning to a wide viewport.

Complete these rendered-device checks before claiming full mobile-browser acceptance.


## Device-preview authentication correction

The server previously used strong fingerprint revocation, which logged users out when phone emulation changed the User-Agent. Session protection now uses the basic policy: a changed fingerprint marks the session non-fresh while preserving authentication. Credential changes continue to require the current password. Five additional regressions cover desktop/phone transitions, login with different document/fetch User-Agents, and credential verification. These simulate Chrome/Edge-style request headers; they do not claim interactive browser verification.
