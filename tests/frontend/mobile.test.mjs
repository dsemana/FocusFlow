// Unit tests for responsive behavior. These do not render a browser or prove layout.
// Run with: node --test tests/frontend/mobile.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(
  new URL("../../app/static/js/responsive.js", import.meta.url),
  "utf8",
);
const { initNavigation, initTaskFilters, initViewport, calendarLayout } =
  await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );

class Element extends EventTarget {
  constructor(doc, parent = null) {
    super();
    this.doc = doc;
    this.parent = parent;
    this.inert = false;
    this.attributes = new Map();
    this.children = [];
    this.hidden = false;
    this.classes = new Set();
    this.classList = {
      toggle: (name, value) =>
        value ? this.classes.add(name) : this.classes.delete(name),
    };
    if (parent) parent.children.push(this);
  }
  setAttribute(name, value) {
    this.attributes.set(name, value);
  }
  removeAttribute(name) {
    this.attributes.delete(name);
  }
  getAttribute(name) {
    return this.attributes.get(name);
  }
  contains(node) {
    return node === this || this.children.some((child) => child.contains(node));
  }
  focus() {
    let node = this;
    while (node) {
      if (node.inert) return;
      node = node.parent;
    }
    this.doc.activeElement = this;
  }
  querySelectorAll() {
    return this.children;
  }
  querySelector() {
    return this.children.find((child) => child.active);
  }
  click() {
    this.dispatchEvent(new Event("click"));
  }
}
class Media extends EventTarget {
  constructor(matches) {
    super();
    this.matches = matches;
  }
  change(matches) {
    this.matches = matches;
    this.dispatchEvent(new Event("change"));
  }
}
function navigation(mobile = true) {
  const doc = new EventTarget();
  doc.body = new Element(doc);
  const media = new Media(mobile),
    sidebar = new Element(doc, doc.body),
    shell = new Element(doc, doc.body);
  const trigger = new Element(doc, shell),
    close = new Element(doc, sidebar);
  const first = new Element(doc, sidebar),
    last = new Element(doc, sidebar),
    backdrop = new Element(doc, doc.body);
  first.active = true;
  trigger.focus();
  initNavigation({ doc, media, sidebar, shell, trigger, close, backdrop });
  return { doc, media, sidebar, shell, trigger, close, first, last, backdrop };
}
function key(doc, value, shift = false) {
  const event = new Event("keydown", { cancelable: true });
  Object.assign(event, { key: value, shiftKey: shift });
  doc.dispatchEvent(event);
  return event;
}

test("closed phone drawer cannot receive focus; opening isolates the background", () => {
  const n = navigation();
  n.first.focus();
  assert.equal(n.doc.activeElement, n.trigger);
  n.trigger.click();
  assert.equal(n.doc.activeElement, n.close);
  assert.equal(n.shell.inert, true);
  assert.equal(n.sidebar.inert, false);
  assert.equal(n.backdrop.hidden, false);
  assert.equal(n.trigger.getAttribute("aria-expanded"), "true");
});
for (const method of ["close", "backdrop", "Escape"]) {
  test(`${method} closes navigation and restores focus to the menu button`, () => {
    const n = navigation();
    n.trigger.click();
    if (method === "Escape") key(n.doc, "Escape");
    else n[method].click();
    assert.equal(n.doc.activeElement, n.trigger);
    assert.equal(n.shell.inert, false);
    assert.equal(n.sidebar.inert, true);
    assert.equal(n.backdrop.hidden, true);
    assert.equal(n.trigger.getAttribute("aria-expanded"), "false");
  });
}
test("Tab and Shift+Tab wrap within the opened drawer", () => {
  const n = navigation();
  n.trigger.click();
  n.last.focus();
  assert.equal(key(n.doc, "Tab").defaultPrevented, true);
  assert.equal(n.doc.activeElement, n.close);
  assert.equal(key(n.doc, "Tab", true).defaultPrevented, true);
  assert.equal(n.doc.activeElement, n.last);
});
test("rotation to desktop clears modal state and restores ordinary navigation", () => {
  const n = navigation();
  n.trigger.click();
  n.media.change(false);
  assert.equal(n.shell.inert, false);
  assert.equal(n.sidebar.inert, false);
  assert.equal(n.backdrop.hidden, true);
  assert.equal(n.sidebar.getAttribute("role"), undefined);
  assert.equal(n.doc.body.classes.has("navigation-open"), false);
  n.first.focus();
  assert.equal(n.doc.activeElement, n.first);
  n.media.change(true);
  assert.equal(n.sidebar.inert, true);
  n.trigger.focus();
  n.media.change(false);
  assert.equal(n.doc.activeElement, n.first);
});
test("desktop navigation stays available and does not open a mobile modal", () => {
  const n = navigation(false);
  n.trigger.click();
  assert.equal(n.sidebar.inert, false);
  assert.equal(n.shell.inert, false);
  assert.equal(n.backdrop.hidden, true);
});
test("phone filters toggle, remain visible on desktop, and dispose resize listeners", () => {
  const doc = {},
    media = new Media(true),
    trigger = new Element(doc),
    controls = new Element(doc);
  const dispose = initTaskFilters({ media, trigger, controls });
  assert.equal(controls.hidden, true);
  assert.equal(trigger.hidden, false);
  trigger.click();
  assert.equal(controls.hidden, false);
  trigger.click();
  assert.equal(controls.hidden, true);
  media.change(false);
  assert.equal(controls.hidden, false);
  assert.equal(trigger.hidden, true);
  media.change(true);
  assert.equal(controls.hidden, true);
  assert.equal(trigger.hidden, false);
  dispose();
  media.change(false);
  assert.equal(controls.hidden, true);
});
test("phone calendar starts in agenda with compact controls; desktop retains every view", () => {
  assert.equal(calendarLayout(true).initialView, "listWeek");
  assert.equal(calendarLayout(true).headerToolbar.left, "prev,next today");
  assert.equal(calendarLayout(false).initialView, "dayGridMonth");
  assert.match(
    calendarLayout(false).headerToolbar.right,
    /timeGridWeek,timeGridDay/,
  );
});
test("keyboard viewport changes reserve visible height without suppressing pinch zoom", () => {
  const values = new Map(),
    doc = {
      documentElement: { style: { setProperty: (k, v) => values.set(k, v) } },
    };
  const viewport = new EventTarget();
  Object.assign(viewport, { height: 800, offsetTop: 0, scale: 1 });
  const win = { innerHeight: 800, visualViewport: viewport };
  initViewport(win, doc);
  assert.equal(values.get("--keyboard-offset"), "0px");
  viewport.height = 480;
  viewport.dispatchEvent(new Event("resize"));
  assert.equal(values.get("--viewport-height"), "480px");
  assert.equal(values.get("--keyboard-offset"), "320px");
  viewport.scale = 2;
  viewport.dispatchEvent(new Event("resize"));
  assert.equal(values.get("--keyboard-offset"), "0px");
  assert.equal(values.get("--viewport-height"), "800px");
});
