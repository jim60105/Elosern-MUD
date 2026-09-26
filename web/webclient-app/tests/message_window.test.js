// webclient-message-window-component (tasks 4.3): the AVG message window's
// reader state, reading controls, and live region (the dialogue mode's
// window is covered by message_window_dialogue.test.js). jsdom has no layout, so every test injects a deterministic
// code-point `pageFit` (the documented test seam) and stubs
// ResizeObserver / document.fonts where a case needs them.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import MessageWindow from "../components/MessageWindow.vue";

// A page holds `budget.value` code points (fragment end − start summed).
function codePointFit(budget) {
  return (fragments) =>
    fragments.reduce((sum, fragment) => sum + (fragment.end - fragment.start), 0) <= budget.value;
}

function seqLines(start, entries) {
  return entries.map(([kind, text], index) => ({ kind, text, seq: start + index }));
}

const ARRIVAL = seqLines(1, [["out", "渡口的霧。"]]);
// 30 code points, sentence ends every 10: three pages at a budget of 10.
const LONG = "一二三四五六七八九。甲乙丙丁戊己庚辛壬。天地玄黃宇宙洪荒日。";

async function settle() {
  await nextTick();
  await nextTick();
  await nextTick();
}

const pageSurface = (w) => w.get('[data-testid="message-page"]');
const marker = (w) => w.find('[data-testid="message-page-marker"]');
const live = (w) => w.get('[data-testid="message-live"]').text();

describe("MessageWindow paged presentation", () => {
  let wrapper;
  let budget;

  beforeEach(() => {
    budget = { value: 10 };
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
    vi.unstubAllGlobals();
  });

  async function mountWindow(props = {}) {
    wrapper = mount(MessageWindow, {
      attachTo: document.body,
      // C7: instant pages keep these C6b cases about paging, not typing.
      props: { lines: ARRIVAL, marks: [], pageFit: codePointFit(budget), textSpeed: "instant", ...props },
    });
    await settle();
    return wrapper;
  }

  // Mounted on an earlier response, then a long response arrives: page 1.
  async function mountThenArrive(extra = []) {
    const w = await mountWindow();
    await w.setProps({
      lines: [...ARRIVAL, ...seqLines(2, [["in", "look"], ["out", LONG], ...extra])],
    });
    await settle();
    return w;
  }

  it("mounts on the last page of the last response, fully read, and announces nothing", async () => {
    const w = await mountWindow({
      lines: [...ARRIVAL, ...seqLines(2, [["in", "look"], ["out", LONG]])],
    });
    expect(pageSurface(w).attributes("data-pages")).toBe("3");
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    expect(pageSurface(w).text()).toBe("天地玄黃宇宙洪荒日。");
    expect(marker(w).text()).toBe("■");
    expect(marker(w).attributes("aria-hidden")).toBe("true");
    expect(live(w)).toBe("");
  });

  it("shows ■ on a single-page response", async () => {
    const w = await mountWindow();
    expect(pageSurface(w).text()).toBe("渡口的霧。");
    expect(marker(w).text()).toBe("■");
    expect(marker(w).attributes("data-state")).toBe("end");
  });

  it("opens a new response on page 1 with ▼ and announces that page once", async () => {
    const w = await mountThenArrive();
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(pageSurface(w).text()).toBe("一二三四五六七八九。");
    expect(marker(w).text()).toBe("▼");
    expect(marker(w).attributes("data-state")).toBe("more");
    expect(live(w)).toBe("一二三四五六七八九。");
    // The in line heads the response and is never paged.
    expect(pageSurface(w).text()).not.toContain("look");
    expect(w.get(".message-window__sr").text()).toBe("第 1／3 頁");
  });

  it("advances on a click and reaches ■ on the last page", async () => {
    const w = await mountThenArrive();
    await w.get('[data-testid="message-window"]').trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    expect(live(w)).toBe("甲乙丙丁戊己庚辛壬。");
    expect(document.activeElement).toBe(pageSurface(w).element);
    await w.get('[data-testid="message-window"]').trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    expect(marker(w).text()).toBe("■");
    // A click on the last page is a no-op.
    await w.get('[data-testid="message-window"]').trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("3");
  });

  it("does not advance on a click that lands on a button", async () => {
    const w = await mountThenArrive();
    const button = document.createElement("button");
    w.get(".message-window__controls").element.appendChild(button);
    button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await nextTick();
    expect(pageSurface(w).attributes("data-page")).toBe("1");
  });

  it("does not advance while text is selected inside the window", async () => {
    const w = await mountThenArrive();
    const range = document.createRange();
    range.selectNodeContents(pageSurface(w).element);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    await w.get('[data-testid="message-window"]').trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    selection.removeAllRanges();
  });

  it("advances on Enter and Space on the surface without reaching the document", async () => {
    const w = await mountThenArrive();
    const documentSpy = vi.fn();
    document.addEventListener("keydown", documentSpy);
    try {
      await pageSurface(w).trigger("keydown", { key: "Enter" });
      expect(pageSurface(w).attributes("data-page")).toBe("2");
      await pageSurface(w).trigger("keydown", { key: " " });
      expect(pageSurface(w).attributes("data-page")).toBe("3");
      expect(documentSpy).not.toHaveBeenCalled();
    } finally {
      document.removeEventListener("keydown", documentSpy);
    }
  });

  it("ignores key repeat but still keeps the key from the document", async () => {
    const w = await mountThenArrive();
    const documentSpy = vi.fn();
    document.addEventListener("keydown", documentSpy);
    try {
      await pageSurface(w).trigger("keydown", { key: "Enter", repeat: true });
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      expect(documentSpy).not.toHaveBeenCalled();
    } finally {
      document.removeEventListener("keydown", documentSpy);
    }
  });

  it("leaves Enter alone when focus is outside the surface", async () => {
    const w = await mountThenArrive();
    const outside = document.createElement("div");
    outside.tabIndex = 0;
    document.body.appendChild(outside);
    const documentSpy = vi.fn();
    document.addEventListener("keydown", documentSpy);
    try {
      outside.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      // A key on a child of the window that is not the surface is not claimed either.
      w.get(".message-window__controls").element.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
      );
      await nextTick();
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      expect(documentSpy).toHaveBeenCalledTimes(2);
    } finally {
      document.removeEventListener("keydown", documentSpy);
    }
  });

  it("flushes to the previous response's last page while a mark awaits its first line", async () => {
    const w = await mountThenArrive();
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    // A silent action is out: its mark (seq 5) has no line yet.
    await w.setProps({ marks: [5] });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    expect(marker(w).text()).toBe("■");
    // Its first reply line opens the new response on page 1.
    await w.setProps({
      lines: [...w.props("lines"), ...seqLines(5, [["out", "門開了。"]])],
    });
    await settle();
    expect(pageSurface(w).text()).toBe("門開了。");
    expect(live(w)).toBe("門開了。");
  });

  it("flushes when an echo line arrives before any reply line", async () => {
    const w = await mountThenArrive();
    const lines = [...w.props("lines"), ...seqLines(5, [["in", "wait"]])];
    await w.setProps({ lines, marks: [5] });
    await settle();
    // The header-only response never blanks the window.
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    expect(pageSurface(w).text()).toBe("天地玄黃宇宙洪荒日。");
    await w.setProps({ lines: [...lines, ...seqLines(6, [["out", "時間流逝。"]])] });
    await settle();
    expect(pageSurface(w).text()).toBe("時間流逝。");
    expect(pageSurface(w).attributes("data-page")).toBe("1");
  });

  it("keeps the page when lines are appended to the current response and announces only them", async () => {
    const w = await mountThenArrive();
    expect(pageSurface(w).attributes("data-pages")).toBe("3");
    await w.setProps({
      lines: [...w.props("lines"), ...seqLines(4, [["out", "尾聲。"]])],
    });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(pageSurface(w).attributes("data-pages")).toBe("4");
    expect(marker(w).text()).toBe("▼");
    // Nothing new landed on page 1, so nothing new was announced.
    expect(live(w)).toBe("一二三四五六七八九。");
  });

  it("announces an appended line that lands on the page on screen", async () => {
    budget.value = 20;
    const w = await mountWindow();
    await w.setProps({ lines: [...ARRIVAL, ...seqLines(2, [["in", "look"], ["out", "風起。"]])] });
    await settle();
    expect(live(w)).toBe("風起。");
    await w.setProps({ lines: [...w.props("lines"), ...seqLines(4, [["out", "雨落。"]])] });
    await settle();
    expect(pageSurface(w).text()).toContain("雨落。");
    expect(live(w)).toBe("雨落。");
  });

  it("settles on the last page, silently, when a trim cuts into the shown response", async () => {
    const lead = seqLines(1, [["out", LONG], ["out", "尾聲。"]]);
    const w = await mountWindow({ lines: lead });
    await w.get('[data-testid="message-window"]').trigger("click");
    // Nothing moved yet: the reader is on the last page after mount.
    expect(pageSurface(w).attributes("data-page")).toBe("4");
    const spoken = live(w);
    // The log trims its oldest line: the leading response loses its head.
    await w.setProps({ lines: lead.slice(1) });
    await settle();
    expect(pageSurface(w).attributes("data-pages")).toBe("1");
    expect(pageSurface(w).text()).toBe("尾聲。");
    expect(live(w)).toBe(spoken);
  });

  it("re-pages on a fontScale change to the page holding the anchor, announcing nothing", async () => {
    const w = await mountThenArrive();
    await w.get('[data-testid="message-window"]').trigger("click");
    expect(pageSurface(w).text()).toBe("甲乙丙丁戊己庚辛壬。");
    const spoken = live(w);
    // Larger text: five code points per page. The anchor of a fully shown
    // page is its last character shown (C7 design D6), offset 19, which now
    // sits on page 4.
    budget.value = 5;
    await w.setProps({ fontScale: 2 });
    await settle();
    expect(pageSurface(w).attributes("data-pages")).toBe("6");
    expect(pageSurface(w).attributes("data-page")).toBe("4");
    expect(pageSurface(w).text()).toBe("己庚辛壬。");
    expect(live(w)).toBe(spoken);
    // Back to the normal size: the anchor did not drift.
    budget.value = 10;
    await w.setProps({ fontScale: 1 });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("2");
  });

  it("re-pages on a box change reported by the ResizeObserver", async () => {
    let observerCallback = null;
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback) {
          observerCallback = callback;
        }
        observe() {}
        disconnect() {}
      },
    );
    const w = await mountThenArrive();
    await w.get('[data-testid="message-window"]').trigger("click");
    budget.value = 30;
    const surface = pageSurface(w).element;
    surface.getBoundingClientRect = () => ({ width: 900, height: 400 });
    observerCallback([]);
    await settle();
    expect(pageSurface(w).attributes("data-pages")).toBe("1");
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(marker(w).text()).toBe("■");
  });

  it("shows the first block unpaged until the fonts are ready", async () => {
    let resolveFonts;
    const ready = new Promise((resolve) => {
      resolveFonts = resolve;
    });
    Object.defineProperty(document, "fonts", { value: { ready }, configurable: true });
    try {
      const w = await mountWindow({
        lines: [...ARRIVAL, ...seqLines(2, [["in", "look"], ["out", LONG], ["out", "尾聲。"]])],
      });
      expect(pageSurface(w).text()).toBe(LONG);
      expect(pageSurface(w).attributes("data-oversize")).toBe("true");
      expect(marker(w).exists()).toBe(false);
      resolveFonts();
      await ready;
      await settle();
      expect(pageSurface(w).attributes("data-oversize")).toBe("false");
      expect(pageSurface(w).text()).toBe("尾聲。");
      expect(marker(w).text()).toBe("■");
      expect(live(w)).toBe("");
    } finally {
      delete document.fonts;
    }
  });

  it("gives a block that fits no page its own oversize page", async () => {
    budget.value = 4;
    const w = await mountWindow({
      lines: seqLines(1, [["in", "map"], ["out", "┌──┐<br>│@ │<br>└──┘"]]),
    });
    expect(pageSurface(w).attributes("data-oversize")).toBe("true");
    expect(pageSurface(w).find(".narrative-line.map-art").exists()).toBe(true);
  });

  it("starts a new page at an err line in the seal treatment", async () => {
    budget.value = 50;
    const w = await mountWindow();
    await w.setProps({
      lines: [...ARRIVAL, ...seqLines(2, [["in", "north"], ["out", "你走向北門。"], ["err", "門鎖著。"]])],
    });
    await settle();
    expect(pageSurface(w).attributes("data-pages")).toBe("2");
    await w.get('[data-testid="message-window"]').trigger("click");
    expect(pageSurface(w).find(".narrative-line.err").text()).toBe("門鎖著。");
  });

  it("marks a sys continuation after a cut with the cont class", async () => {
    budget.value = 6;
    const w = await mountWindow();
    await w.setProps({
      lines: [...ARRIVAL, ...seqLines(2, [["in", "look"], ["sys", "甲乙丙丁戊。己庚辛壬癸。"]])],
    });
    await settle();
    expect(pageSurface(w).find(".narrative-line.sys").classes()).not.toContain("cont");
    await w.get('[data-testid="message-window"]').trigger("click");
    expect(pageSurface(w).find(".narrative-line.sys").classes()).toContain("cont");
  });

  it("emits open-full-log on wheel-up over a page with nothing to scroll", async () => {
    const w = await mountWindow();
    await w.get('[data-testid="message-window"]').trigger("wheel", { deltaY: -40 });
    expect(w.emitted("open-full-log")).toHaveLength(1);
    await w.get('[data-testid="message-window"]').trigger("wheel", { deltaY: 40 });
    expect(w.emitted("open-full-log")).toHaveLength(1);
  });

  it("keeps the live region polite, atomic, and outside the page surface", async () => {
    const w = await mountWindow();
    const region = w.get('[data-testid="message-live"]');
    expect(region.attributes("role")).toBe("status");
    expect(region.attributes("aria-live")).toBe("polite");
    expect(region.attributes("aria-atomic")).toBe("true");
    expect(pageSurface(w).attributes("aria-live")).toBeUndefined();
    expect(pageSurface(w).attributes("tabindex")).toBe("0");
    expect(pageSurface(w).attributes("aria-describedby")).toBe(
      w.get(".message-window__sr").attributes("id"),
    );
  });
});
