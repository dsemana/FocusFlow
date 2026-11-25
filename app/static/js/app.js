import {
  MOBILE_QUERY,
  calendarLayout,
  initNavigation,
  initTaskFilters,
  initViewport,
} from "./responsive.js";
const mobileMedia = window.matchMedia(MOBILE_QUERY);
let disposeTaskFilters = () => {};
const $ = (s, r = document) => r.querySelector(s),
  $$ = (s, r = document) => [...r.querySelectorAll(s)];
const page = document.body.dataset.page;
let csrf = $('meta[name="csrf-token"]').content,
  user,
  prefs,
  courses = [],
  items = [],
  view = mobileMedia.matches ? "cards" : "list",
  proposals = [],
  calendar,
  charts = [];
const paths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  check:
    '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="m8 12 3 3 5-6"/>',
  book: '<path d="M12 6c-3-3-7-3-10-2v15c4-1 7-1 10 2 3-3 6-3 10-2V4c-3-1-7-1-10 2v15"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  calendar:
    '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4m8-4v4M8 14h2m4 0h2"/>',
  chart: '<path d="M4 3v17h17M8 15v-4m5 4V7m5 8v-6"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-9 12h6"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  settings:
    '<path d="m10 2-.6 3-2 1-3-.9-2 3 2.2 2.1v2.6L2.4 15l2 3 3-.9 2 1 .6 3h4l.6-3 2-1 3 .9 2-3-2.2-2.1v-2.6L21.6 8l-2-3-3 .9-2-1L14 2z"/><circle cx="12" cy="11.5" r="3"/>',
  spark:
    '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>',
  logout: '<path d="M10 3H4v18h6m5-14 5 5-5 5m-8-5h13"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  edit: '<path d="m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-5-5L4 14z"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h1m-1 6h1m-1 6h1"/>',
  leaf: '<path d="M20 3C8 2 2 8 5 16c8 4 15-1 15-13ZM4 21 16 9"/>',
};
const icon = (n) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">${paths[n] || paths.check}</svg>`;
const e = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function hydrate() {
  $$("[data-icon]").forEach((el) => (el.innerHTML = icon(el.dataset.icon)));
}
function toast(message, error = false) {
  $("#toast").textContent = message;
  $("#toast").className = "visible" + (error ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("#toast").className = ""), 5000);
}
const fail = (err) => toast(err.message, true);
async function api(path, method = "GET", data) {
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
    ...(data === undefined ? {} : { body: JSON.stringify(data) }),
  });
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401 && !["login", "register"].includes(page))
      location.assign("/login");
    throw new Error(
      result.errors && Object.keys(result.errors).length
        ? Object.values(result.errors).flat().join(" ")
        : result.message || "The request could not be completed.",
    );
  }
  return result.data;
}
async function token() {
  csrf = (await api("/auth/csrf")).csrf_token;
}
const date = (v, o = {}) =>
  v
    ? new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        ...o,
      }).format(new Date(v))
    : "No deadline";
const dt = (v) => date(v, { hour: "2-digit", minute: "2-digit" }),
  tm = (v) =>
    date(v, {
      month: undefined,
      day: undefined,
      hour: "2-digit",
      minute: "2-digit",
    });
function relative(v) {
  if (!v) return "No deadline";
  const h = (new Date(v) - Date.now()) / 36e5;
  return h < 0
    ? "Overdue"
    : h < 1
      ? "Due this hour"
      : h < 24
        ? `In ${Math.ceil(h)} hours`
        : `In ${Math.ceil(h / 24)} days`;
}
function inputDate(v) {
  if (!v) return "";
  const d = new Date(v);
  return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
const pill = (v, label = v) =>
  `<span class="pill ${e(v)}">${e(label.replaceAll("_", " "))}</span>`;
const btn = (action, title, id, type = "quiet", symbol = "") =>
  `<button type="button" class="${type}" data-action="${action}" ${id ? `data-id="${id}"` : ""}>${symbol ? icon(symbol) : ""}${e(title)}</button>`;
const ib = (a, title, id, s) =>
  `<button type="button" class="icon-button" data-action="${a}" data-id="${id}" title="${e(title)}" aria-label="${e(title)}">${icon(s)}</button>`;
const empty = (title, text, action = "") =>
  `<div class="empty">${icon("leaf")}<strong>${e(title)}</strong><p>${e(text)}</p>${action}</div>`;
const heading = (
  title,
  sub,
  actions = "",
  eyebrow = "A LITTLE CLARITY FOR YOUR DAY",
) =>
  `<div class="page-heading"><div><div class="eyebrow">${e(eyebrow)}</div><h1>${e(title)}</h1><p>${e(sub)}</p></div><div class="heading-actions">${actions}</div></div>`;
const panel = (title, sub, content, link = "") =>
  `<section class="panel"><div class="panel-head"><div><h2>${e(title)}</h2>${sub ? `<p>${e(sub)}</p>` : ""}</div>${link}</div>${content}</section>`;
const meta = (t) =>
  `<span><i class="course-dot" style="background:${e(t.course_color)}"></i>${e(t.course_name)}</span>`;
function bar(selector, daily) {
  if (!globalThis.Chart || !$(selector)) return;
  charts.push(
    new Chart($(selector), {
      type: "bar",
      data: {
        labels: daily.map((d) =>
          new Date(d.date + "T12:00:00").toLocaleDateString(undefined, {
            weekday: "short",
          }),
        ),
        datasets: [
          {
            label: "Planned hours",
            data: daily.map((d) => d.hours),
            backgroundColor: daily.map((d) =>
              d.hours > d.capacity ? "#d58188" : "#6a7ce3",
            ),
            borderRadius: 5,
            maxBarThickness: 28,
          },
          {
            label: "Available hours",
            data: daily.map((d) => d.capacity),
            backgroundColor: "#edf0f8",
            borderRadius: 5,
            maxBarThickness: 28,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: {
              color: "#697389",
              font: { size: 12 },
              maxRotation: 0,
              minRotation: 0,
            },
          },
          y: {
            beginAtZero: true,
            suggestedMax: 4,
            border: { display: false },
            grid: { color: "#f0f2f8" },
            ticks: {
              stepSize: 2,
              color: "#939aae",
              font: { size: 12 },
              callback: (v) => v + "h",
            },
          },
        },
      },
    }),
  );
}
const legend =
  '<div class="legend"><span><i></i>Planned workload</span><span><i class="light"></i>Daily availability</span></div>';
async function calendarPage() {
  $("#content").innerHTML =
    heading(
      "Give your week some space.",
      "See your study sessions and deadlines together.",
      btn("session-new", "Schedule time", null, "primary", "plus"),
      "YOUR TIME, THOUGHTFULLY PLANNED",
    ) +
    '<section class="calendar-panel"><label class="calendar-view-label">Calendar view<select id="calendar-view"><option value="dayGridMonth">Month</option><option value="timeGridWeek">Week</option><option value="timeGridDay">Day</option><option value="listWeek">Agenda</option></select></label><div id="calendar"></div><div class="calendar-note"><span>Solid events: study sessions</span><span>Deadline events: due dates</span></div><p class="help" style="margin:15px 0 0">Calendar times use your device timezone. Planning availability uses ' +
    e(prefs.timezone) +
    ". Click an event to view or edit.</p></section>";
  if (!globalThis.FullCalendar)
    throw new Error("The local calendar library could not load.");
  calendar = new FullCalendar.Calendar($("#calendar"), {
    ...calendarLayout(mobileMedia.matches),
    height: "auto",
    timeZone: "local",
    buttonText: {
      today: "Today",
      month: "Month",
      week: "Week",
      day: "Day",
      list: "List",
    },
    datesSet: (info) => {
      const select = $("#calendar-view");
      if (select) select.value = info.view.type;
    },
    windowResize: () => {
      if (!calendar) return;
      calendar.setOption(
        "headerToolbar",
        calendarLayout(mobileMedia.matches).headerToolbar,
      );
      calendar.updateSize();
    },
    firstDay: 1,
    nowIndicator: true,
    events: async (info, success, failure) => {
      try {
        const [s, d] = await Promise.all([
          api(
            "/schedules?" +
              new URLSearchParams({ start: info.startStr, end: info.endStr }),
          ),
          api("/deadlines"),
        ]);
        success([
          ...s.map((v) => ({
            id: "s" + v.id,
            title: v.title,
            start: v.start,
            end: v.end,
            backgroundColor: v.completed ? "#a3acbf" : v.color,
            borderColor: "transparent",
            extendedProps: { kind: "session", recordId: v.id },
          })),
          ...d.map((t) => ({
            id: "d" + t.id,
            title: "Due: " + t.title,
            start: t.deadline,
            backgroundColor: "#fff0f0",
            textColor: "#aa4c58",
            borderColor: "#ebccd1",
            extendedProps: { kind: "deadline", recordId: t.id },
          })),
        ]);
      } catch (err) {
        failure(err);
        fail(err);
      }
    },
    eventClick: (info) => {
      const v = info.event.extendedProps;
      (v.kind === "session"
        ? sessionEditor(v.recordId)
        : taskDetails(v.recordId)
      ).catch(fail);
    },
  });
  calendar.render();
  $("#calendar-view").value = calendar.view.type;
  $("#calendar-view").onchange = (event) =>
    calendar.changeView(event.target.value);
}
async function plannerPage() {
  const w = await api("/workload/summary");
  const stats = [
    [
      "Remaining effort",
      w.remaining_hours + "h",
      w.pending_count + " active tasks",
    ],
    ["Planned this week", w.weekly_hours + "h", "Across your study sessions"],
    [
      "Weekly capacity",
      w.weekly_capacity + "h",
      prefs.daily_hours + "h per available day",
    ],
    [
      "Overloaded days",
      w.overloaded_days.length,
      w.missing_estimates + " tasks need estimates",
    ],
  ];
  $("#content").innerHTML =
    heading(
      "A plan that leaves room to live.",
      "Distribute work around your time, energy, and deadlines.",
      btn("generate-plan", "Suggest a study plan", null, "primary", "spark"),
      "YOUR WORKLOAD, IN BALANCE",
    ) +
    `<div class="stats">${stats.map(([l, v, n]) => `<div class="stat"><div class="stat-head">${l}</div><div class="stat-value">${v}</div><div class="stat-note">${n}</div></div>`).join("")}</div>` +
    (w.overloaded_days.length
      ? `<div class="notice">${w.overloaded_days.map((d) => `${e(d.date)}: ${d.hours}h planned, ${d.capacity}h available`).join("<br>")}</div>`
      : "") +
    `<div class="columns"><div class="stack">${panel("Your weekly workload", "Planned effort alongside your preferred availability.", '<div class="panel-body"><div class="chart-wrap"><canvas id="planner-chart" role="img" aria-label="Workload and capacity"></canvas></div>' + legend + "</div>")}${panel("Workload by course", "Estimated effort for incomplete tasks.", '<div class="panel-body"><div class="chart-wrap compact"><canvas id="course-chart" role="img" aria-label="Remaining workload by course"></canvas></div></div>')}</div><div class="stack">${panel("Your planning preferences", "A plan that fits around you.", `<div class="panel-body"><div class="progress-detail"><div><span>Daily limit</span><strong>${prefs.daily_hours} hours</strong></div><div><span>Study window</span><strong>${e(prefs.study_start)} – ${e(prefs.study_end)}</strong></div><div><span>Study days</span><strong>${prefs.study_days.length} days / week</strong></div><div><span>Timezone</span><strong>${e(prefs.timezone)}</strong></div></div><a class="secondary full" href="/settings">Edit availability</a></div>`)}${panel("Workload by importance", "Where your remaining effort goes.", `<div class="panel-body progress-detail">${["high", "medium", "low"].map((p) => `<div><span>${pill(p)}</span><strong>${w.by_priority[p] || 0}h</strong></div>`).join("")}</div>`)}<div class="notice info">Plans use a 30-day horizon and sessions of up to one hour. Existing sessions stay in place. Review suggestions before accepting them.</div></div></div><div id="plan-results" style="margin-top:24px"></div>`;
  bar("#planner-chart", w.daily);
  if (globalThis.Chart)
    charts.push(
      new Chart($("#course-chart"), {
        type: "bar",
        data: {
          labels: Object.keys(w.by_course),
          datasets: [
            {
              label: "Remaining hours",
              data: Object.values(w.by_course),
              backgroundColor: "#8190e6",
              borderRadius: 5,
              maxBarThickness: 24,
            },
          ],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              beginAtZero: true,
              grid: { color: "#f1f3f8" },
              border: { display: false },
            },
            y: {
              grid: { display: false },
              border: { display: false },
              ticks: {
                font: { size: 12 },
                callback: function (value) {
                  const label = this.getLabelForValue(value);
                  const limit = mobileMedia.matches ? 16 : 26;
                  return label.length > limit
                    ? label.slice(0, limit - 1) + "…"
                    : label;
                },
              },
            },
          },
        },
      }),
    );
}
async function generatePlan(b) {
  b.disabled = true;
  b.textContent = "Finding space in your week…";
  try {
    const p = await api("/workload/recommendations");
    proposals = p.sessions;
    $("#plan-results").innerHTML =
      (p.unplaced.length
        ? `<div class="notice"><strong>Some work needs a closer look.</strong><br>${p.unplaced.map((v) => `${e(v.title)}: ${v.unallocated_hours}h could not fit. ${e(v.reason)}`).join("<br>")}</div>`
        : "") +
      panel(
        "Your suggested study plan",
        `${proposals.length} sessions. Select the ones that work for you.`,
        proposals.length
          ? proposals
              .map(
                (s, i) =>
                  `<div class="suggestion-row"><label><input type="checkbox" class="proposal-check" value="${i}" checked aria-label="Select session for ${e(s.title)}"></label><div class="task-info"><strong class="task-title">${e(s.title)}</strong><p>${e(dt(s.start))} – ${e(tm(s.end))}</p></div><span class="pill low">${s.hours}h</span></div>`,
              )
              .join("") +
              `<div class="panel-body inline-actions" style="padding-top:18px">${btn("accept-plan", "Accept selected sessions", null, "primary", "check")}${btn("reject-plan", "Discard suggestions", null, "secondary")}</div>`
          : empty(
              "No new sessions to suggest",
              "Work may already be scheduled, or no time is available before deadlines.",
            ),
      );
    $("#plan-results").scrollIntoView({ behavior: "smooth", block: "start" });
  } finally {
    b.disabled = false;
    b.innerHTML = icon("spark") + "Suggest a study plan";
  }
}
async function notificationsPage() {
  const d = await api("/notifications");
  $("#content").innerHTML =
    heading(
      "A gentle heads-up.",
      "Deadlines, overdue work, and workload updates in one place.",
      btn(
        "refresh-notifications",
        "Check reminders",
        null,
        "secondary",
        "bell",
      ) + btn("read-all", "Mark all read", null, "primary", "check"),
      "STAY IN THE KNOW",
    ) +
    `<section class="panel">${d.items.length ? d.items.map((n) => `<article class="notification-item ${n.is_read ? "" : "unread"}"><span class="stat-icon ${n.kind === "overdue" ? "red" : n.kind === "overload" ? "orange" : ""}">${icon(n.kind === "overload" ? "chart" : "bell")}</span><div class="task-info"><strong class="task-title">${e({ deadline: "A deadline is approaching", overdue: "A task needs your attention", overload: "Make a little more space" }[n.kind] || "Update")}</strong><p>${e(n.message)}</p><small>${e(dt(n.created_at))}</small>${n.task_id ? ` <button class="quiet" data-action="task-details" data-id="${n.task_id}">View task</button>` : ""}</div>${n.is_read ? '<span class="muted" style="font-size:.75rem">Read</span>' : btn("notification-read", "Mark read", n.id, "secondary")}</article>`).join("") : empty("You’re all caught up", "Reminders will appear as deadlines approach.")}</section>`;
}
async function profilePage() {
  $("#content").innerHTML =
    heading(
      "Your space, your details.",
      "Keep your account up to date.",
      "",
      "MAKE IT YOURS",
    ) +
    `<section class="panel settings-panel"><div class="panel-head"><h2>Personal information</h2><span class="avatar">${e(user.full_name[0])}</span></div><div class="panel-body"><form id="profile-form">${field("full_name", "Full name", user.full_name, "text", true, 'maxlength="120"')}${field("email", "Email address", user.email, "email", true)}<div class="settings-section"><h3>Account security</h3><p>Enter your current password to change your email or password.</p>${field("current_password", "Current password", "", "password", false, 'autocomplete="current-password"')}${field("password", "New password (optional)", "", "password", false, 'autocomplete="new-password" minlength="10" maxlength="128"')}${field("password_confirmation", "Confirm new password", "", "password", false, 'autocomplete="new-password"')}</div><div class="form-error" id="profile-error" role="alert"></div><button class="primary" type="submit">Save profile</button></form></div></section>`;
  $("#profile-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const b = $('button[type="submit"]', ev.target);
    b.disabled = true;
    try {
      const d = Object.fromEntries(new FormData(ev.target));
      if (d.email === user.email) delete d.email;
      if (!d.password) {
        delete d.password;
        delete d.password_confirmation;
      }
      user = await api("/profile", "PATCH", d);
      await token();
      toast("Your profile is up to date.");
      await profilePage();
    } catch (err) {
      $("#profile-error").textContent = err.message;
    } finally {
      b.disabled = false;
    }
  };
}
async function settingsPage() {
  prefs = await api("/preferences");
  const p = prefs;
  $("#content").innerHTML =
    heading(
      "Find your natural rhythm.",
      "Tell FocusFlow when and how much you want to study.",
      "",
      "A HEALTHIER STUDY ROUTINE",
    ) +
    `<section class="panel settings-panel"><div class="panel-head"><h2>Study availability</h2></div><div class="panel-body"><form id="settings-form"><div class="field-grid">${field("daily_hours", "Preferred maximum hours per day", p.daily_hours, "number", true, 'min="0.25" max="16" step="0.25"')}${field("timezone", "Planning timezone", p.timezone, "text", true, 'maxlength="64"')}${field("study_start", "Study window starts", p.study_start, "time", true)}${field("study_end", "Study window ends", p.study_end, "time", true)}</div><p class="help">Use an IANA timezone, for example Africa/Kigali or Europe/London. Study windows start and end on the same day.</p><h3>Your available days</h3><div class="days">${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, i) => `<label><input type="checkbox" name="study_days" value="${i}" ${p.study_days.includes(i) ? "checked" : ""}>${d}</label>`).join("")}</div><div class="settings-section"><h3>Deadline reminders</h3>${field("reminder_hours", "Hours before deadline (comma-separated)", p.reminder_hours.join(", "), "text", true)}<p class="help">For example 24, 72 sends reminders one and three days before a deadline. Scheduled jobs run separately from your browser.</p></div><div class="notice info">Changing availability preserves existing sessions. Overloaded dates are highlighted in the planner and notifications.</div><div id="settings-error" class="form-error" role="alert"></div><button class="primary" type="submit">Save preferences</button></form></div></section>`;
  $("#settings-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const b = $('button[type="submit"]', ev.target);
    b.disabled = true;
    try {
      const f = new FormData(ev.target),
        d = Object.fromEntries(f);
      d.daily_hours = Number(d.daily_hours);
      d.study_days = f.getAll("study_days").map(Number);
      d.reminder_hours = d.reminder_hours
        .split(",")
        .map((v) => Number(v.trim()));
      prefs = await api("/preferences", "PATCH", d);
      toast("Your study rhythm has been saved.");
    } catch (err) {
      $("#settings-error").textContent = err.message;
    } finally {
      b.disabled = false;
    }
  };
}
function confirmDelete(text, action) {
  $("#confirm-text").textContent = text;
  $("#confirm-dialog").showModal();
  $("#confirm-delete").onclick = async () => {
    const b = $("#confirm-delete");
    b.disabled = true;
    try {
      await action();
      $("#confirm-dialog").close();
      if ($("#editor").open) $("#editor").close();
      await render();
      toast("Deleted successfully.");
    } catch (err) {
      fail(err);
    } finally {
      b.disabled = false;
    }
  };
}
async function render() {
  disposeTaskFilters();
  disposeTaskFilters = () => {};
  charts.forEach((c) => c.destroy());
  charts = [];
  if (calendar) {
    calendar.destroy();
    calendar = null;
  }
  const views = {
    dashboard,
    tasks: () => tasksPage(),
    deadlines: () => tasksPage(true),
    courses: coursesPage,
    calendar: calendarPage,
    planner: plannerPage,
    notifications: notificationsPage,
    profile: profilePage,
    settings: settingsPage,
  };
  await views[page]();
  hydrate();
}
async function action(ev) {
  const b = ev.target.closest("[data-action]");
  if (!b) return;
  const id = b.dataset.id ? Number(b.dataset.id) : null;
  try {
    switch (b.dataset.action) {
      case "new-task":
      case "task-edit":
        if ($("#editor").open) $("#editor").close();
        await taskEditor(id);
        break;
      case "task-details":
        await taskDetails(id);
        break;
      case "new-course":
      case "course-edit":
        if ($("#editor").open) $("#editor").close();
        await courseEditor(id);
        break;
      case "course-details":
        await courseDetails(id);
        break;
      case "task-delete":
        confirmDelete(
          "Delete this task permanently? Its deadline and study sessions will also be removed. Notification history is preserved.",
          () => api("/tasks/" + id + "?confirm=true", "DELETE"),
        );
        break;
      case "course-delete":
        confirmDelete(
          "Remove this course? All its tasks, deadlines, and sessions will be preserved as independent study.",
          () => api("/courses/" + id + "?confirm=true", "DELETE"),
        );
        break;
      case "complete": {
        b.disabled = true;
        const t = await api("/tasks/" + id);
        await api("/tasks/" + id + "/complete", "POST", {
          completed: t.status !== "completed",
        });
        if ($("#editor").open) $("#editor").close();
        await render();
        toast(
          t.status === "completed"
            ? "Task reopened."
            : "A little progress worth celebrating.",
        );
        break;
      }
      case "session-new":
      case "session-edit":
        if ($("#editor").open) $("#editor").close();
        await sessionEditor(
          b.dataset.action === "session-edit" ? id : null,
          b.dataset.action === "session-new" ? id : null,
        );
        break;
      case "session-delete":
        confirmDelete(
          "Remove this study session? The task and deadline stay in place.",
          () => api("/schedules/" + id + "?confirm=true", "DELETE"),
        );
        break;
      case "generate-plan":
        await generatePlan(b);
        break;
      case "accept-plan": {
        const selected = $$(".proposal-check:checked").map(
          (c) => proposals[Number(c.value)],
        );
        if (!selected.length) throw new Error("Select at least one session.");
        b.disabled = true;
        await api("/schedules/accept", "POST", { sessions: selected });
        await render();
        toast("Your selected sessions are now on the calendar.");
        break;
      }
      case "reject-plan":
        proposals = [];
        $("#plan-results").innerHTML = "";
        toast("Suggestions discarded.");
        break;
      case "refresh-notifications":
        b.disabled = true;
        await api("/notifications/refresh", "POST", {});
        await render();
        await badge();
        toast("Reminders checked.");
        break;
      case "read-all":
        await api("/notifications/read-all", "POST", {});
        await render();
        await badge();
        break;
      case "notification-read":
        await api("/notifications/" + id + "/read", "POST", {});
        await render();
        await badge();
        break;
    }
  } catch (err) {
    b.disabled = false;
    fail(err);
  }
}
async function init() {
  initViewport();
  hydrate();
  if (["login", "register"].includes(page)) {
    $("#auth-form").onsubmit = async (ev) => {
      ev.preventDefault();
      const b = $('button[type="submit"]', ev.target);
      b.disabled = true;
      $("#form-error").textContent = "";
      try {
        await token();
        await api(
          "/auth/" + page,
          "POST",
          Object.fromEntries(new FormData(ev.target)),
        );
        location.assign("/dashboard");
      } catch (err) {
        $("#form-error").textContent = err.message;
        b.disabled = false;
      }
    };
    return;
  }
  $("#current-date").textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(new Date());
  document.addEventListener("click", action);
  $("#close-editor").onclick = $("#cancel-editor").onclick = () =>
    $("#editor").close();
  $("#confirm-cancel").onclick = () => $("#confirm-dialog").close();
  initNavigation({
    doc: document,
    media: mobileMedia,
    sidebar: $("#sidebar"),
    shell: $(".app-shell"),
    trigger: $("#menu"),
    close: $("#close-navigation"),
    backdrop: $("#nav-backdrop"),
  });
  $("#logout").onclick = async () => {
    try {
      await api("/auth/logout", "POST", {});
      location.assign("/login");
    } catch (err) {
      fail(err);
    }
  };
  try {
    [user, prefs, courses] = await Promise.all([
      api("/auth/me"),
      api("/preferences"),
      api("/courses"),
    ]);
    await render();
    await api("/notifications/refresh", "POST", {});
    await badge();
    const q = new URLSearchParams(location.search);
    if (q.get("task")) await taskDetails(Number(q.get("task")));
  } catch (err) {
    $("#content").innerHTML = empty(
      "Your workspace needs a moment",
      err.message,
      '<a class="secondary" href="/dashboard">Try again</a>',
    );
  }
}
init();
async function tasksPage(deadlines = false) {
  $("#content").innerHTML =
    heading(
      deadlines
        ? "Every deadline, in sight."
        : "A little focus. Real progress.",
      deadlines
        ? "Assignments, projects, and exam preparation in one place."
        : "Make your next step a clear one.",
      btn("new-task", "Add task", null, "primary", "plus"),
      "YOUR ACADEMIC TO-DO",
    ) +
    `<div class="toolbar"><input id="search" type="search" placeholder="Search your tasks…" aria-label="Search tasks"><button type="button" id="filter-toggle" class="secondary filter-toggle" aria-controls="task-filters" aria-expanded="false">${icon("settings")} <span id="filter-label">Filters & sort</span></button><div id="task-filters" class="filter-controls"><select id="course-filter" aria-label="Filter by course"><option value="">All courses</option>${courses.map((c) => `<option value="${c.id}">${e(c.name)}</option>`).join("")}</select><select id="status-filter" aria-label="Filter by status"><option value="">All statuses</option><option value="pending">Pending</option><option value="in_progress">In progress</option><option value="completed">Completed</option></select><select id="priority-filter" aria-label="Filter by priority"><option value="">All priorities</option><option>high</option><option>medium</option><option>low</option></select><select id="deadline-filter" aria-label="Filter by deadline"><option value="">All deadlines</option><option value="upcoming">Upcoming</option><option value="overdue">Overdue</option></select><select id="sort" aria-label="Sort tasks"><option value="urgency">By urgency</option><option value="due_date" ${deadlines ? "selected" : ""}>By deadline</option><option value="priority">By priority</option></select></div><div class="view-switch"><button id="list-view" class="active" aria-label="List view">${icon("list")}</button><button id="card-view" aria-label="Card view">${icon("grid")}</button></div></div><div id="results"></div>`;
  disposeTaskFilters = initTaskFilters({
    media: mobileMedia,
    trigger: $("#filter-toggle"),
    controls: $("#task-filters"),
  });
  const q = new URLSearchParams(location.search);
  if (q.get("course")) $("#course-filter").value = q.get("course");
  const updateFilterLabel = () => {
    const count = [
      "course-filter",
      "status-filter",
      "priority-filter",
      "deadline-filter",
    ].filter((id) => $("#" + id).value).length;
    $("#filter-label").textContent =
      "Filters & sort" + (count ? ` (${count})` : "");
  };
  updateFilterLabel();
  const load = () => {
    updateFilterLabel();
    return loadTasks(deadlines).catch(fail);
  };
  [
    "course-filter",
    "status-filter",
    "priority-filter",
    "deadline-filter",
    "sort",
  ].forEach((id) => ($("#" + id).onchange = load));
  $("#search").oninput = () => {
    clearTimeout(tasksPage.timer);
    tasksPage.timer = setTimeout(load, 220);
  };
  $("#list-view").onclick = () => {
    view = "list";
    paintTasks();
  };
  $("#card-view").onclick = () => {
    view = "cards";
    paintTasks();
  };
  await loadTasks(deadlines);
}
let searchSeq = 0;
async function loadTasks(deadlines) {
  const seq = ++searchSeq;
  const p = new URLSearchParams({
    q: $("#search").value,
    course_id: $("#course-filter").value,
    status: $("#status-filter").value,
    priority: $("#priority-filter").value,
    deadline: $("#deadline-filter").value,
    sort: $("#sort").value,
  });
  const data = await api("/tasks?" + p);
  if (seq !== searchSeq) return;
  items = deadlines ? data.filter((t) => t.deadline) : data;
  paintTasks();
}
function paintTasks() {
  $("#list-view").classList.toggle("active", view === "list");
  $("#list-view").setAttribute("aria-pressed", String(view === "list"));
  $("#card-view").setAttribute("aria-pressed", String(view === "cards"));
  $("#card-view").classList.toggle("active", view === "cards");
  if (!items.length) {
    $("#results").innerHTML =
      `<section class="panel">${empty("A fresh page", "No tasks match this view. Add something to work toward.", btn("new-task", "Create a task", null, "primary", "plus"))}</section>`;
    return;
  }
  const actions = (t) =>
    `<div class="actions">${ib("task-edit", "Edit task", t.id, "edit")}${ib("task-delete", "Delete task", t.id, "trash")}</div>`;
  const check = (t) =>
    `<button class="check-button ${t.status === "completed" ? "completed" : ""}" data-action="complete" data-id="${t.id}" aria-label="${t.status === "completed" ? "Reopen" : "Complete"} task">${t.status === "completed" ? "✓" : ""}</button>`;
  if (view === "cards")
    $("#results").innerHTML =
      `<div class="card-grid">${items.map((t) => `<article class="task-card"><div class="inline-actions">${pill(t.priority)}${pill(t.status)}${t.overdue ? pill("overdue") : ""}</div><button class="task-title" data-action="task-details" data-id="${t.id}">${e(t.title)}</button><div class="task-meta">${meta(t)}</div><p class="muted" style="font-size:.8rem;margin:13px 0">${e(t.description.slice(0, 120)) || "Give this task a little context."}</p><div class="task-meta">${icon("clock")} ${e(dt(t.deadline))} · ${e(t.estimated_hours ?? "?")}h</div><div class="task-card-bottom">${btn("complete", t.status === "completed" ? "Reopen" : "Complete", t.id, "secondary", "check")}${actions(t)}</div></article>`).join("")}</div>`;
  else
    $("#results").innerHTML =
      `<section class="panel table-wrap task-table"><table role="table" aria-label="Academic tasks"><thead role="rowgroup"><tr role="row"><th scope="col" role="columnheader">Task</th><th scope="col" role="columnheader">Course</th><th scope="col" role="columnheader">Deadline</th><th scope="col" role="columnheader">Priority</th><th scope="col" role="columnheader">Status</th><th scope="col" role="columnheader">Effort</th><th scope="col" role="columnheader">Actions</th></tr></thead><tbody role="rowgroup">${items.map((t) => `<tr role="row"><td role="cell" data-label="Task"><div class="table-title">${check(t)}<button class="task-title" data-action="task-details" data-id="${t.id}">${e(t.title)}</button></div></td><td role="cell" data-label="Course">${meta(t)}</td><td role="cell" data-label="Deadline"><span class="${t.overdue ? "form-error" : ""}">${e(dt(t.deadline))}</span><div class="task-meta">${e(relative(t.deadline))}</div></td><td role="cell" data-label="Priority">${pill(t.priority)}</td><td role="cell" data-label="Status">${pill(t.status)}</td><td role="cell" data-label="Effort">${e(t.estimated_hours ?? "?")}h</td><td role="cell" data-label="Actions">${actions(t)}</td></tr>`).join("")}</tbody></table></section>`;
}
async function coursesPage() {
  courses = await api("/courses");
  $("#content").innerHTML =
    heading(
      "Your semester, organized.",
      "A home for every course and everything that comes with it.",
      btn("new-course", "Add course", null, "primary", "plus"),
      "THE BIGGER PICTURE",
    ) +
    (courses.length
      ? `<div class="card-grid">${courses.map((c) => `<article class="course-card"><div class="course-header"><div class="course-icon" style="color:${e(c.color)}">${icon("book")}</div><div class="actions">${ib("course-edit", "Edit course", c.id, "edit")}${ib("course-delete", "Delete course", c.id, "trash")}</div></div><span class="course-code">${e(c.code)} ${c.semester ? "· " + e(c.semester) : ""}</span><h2><button class="task-title" data-action="course-details" data-id="${c.id}">${e(c.name)}</button></h2><p>${e(c.description) || "Space for your next chapter of learning."}</p><div class="course-progress"><span style="width:${c.task_count ? (c.completed_count / c.task_count) * 100 : 0}%;background:${e(c.color)}"></span></div><div class="course-meta"><span>${c.completed_count} of ${c.task_count} completed</span><span>${c.pending_count} pending</span></div><div class="course-footer"><span>${c.next_deadline ? "Next: " + e(date(c.next_deadline)) : "No upcoming deadline"}</span><a href="/tasks?course=${c.id}">View tasks</a></div></article>`).join("")}</div>`
      : `<section class="panel">${empty("Build your academic home", "Add the courses you’re taking this semester.", btn("new-course", "Add your first course", null, "primary", "plus"))}</section>`);
}
const field = (
  name,
  label,
  value = "",
  type = "text",
  required = false,
  extra = "",
) =>
  `<label>${e(label)}<input name="${name}" type="${type}" value="${e(value)}" ${required ? "required" : ""} ${extra}></label>`;
const select = (name, label, options, value) =>
  `<label>${e(label)}<select name="${name}">${options.map(([v, t]) => `<option value="${e(v)}" ${String(v) === String(value) ? "selected" : ""}>${e(t)}</option>`).join("")}</select></label>`;
function editor(title, fields, submit, button = "Save changes") {
  $("#editor-title").textContent = title;
  $("#editor-fields").innerHTML = fields;
  $("#editor-error").textContent = "";
  $('#editor-form button[type="submit"]').textContent = button;
  $("#editor-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const b = $('#editor-form button[type="submit"]');
    b.disabled = true;
    $("#editor-error").textContent = "";
    try {
      await submit(new FormData(ev.target));
      $("#editor").close();
      await render();
      await badge();
    } catch (err) {
      $("#editor-error").textContent = err.message;
    } finally {
      b.disabled = false;
    }
  };
  $("#editor").showModal();
}
async function taskEditor(id) {
  const t = id
    ? await api("/tasks/" + id)
    : { priority: "medium", status: "pending", task_type: "assignment" };
  editor(
    id ? "Edit your task" : "Make a little plan",
    field("title", "Task title", t.title, "text", true, 'maxlength="200"') +
      `<label>Description<textarea name="description" maxlength="10000">${e(t.description)}</textarea></label><div class="field-grid">` +
      select(
        "course_id",
        "Course",
        [["", "Independent study"], ...courses.map((c) => [c.id, c.name])],
        t.course_id,
      ) +
      select(
        "task_type",
        "Task type",
        [
          ["assignment", "Assignment"],
          ["project", "Project"],
          ["study_session", "Study session"],
          ["exam_preparation", "Exam preparation"],
          ["reading", "Reading"],
          ["other", "Other academic activity"],
        ],
        t.task_type,
      ) +
      select(
        "priority",
        "Importance",
        [
          ["low", "Low"],
          ["medium", "Medium"],
          ["high", "High"],
        ],
        t.priority,
      ) +
      select(
        "status",
        "Status",
        [
          ["pending", "Pending"],
          ["in_progress", "In progress"],
          ["completed", "Completed"],
        ],
        t.status,
      ) +
      field(
        "deadline",
        "Deadline (device time)",
        inputDate(t.deadline),
        "datetime-local",
      ) +
      field(
        "estimated_hours",
        "Estimated hours",
        t.estimated_hours ?? "",
        "number",
        false,
        'min="0.017" max="1000" step="any"',
      ) +
      '</div><p class="help">Without an estimate, the planner assumes 1 hour. Add your best estimate for a realistic plan.</p>',
    async (f) => {
      const d = Object.fromEntries(f);
      d.course_id = d.course_id ? Number(d.course_id) : null;
      d.estimated_hours = d.estimated_hours ? Number(d.estimated_hours) : null;
      d.deadline = d.deadline ? new Date(d.deadline).toISOString() : null;
      await api("/tasks" + (id ? "/" + id : ""), id ? "PATCH" : "POST", d);
      toast("Task saved to your workspace.");
    },
    id ? "Save task" : "Create task",
  );
}
async function taskDetails(id) {
  const t = await api("/tasks/" + id);
  editor(
    t.title,
    `<div class="inline-actions">${pill(t.status)}${pill(t.priority)}${t.overdue ? pill("overdue") : ""}</div><p style="margin-top:20px;white-space:pre-wrap">${e(t.description) || "No description added."}</p><div class="progress-detail"><div><span>Course</span><strong>${e(t.course_name)}</strong></div><div><span>Deadline</span><strong>${e(dt(t.deadline))}</strong></div><div><span>Estimated effort</span><strong>${e(t.estimated_hours ?? "Not estimated")} ${t.estimated_hours ? "hours" : ""}</strong></div><div><span>Completed</span><strong>${e(t.completed_at ? dt(t.completed_at) : "Not yet")}</strong></div></div><div class="inline-actions">${btn("task-edit", "Edit task", id, "secondary", "edit")}${btn("session-new", "Schedule time", id, "secondary", "calendar")}${btn("complete", t.status === "completed" ? "Reopen task" : "Mark completed", id, "secondary", "check")}</div>`,
    async () => {},
    "Done",
  );
}
async function courseEditor(id) {
  const c = id ? await api("/courses/" + id) : { color: "#5366de" };
  editor(
    id ? "Edit course" : "Add a new course",
    field("name", "Course name", c.name, "text", true, 'maxlength="160"') +
      '<div class="field-grid">' +
      field("code", "Course code", c.code, "text", true, 'maxlength="40"') +
      field(
        "semester",
        "Semester / term",
        c.semester,
        "text",
        false,
        'maxlength="80"',
      ) +
      "</div>" +
      field(
        "instructor",
        "Instructor (optional)",
        c.instructor,
        "text",
        false,
        'maxlength="120"',
      ) +
      `<label>Description<textarea name="description" maxlength="5000">${e(c.description)}</textarea></label>` +
      field("color", "Course color", c.color, "color"),
    async (f) => {
      await api(
        "/courses" + (id ? "/" + id : ""),
        id ? "PATCH" : "POST",
        Object.fromEntries(f),
      );
      courses = await api("/courses");
      toast("Course saved.");
    },
    id ? "Save course" : "Create course",
  );
}
async function courseDetails(id) {
  const c = await api("/courses/" + id);
  editor(
    c.name,
    `<p class="muted">${e(c.code)} · ${e(c.semester)}</p><p style="white-space:pre-wrap">${e(c.description) || "No description yet."}</p><p>Instructor: ${e(c.instructor) || "Not specified"}</p><p>${c.pending_count} pending tasks · ${c.completed_count} completed</p><div class="inline-actions"><a class="secondary" href="/tasks?course=${c.id}">View course tasks</a>${btn("course-edit", "Edit course", c.id, "secondary", "edit")}</div>`,
    async () => {},
    "Done",
  );
}
async function sessionEditor(id, taskId) {
  const s = id ? await api("/schedules/" + id) : {},
    tasks = (await api("/tasks")).filter(
      (t) => t.status !== "completed" || t.id === s.task_id,
    );
  if (!tasks.length) {
    toast("Create or reopen a task before scheduling.", true);
    return;
  }
  editor(
    id ? "Your study session" : "Make time to focus",
    select(
      "task_id",
      "Task",
      tasks.map((t) => [t.id, t.title]),
      s.task_id || taskId,
    ) +
      field(
        "start",
        "Starts (device time)",
        inputDate(s.start),
        "datetime-local",
        true,
      ) +
      field(
        "end",
        "Ends (device time)",
        inputDate(s.end),
        "datetime-local",
        true,
      ) +
      `<p class="help">Availability is checked in ${e(prefs.timezone)}. Sessions must fit study hours, estimated effort, and deadlines.</p>${id ? btn("session-delete", "Remove this session", id, "quiet", "trash") : ""}`,
    async (f) => {
      await api("/schedules" + (id ? "/" + id : ""), id ? "PATCH" : "POST", {
        task_id: Number(f.get("task_id")),
        start: new Date(f.get("start")).toISOString(),
        end: new Date(f.get("end")).toISOString(),
      });
      toast("Study session saved.");
    },
    id ? "Save session" : "Schedule session",
  );
}
async function badge() {
  const d = await api("/notifications");
  $("#nav-unread").textContent = d.unread;
  $("#nav-unread").hidden = !d.unread;
  $("#top-unread").hidden = !d.unread;
}
async function dashboard() {
  const d = await api("/dashboard/summary"),
    w = d.workload,
    g =
      new Date().getHours() < 12
        ? "Good morning"
        : new Date().getHours() < 17
          ? "Good afternoon"
          : "Good evening";
  const stat = (l, v, n, i, c = "") =>
    `<div class="stat"><div class="stat-head">${l}<span class="stat-icon ${c}">${icon(i)}</span></div><div class="stat-value">${v}</div><div class="stat-note">${n}</div></div>`;
  const rec = d.recommendations
    .map(
      (v) =>
        `<div class="recommendation"><div class="recommendation-top"><button class="task-title" data-action="task-details" data-id="${v.task.id}">${e(v.task.title)}</button><span class="score">${v.score} / 100</span></div><p>${e(v.reason)}</p>${v.at_risk ? '<p class="form-error">At risk: effort exceeds time remaining.</p>' : ""}</div>`,
    )
    .join("");
  const deadlines = d.deadlines
    .map(
      (t) =>
        `<div class="deadline-item"><div class="date-tile"><small>${e(date(t.deadline, { month: "short", day: undefined }))}</small><strong>${e(date(t.deadline, { month: undefined, day: "numeric" }))}</strong></div><div class="task-info"><button class="task-title" data-action="task-details" data-id="${t.id}">${e(t.title)}</button><div class="task-meta">${meta(t)}</div></div><span class="date-relative">${e(relative(t.deadline))}</span></div>`,
    )
    .join("");
  $("#content").innerHTML =
    heading(
      `${g}, ${user.full_name.split(" ")[0]}.`,
      "A clear mind starts with a clear plan. Here’s where you stand.",
      `${btn("new-course", "Add course", null, "secondary", "book")}<a class="secondary" href="/calendar">${icon("calendar")} My calendar</a>${btn("new-task", "Add task", null, "primary", "plus")}`,
    ) +
    `<div class="welcome-strip"><span class="strip-icon">${icon("spark")}</span><div><h3>${d.recommendations.length ? "A little focus goes a long way." : "Your next chapter starts here."}</h3><p>${d.recommendations.length ? `Start with ${e(d.recommendations[0].task.title)}. One thoughtful step at a time.` : "Add a course and your first task. We’ll help you find your rhythm."}</p></div><a href="/planner">Find your focus</a></div><div class="stats">${stat("Total tasks", d.total, `${d.pending} still in progress`, "check")}${stat("Completed", d.completed, `${d.completion_percent}% of your tasks`, "check", "green")}${stat("Overdue tasks", d.overdue, d.overdue ? "Let’s make a plan to catch up" : "You’re staying on track", "clock", "red")}${stat("Work remaining", `${w.remaining_hours}<small> hrs</small>`, `${w.missing_estimates} tasks without an estimate`, "chart", "orange")}</div>` +
    `<div class="columns"><div class="stack">${panel("Your week, in focus", "A balanced workload leaves room to breathe.", '<div class="panel-body"><div class="chart-wrap"><canvas id="week-chart" role="img" aria-label="Weekly workload"></canvas></div>' + legend + "</div>", '<a href="/planner">Open planner</a>')}${panel("Today’s study plan", `${d.today.length} sessions on your calendar`, d.today.length ? d.today.map((s) => `<div class="task-row"><span class="stat-icon">${icon("clock")}</span><div class="task-info"><button class="task-title" data-action="session-edit" data-id="${s.id}">${e(s.title)}</button><div class="task-meta">${e(tm(s.start))} – ${e(tm(s.end))}</div></div>${btn("session-edit", "Details", s.id)}</div>`).join("") : empty("A little breathing room", "No study sessions planned for today.", '<a class="secondary" href="/planner">Build a study plan</a>'), '<a href="/calendar">View calendar</a>')}${panel("Your progress", "Small steps add up.", `<div class="panel-body"><div class="progress-row"><div class="progress-visual"><canvas id="progress-chart" role="img" aria-label="Task completion"></canvas><div class="progress-number">${d.completion_percent}%<small>completed</small></div></div><div class="progress-detail"><div><span>Completed</span><strong>${d.completed}</strong></div><div><span>Remaining</span><strong>${d.pending}</strong></div><div><span>Upcoming deadlines</span><strong>${d.upcoming_count}</strong></div></div></div></div>`)}</div><div class="stack">${panel("Focus on what matters", "Your priorities, with a little perspective.", rec || empty("Make space for what’s next", "Recommendations appear when you add tasks.", btn("new-task", "Add your first task", null, "secondary")), '<a href="/tasks">All tasks</a>')}${d.recommendations.length ? '<p class="section-note">Ranked by deadline, importance, and effort. Rule-based recommendations you can understand.</p>' : ""}${panel("Coming up next", "Keep the important dates in sight.", deadlines || empty("No upcoming deadlines", "A clear horizon. Add deadlines as your semester takes shape."), '<a href="/deadlines">View all</a>')}${panel("Keep it balanced", "Your weekly snapshot.", `<div class="panel-body"><div class="progress-detail"><div><span>Planned this week</span><strong>${w.weekly_hours}h</strong></div><div><span>Available this week</span><strong>${w.weekly_capacity}h</strong></div><div><span>Overloaded days</span><strong>${w.overloaded_days.length}</strong></div></div><a class="secondary full" href="/settings">Adjust study preferences</a></div>`)}</div></div>`;
  bar("#week-chart", w.daily);
  if (globalThis.Chart)
    charts.push(
      new Chart($("#progress-chart"), {
        type: "doughnut",
        data: {
          datasets: [
            {
              data: [d.completed, d.pending || (!d.completed ? 1 : 0)],
              backgroundColor: ["#6b7ee2", "#edf0f8"],
              borderWidth: 0,
            },
          ],
        },
        options: {
          cutout: "82%",
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
        },
      }),
    );
}
