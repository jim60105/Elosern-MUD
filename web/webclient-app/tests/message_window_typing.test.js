// webclient-typewriter-reading-prefs (task 4.5): the message window's
// typewriter. jsdom has no layout, so a deterministic code-point `pageFit`
// (the documented test seam) pages; `requestAnimationFrame` and
// `performance` are faked so the typing clock advances with
// `vi.advanceTimersByTime`, one 16ms frame at a time.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import MessageWindow from "../components/MessageWindow.vue";
import { dialogueViewModel } from "../stores/dialogue-view.js";

function codePointFit(budget) {
  return (fragments) =>
    fragments.reduce((sum, fragment) => sum + (fragment.end - fragment.start), 0) <= budget.value;
}

function seqLines(start, entries) {
  return entries.map(([kind, text], index) => ({ kind, text, seq: start + index }));
}

const ARRIVAL = seqLines(1, [["out", "渡口的霧。"]]);
// 90 code points with no sentence end: one page at a budget of 100.
const NINETY = "一二三四五六七八九十".repeat(9);
// 30 code points, sentence ends every 10: three pages at a budget of 10.
const LONG = "一二三四五六七八九。甲乙丙丁戊己庚辛壬。天地玄黃宇宙洪荒日。";

async function settle() {
  await nextTick();
  await nextTick();
  await nextTick();
}

const windowEl = (w) => w.get('[data-testid="message-window"]');
const pageSurface = (w) => w.get('[data-testid="message-page"]');
const marker = (w) => w.find('[data-testid="message-page-marker"]');
const live = (w) => w.get('[data-testid="message-live"]').text();

// The text a reader sees: the page minus its hidden, unrevealed parts.
function revealedText(w) {
  const clone = pageSurface(w).element.cloneNode(true);
  clone.querySelectorAll(".narrative-unrevealed, .narrative-line.unrevealed").forEach((el) => el.remove());
  return clone.textContent;
}

async function tick(ms) {
  vi.advanceTimersByTime(ms);
  await settle();
}

// Advance in short steps so Vue's scheduler (microtasks, not faked) runs
// between frames, as it does in a browser.
async function tickSteps(ms, step = 50) {
  for (let spent = 0; spent < ms; spent += step) {
    await tick(Math.min(step, ms - spent));
  }
}

function stubMatchMedia(matches) {
  const listeners = new Set();
  const media = {
    matches,
    media: "(prefers-reduced-motion: reduce)",
    addEventListener: (_type, fn) => listeners.add(fn),
    removeEventListener: (_type, fn) => listeners.delete(fn),
  };
  window.matchMedia = () => media;
  return {
    listeners,
    set(value) {
      media.matches = value;
      for (const fn of listeners) fn({ matches: value });
    },
  };
}

describe("MessageWindow typewriter", () => {
  let wrapper;
  let budget;
  const originalMatchMedia = window.matchMedia;

  beforeEach(() => {
    budget = { value: 100 };
    vi.useFakeTimers({
      toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance", "setTimeout", "clearTimeout"],
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
    vi.useRealTimers();
    vi.unstubAllGlobals();
    window.matchMedia = originalMatchMedia;
  });

  async function mountWindow(props = {}) {
    wrapper = mount(MessageWindow, {
      attachTo: document.body,
      props: { lines: ARRIVAL, marks: [], pageFit: codePointFit(budget), ...props },
    });
    await settle();
    return wrapper;
  }

  // Mounted on an earlier response, then `text` arrives as a new response.
  async function arrive(text, props = {}) {
    const w = await mountWindow(props);
    await w.setProps({ lines: [...ARRIVAL, ...seqLines(2, [["in", "look"], ["out", text]])] });
    await settle();
    return w;
  }

  it("types a page at the normal speed with no marker until it is fully shown", async () => {
    const w = await arrive(NINETY);
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    expect(revealedText(w)).toBe("");
    expect(marker(w).exists()).toBe(false);
    // The whole page is rendered from the first frame; only its tail is hidden.
    expect(pageSurface(w).text()).toBe(NINETY);
    expect(pageSurface(w).find(".narrative-line").attributes("aria-hidden")).toBe("true");

    await tick(1000);
    const shown = Array.from(revealedText(w)).length;
    expect(shown).toBeGreaterThanOrEqual(40);
    expect(shown).toBeLessThanOrEqual(46);
    expect(NINETY.startsWith(revealedText(w))).toBe(true);
    expect(pageSurface(w).find(".narrative-unrevealed").attributes("aria-hidden")).toBe("true");
    expect(marker(w).exists()).toBe(false);

    await tick(1100);
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    expect(revealedText(w)).toBe(NINETY);
    expect(pageSurface(w).find(".narrative-unrevealed").exists()).toBe(false);
    expect(marker(w).text()).toBe("■");
  });

  it("opens a response that arrived while the fonts loaded on page 1 and types it", async () => {
    let resolveFonts;
    const ready = new Promise((resolve) => {
      resolveFonts = resolve;
    });
    Object.defineProperty(document, "fonts", { value: { ready }, configurable: true });
    try {
      budget.value = 10;
      const w = await arrive(LONG);
      // Fonts pending: the first block, unpaged and shown whole.
      expect(pageSurface(w).attributes("data-oversize")).toBe("true");
      expect(windowEl(w).attributes("data-typing")).toBe("false");
      resolveFonts();
      await ready;
      await settle();
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      expect(pageSurface(w).attributes("data-pages")).toBe("3");
      expect(windowEl(w).attributes("data-typing")).toBe("true");
      expect(revealedText(w)).toBe("");
      expect(live(w)).toBe("一二三四五六七八九。");
      await tick(400);
      expect(revealedText(w)).toBe("一二三四五六七八九。");
    } finally {
      delete document.fonts;
    }
  });

  it("still settles a log retained at mount on its last page once the fonts load", async () => {
    let resolveFonts;
    const ready = new Promise((resolve) => {
      resolveFonts = resolve;
    });
    Object.defineProperty(document, "fonts", { value: { ready }, configurable: true });
    try {
      budget.value = 10;
      const w = await mountWindow({
        lines: [...ARRIVAL, ...seqLines(2, [["in", "look"], ["out", LONG]])],
      });
      resolveFonts();
      await ready;
      await settle();
      expect(pageSurface(w).attributes("data-page")).toBe("3");
      expect(windowEl(w).attributes("data-typing")).toBe("false");
      expect(live(w)).toBe("");
    } finally {
      delete document.fonts;
    }
  });

  it("types at the slow and fast speeds", async () => {
    let w = await arrive(NINETY, { textSpeed: "slow" });
    await tick(1000);
    const slow = Array.from(revealedText(w)).length;
    expect(slow).toBeGreaterThanOrEqual(17);
    expect(slow).toBeLessThanOrEqual(20);
    w.unmount();

    w = await arrive(NINETY, { textSpeed: "fast" });
    await tick(500);
    const fast = Array.from(revealedText(w)).length;
    expect(fast).toBeGreaterThanOrEqual(40);
    expect(fast).toBeLessThanOrEqual(45);
    await tick(600);
    expect(revealedText(w)).toBe(NINETY);
  });

  it("counts at most 100ms of a long frame gap, so time in a hidden tab never counts", async () => {
    const frames = [];
    vi.stubGlobal("requestAnimationFrame", (callback) => frames.push(callback));
    vi.stubGlobal("cancelAnimationFrame", () => {});
    const w = await arrive(NINETY);
    const frame = async (time) => {
      frames.shift()(time);
      await settle();
    };
    await frame(1000);
    await frame(1016);
    // The tab was hidden for five seconds: the next frame adds only 100ms.
    await frame(6016);
    // 116ms at 45 cps.
    expect(Array.from(revealedText(w)).length).toBe(5);
    expect(windowEl(w).attributes("data-typing")).toBe("true");
  });

  it("completes a typing page on a click, then advances on the next click", async () => {
    budget.value = 10;
    const w = await arrive(LONG);
    await tick(50);
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    const spoken = live(w);
    await windowEl(w).trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(revealedText(w)).toBe("一二三四五六七八九。");
    expect(marker(w).text()).toBe("▼");
    expect(live(w)).toBe(spoken);
    await windowEl(w).trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    expect(marker(w).exists()).toBe(false);
  });

  it("completes on Enter, advances on the next Enter, and ignores a held key's repeats", async () => {
    budget.value = 10;
    const w = await arrive(LONG);
    const surface = pageSurface(w);
    surface.element.focus();
    const reached = vi.fn();
    document.addEventListener("keydown", reached);
    try {
      await surface.trigger("keydown", { key: "Enter" });
      expect(windowEl(w).attributes("data-typing")).toBe("false");
      expect(surface.attributes("data-page")).toBe("1");
      for (let i = 0; i < 3; i += 1) {
        await surface.trigger("keydown", { key: "Enter", repeat: true });
      }
      expect(surface.attributes("data-page")).toBe("1");
      await surface.trigger("keydown", { key: " " });
      expect(surface.attributes("data-page")).toBe("2");
      expect(reached).not.toHaveBeenCalled();
    } finally {
      document.removeEventListener("keydown", reached);
    }
  });

  it("announces each page once, when it starts, and nothing while typing or on completion", async () => {
    budget.value = 10;
    const w = await arrive(LONG);
    expect(live(w)).toBe("一二三四五六七八九。");
    await tick(300);
    expect(live(w)).toBe("一二三四五六七八九。");
    await tick(1000);
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    expect(live(w)).toBe("一二三四五六七八九。");
    await windowEl(w).trigger("click");
    expect(live(w)).toBe("甲乙丙丁戊己庚辛壬。");
  });

  it("stops typing and shows the last page complete when an action flushes", async () => {
    budget.value = 10;
    const w = await arrive(LONG);
    await tick(50);
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    // A silent action records its mark; no line has arrived yet.
    await w.setProps({ marks: [9] });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    expect(revealedText(w)).toBe("天地玄黃宇宙洪荒日。");
    expect(marker(w).text()).toBe("■");
  });

  it("resumes typing into lines appended to a fully shown page", async () => {
    const w = await arrive("渡口。", { textSpeed: "fast" });
    await tick(200);
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    await w.setProps({
      lines: [...ARRIVAL, ...seqLines(2, [["in", "look"], ["out", "渡口。"], ["out", "霧散了。"]])],
    });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    expect(revealedText(w)).toBe("渡口。");
    await tick(200);
    expect(revealedText(w)).toBe("渡口。霧散了。");
  });

  it("keeps the typing position through a re-page while typing", async () => {
    budget.value = 10;
    const w = await arrive(LONG);
    await windowEl(w).trigger("click");
    await windowEl(w).trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    await tick(100);
    const typed = Array.from(revealedText(w)).length;
    expect(typed).toBeGreaterThan(0);
    expect(typed).toBeLessThan(5);
    // Larger text: five code points per page; offset 10 + typed sits on page 3.
    budget.value = 5;
    await w.setProps({ fontScale: 2 });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    expect(revealedText(w)).toBe(Array.from("甲乙丙丁戊").slice(0, typed).join(""));
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    await tick(300);
    expect(revealedText(w)).toBe("甲乙丙丁戊");
  });

  it("keeps the last character shown through a re-page of a complete page", async () => {
    budget.value = 10;
    const w = await arrive(LONG, { textSpeed: "instant" });
    expect(revealedText(w)).toBe("一二三四五六七八九。");
    await w.setProps({ textSpeed: "normal" });
    budget.value = 5;
    await w.setProps({ fontScale: 2 });
    await settle();
    // Offset 9 (the last character shown) sits on page 2, shown in full.
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    expect(revealedText(w)).toBe("六七八九。");
    expect(windowEl(w).attributes("data-typing")).toBe("false");
  });

  it("completes the typing page on a switch to instant; other speed changes wait for the next page", async () => {
    const w = await arrive(NINETY);
    await tickSteps(1000);
    const atNormal = Array.from(revealedText(w)).length;
    // Slower mid-page: nothing un-reveals and the pace stays normal.
    await w.setProps({ textSpeed: "slow" });
    await settle();
    expect(Array.from(revealedText(w)).length).toBe(atNormal);
    await tickSteps(400);
    const later = Array.from(revealedText(w)).length;
    expect(later - atNormal).toBeGreaterThanOrEqual(16);
    expect(later - atNormal).toBeLessThanOrEqual(19);
    // Faster mid-page: no jump ahead either.
    await w.setProps({ textSpeed: "fast" });
    await settle();
    expect(Array.from(revealedText(w)).length).toBe(later);
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    await w.setProps({ textSpeed: "instant" });
    await settle();
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    expect(revealedText(w)).toBe(NINETY);
  });

  it("shows pages at once while the reduced-motion override is on", async () => {
    const w = await arrive(NINETY, { textSpeed: "slow", reducedMotion: "on" });
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    expect(revealedText(w)).toBe(NINETY);
    expect(marker(w).text()).toBe("■");
  });

  it("follows the OS reduced-motion query with no override, and an explicit off lets pages type", async () => {
    const media = stubMatchMedia(true);
    let w = await arrive(NINETY, { textSpeed: "slow" });
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    expect(revealedText(w)).toBe(NINETY);
    w.unmount();
    expect(media.listeners.size).toBe(0);

    w = await arrive(NINETY, { textSpeed: "slow", reducedMotion: "off" });
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    // Going live into reduced motion with no override completes the page.
    await w.setProps({ reducedMotion: null });
    await settle();
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    w.unmount();

    media.set(false);
    w = await arrive(NINETY, { textSpeed: "slow" });
    expect(windowEl(w).attributes("data-typing")).toBe("true");
    media.set(true);
    await settle();
    expect(windowEl(w).attributes("data-typing")).toBe("false");
  });

  describe("auto-advance", () => {
    it("advances after 1.2s + 60ms per character and stops at the last page", async () => {
      budget.value = 10;
      const w = await arrive(LONG, { textSpeed: "instant", autoAdvance: true });
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      // Ten characters: 1200 + 600 = 1800ms.
      await tick(1750);
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      await tick(100);
      expect(pageSurface(w).attributes("data-page")).toBe("2");
      await tick(1850);
      expect(pageSurface(w).attributes("data-page")).toBe("3");
      await tick(5000);
      expect(pageSurface(w).attributes("data-page")).toBe("3");
      expect(marker(w).text()).toBe("■");
    });

    it("waits for typing to finish before counting", async () => {
      budget.value = 10;
      const w = await arrive(LONG, { textSpeed: "slow", autoAdvance: true });
      // Ten characters at 20 cps: about half a second of typing, then the
      // 1.8s wait.
      await tickSteps(1800);
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      await tickSteps(700);
      expect(pageSurface(w).attributes("data-page")).toBe("2");
    });

    it("is off by default", async () => {
      budget.value = 10;
      const w = await arrive(LONG, { textSpeed: "instant" });
      await tick(10000);
      expect(pageSurface(w).attributes("data-page")).toBe("1");
    });

    it("pauses while held and resumes with the rest of the wait", async () => {
      budget.value = 10;
      const w = await arrive(LONG, { textSpeed: "instant", autoAdvance: true });
      await tick(1000);
      await w.setProps({ held: true });
      await tick(10000);
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      await w.setProps({ held: false });
      await tick(700);
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      await tick(200);
      expect(pageSurface(w).attributes("data-page")).toBe("2");
    });

    it("leaves an oversize map page to the player", async () => {
      budget.value = 10;
      const map = "┌──────────┐\n│    ＠    │\n└──────────┘";
      const w = await mountWindow({ textSpeed: "instant", autoAdvance: true });
      await w.setProps({
        lines: [...ARRIVAL, ...seqLines(2, [["in", "map"], ["out", map], ["out", "渡口。"]])],
      });
      await settle();
      expect(pageSurface(w).attributes("data-oversize")).toBe("true");
      await tick(20000);
      expect(pageSurface(w).attributes("data-page")).toBe("1");
      await windowEl(w).trigger("click");
      expect(pageSurface(w).attributes("data-page")).toBe("2");
    });
  });

  it("does not type or auto-advance the dialogue variant", async () => {
    const vm = dialogueViewModel({
      schema_version: 1,
      available: true,
      kind: "dialogue",
      host: { identity: 41, display_name: "公會職員", portrait_ref: null },
      bond_stage: null,
      line: "歡迎來到冒險者公會。",
      choices: [{ keyword_id: "公會", label: "公會" }],
    });
    const w = await mountWindow({ mode: "dialogue", dialogue: vm, textSpeed: "slow", autoAdvance: true });
    await w.setProps({
      dialogue: { ...vm, line: "任務板在那裡。" },
      lines: [...ARRIVAL, ...seqLines(2, [["in", "talk"], ["out", LONG]])],
    });
    await settle();
    expect(windowEl(w).attributes("data-variant")).toBe("dialogue");
    expect(windowEl(w).attributes("data-typing")).toBe("false");
    expect(w.get('[data-testid="dialogue-say"]').text()).toBe("任務板在那裡。");
    expect(w.findAll('[data-testid="dialogue-pick"]').length).toBeGreaterThan(0);
    expect(w.find(".narrative-unrevealed").exists()).toBe(false);
    await tick(20000);
    expect(windowEl(w).attributes("data-variant")).toBe("dialogue");
  });
});
