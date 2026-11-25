// Shared breakpoint and mobile controls. No runtime dependencies.
export const MOBILE_QUERY = "(max-width: 760px)";

export function calendarLayout(mobile) {
  return {
    initialView: mobile ? "listWeek" : "dayGridMonth",
    headerToolbar: mobile
      ? { left: "prev,next today", center: "", right: "title" }
      : {
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
        },
  };
}

export function initNavigation({
  doc = document,
  media,
  sidebar,
  shell,
  trigger,
  close,
  backdrop,
}) {
  let opened = false;
  const focusable = () => [
    ...sidebar.querySelectorAll("a[href], button:not([disabled])"),
  ];

  function setOpen(value, restoreFocus = true) {
    opened = Boolean(value && media.matches);
    if (!opened) shell.inert = false;
    if (!media.matches) sidebar.inert = false;
    // Move focus before making its previous container inert.
    if (
      !opened &&
      restoreFocus &&
      (sidebar.contains(doc.activeElement) ||
        (!media.matches && doc.activeElement === trigger))
    ) {
      if (media.matches) trigger.focus();
      else sidebar.querySelector(".active")?.focus();
    }
    sidebar.inert = media.matches && !opened;
    shell.inert = opened;
    sidebar.classList.toggle("open", opened);
    trigger.setAttribute("aria-expanded", String(opened));
    backdrop.hidden = !opened;
    doc.body.classList.toggle("navigation-open", opened);
    if (opened) {
      sidebar.setAttribute("role", "dialog");
      sidebar.setAttribute("aria-modal", "true");
      sidebar.setAttribute("aria-label", "Main navigation");
      close.focus();
    } else {
      sidebar.removeAttribute("role");
      sidebar.removeAttribute("aria-modal");
      sidebar.removeAttribute("aria-label");
    }
  }
  trigger.addEventListener("click", () => setOpen(!opened));
  close.addEventListener("click", () => setOpen(false));
  backdrop.addEventListener("click", () => setOpen(false));
  sidebar.addEventListener("click", (event) => {
    if (event.target.closest("a[href]")) setOpen(false);
  });
  doc.addEventListener("keydown", (event) => {
    if (!opened) return;
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
    } else if (event.key === "Tab") {
      const nodes = focusable();
      const first = nodes[0],
        last = nodes[nodes.length - 1];
      if (
        event.shiftKey &&
        (doc.activeElement === first || !sidebar.contains(doc.activeElement))
      ) {
        event.preventDefault();
        last?.focus();
      } else if (
        !event.shiftKey &&
        (doc.activeElement === last || !sidebar.contains(doc.activeElement))
      ) {
        event.preventDefault();
        first?.focus();
      }
    }
  });
  media.addEventListener("change", () => setOpen(false));
  setOpen(false, false);
  return { close: () => setOpen(false) };
}

export function initViewport(win = window, doc = document) {
  const viewport = win.visualViewport;
  if (!viewport) return;
  const update = () => {
    const unzoomed = viewport.scale === 1;
    doc.documentElement.style.setProperty(
      "--viewport-height",
      `${Math.round(unzoomed ? viewport.height : win.innerHeight)}px`,
    );
    doc.documentElement.style.setProperty(
      "--keyboard-offset",
      `${unzoomed ? Math.max(0, win.innerHeight - viewport.height - viewport.offsetTop) : 0}px`,
    );
  };
  viewport.addEventListener("resize", update);
  viewport.addEventListener("scroll", update);
  update();
}

export function initTaskFilters({ media, trigger, controls }) {
  function setExpanded(expanded) {
    controls.hidden = media.matches && !expanded;
    trigger.hidden = !media.matches;
    trigger.setAttribute("aria-expanded", String(!controls.hidden));
  }
  const toggle = () => setExpanded(controls.hidden);
  const change = () => setExpanded(false);
  trigger.addEventListener("click", toggle);
  media.addEventListener("change", change);
  change();
  return () => {
    trigger.removeEventListener("click", toggle);
    media.removeEventListener("change", change);
  };
}
