// webclient-combat-beat-queue (design D6/D9): the message window's beat
// pages — the beat-and-tail page list, the queue's pacing, the report of a
// shown beat, the activation that ends the round, the end-of-round move to
// the response's remaining lines, and the `off` level's ordinary pages.
//
// jsdom has no layout, so every case injects a deterministic code-point
// `pageFit` (the documented test seam) and fakes the animation frame clock
// where a case needs real typing.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import MessageWindow from "../components/MessageWindow.vue";

function codePointFit(budget) {
  return (fragments) =>
    fragments.reduce((sum, fragment) => sum + (fragment.end - fragment.start), 0) <= budget.value;
}

function seqLines(start, entries) {
  return entries.map(([kind, text], index) => ({ kind, text, seq: start + index }));
}

const ARRIVAL = seqLines(1, [["out", "渡口的霧。"]]);

// The round's response: its `in` echo heads it at seq 2 (the dispatch's
// response mark), so the response's own start is 2.
const ROUND_LINES = seqLines(2, [
  ["in", "attack"],
  ["out", "第一擊。"],
  ["out", "第二擊。"],
  ["out", "行動完成，繼續戰鬥。"],
]);

const BEAT_TEXTS = ["第一擊。", "第二擊。"];

function beatPlayback(overrides = {}) {
  return {
    round: "s-1/1",
    startSeq: 2,
    auto: true,
    index: 0,
    count: BEAT_TEXTS.length,
    phase: "text",
    texts: BEAT_TEXTS,
    coveredLines: 2,
    terminal: false,
    ...overrides,
  };
}

async function settle() {
  await nextTick();
  await nextTick();
  await nextTick();
}

const windowEl = (w) => w.get('[data-testid="message-window"]');
const pageSurface = (w) => w.get('[data-testid="message-page"]');
const marker = (w) => w.find('[data-testid="message-page-marker"]');
const live = (w) => w.get('[data-testid="message-live"]').text();
const shownBeats = (w) => (w.emitted("beat-shown") || []).map(([index]) => index);

describe("MessageWindow beat pages (webclient-combat-beat-queue)", () => {
  let wrapper;
  let budget;

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
  });

  async function mountWindow(props = {}) {
    wrapper = mount(MessageWindow, {
      attachTo: document.body,
      props: {
        lines: ARRIVAL,
        marks: [],
        pageFit: codePointFit(budget),
        textSpeed: "instant",
        ...props,
      },
    });
    await settle();
    return wrapper;
  }

  // The window on the earlier response, then the round's response and its
  // published playback arrive together (the live delivery order: the text
  // lines land first, the panel binds the round).
  async function arriveRound(playback = beatPlayback(), lines = ROUND_LINES) {
    const w = await mountWindow();
    await w.setProps({ lines: [...ARRIVAL, ...lines], beatPlayback: playback });
    await settle();
    return w;
  }

  async function tick(ms) {
    vi.advanceTimersByTime(ms);
    await settle();
  }

  it("pages the beats and then the response's remaining lines", async () => {
    const w = await arriveRound();
    // Two beat pages plus the round's closing line.
    expect(pageSurface(w).attributes("data-pages")).toBe("3");
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(pageSurface(w).text()).toBe("第一擊。");
    expect(live(w)).toBe("第一擊。");
  });

  it("reports each beat once its page is fully shown, and follows the store's beat", async () => {
    const w = await arriveRound();
    expect(shownBeats(w)).toEqual([0]);
    // The queue moves on: the next beat's page replaces it and is reported.
    await w.setProps({ beatPlayback: beatPlayback({ index: 1 }) });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    expect(pageSurface(w).text()).toBe("第二擊。");
    expect(shownBeats(w)).toEqual([0, 1]);
    // A repeated report of the same beat is never emitted twice.
    await w.setProps({ beatPlayback: beatPlayback({ index: 1 }) });
    await settle();
    expect(shownBeats(w)).toEqual([0, 1]);
  });

  it("waits the beat pause before a further page of the same beat", async () => {
    budget.value = 4;
    // jsdom loads no stylesheet, so the token is stubbed as the level blocks
    // declare it at `full` and at `reduced`.
    const computed = window.getComputedStyle;
    window.getComputedStyle = (element) => ({
      getPropertyValue: (name) =>
        name === "--motion-beat" ? "400ms" : computed(element).getPropertyValue(name),
    });
    const w = await arriveRound(
      beatPlayback({ count: 1, texts: ["一二三四五六七八。"] }),
      seqLines(2, [["in", "attack"], ["out", "一二三四五六七八。"], ["out", "行動完成，繼續戰鬥。"]]),
    );
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(shownBeats(w)).toEqual([]);
    // The beat's first page is fully shown: the next page waits the pause
    // (a ~400ms frame clock, so the boundary is asserted from both sides).
    await tick(300);
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    await tick(500);
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    // Neither page has reported the beat yet: it still has a page to come.
    expect(shownBeats(w)).toEqual([]);
    await tick(500);
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    // The beat's last page reports it.
    expect(shownBeats(w)).toEqual([0]);
    window.getComputedStyle = computed;
  });

  it("hides the marker and does not auto-advance while the queue paces", async () => {
    const w = await arriveRound(beatPlayback(), undefined);
    expect(marker(w).exists()).toBe(false);
    // A press cannot advance the page on its own.
    await pageSurface(w).trigger("keydown", { key: "Enter" });
    expect(pageSurface(w).attributes("data-page")).toBe("1");
  });

  it("ends a playing round on a click and on Enter / Space, without advancing", async () => {
    const w = await arriveRound();
    await windowEl(w).trigger("click");
    expect(w.emitted("beat-skip")).toHaveLength(1);
    expect(pageSurface(w).attributes("data-page")).toBe("1");

    await pageSurface(w).trigger("keydown", { key: "Enter" });
    await pageSurface(w).trigger("keydown", { key: " " });
    expect(w.emitted("beat-skip")).toHaveLength(3);
    expect(pageSurface(w).attributes("data-page")).toBe("1");
  });

  it("moves to the first page after the beats when the round ends", async () => {
    const w = await arriveRound();
    await w.setProps({ beatPlayback: beatPlayback({ phase: "done", index: 1 }) });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    expect(pageSurface(w).text()).toBe("行動完成，繼續戰鬥。");
    expect(marker(w).text()).toBe("■");
    // Normal reading resumes, including a further click.
    await windowEl(w).trigger("click");
    expect(w.emitted("beat-skip")).toBeUndefined();
  });

  it("stays on the last beat page when the response has nothing after the beats", async () => {
    const w = await arriveRound(
      beatPlayback(),
      seqLines(2, [["in", "attack"], ["out", "第一擊。"], ["out", "第二擊。"]]),
    );
    await w.setProps({ beatPlayback: beatPlayback({ phase: "done", index: 1 }) });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    // Nothing follows the beats, so the last beat page shows its end marker.
    expect(marker(w).text()).toBe("■");
  });

  it("keeps the beat page across a re-page (a prose-scale change mid-round)", async () => {
    const w = await arriveRound();
    await w.setProps({ beatPlayback: beatPlayback({ index: 1 }) });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    await w.setProps({ fontScale: 1.2 });
    await settle();
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    expect(pageSurface(w).text()).toBe("第二擊。");
  });

  it("treats the beat pages as ordinary pages at off", async () => {
    const w = await arriveRound(beatPlayback({ auto: false, phase: "done" }));
    expect(pageSurface(w).attributes("data-pages")).toBe("3");
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(pageSurface(w).text()).toBe("第一擊。");
    expect(marker(w).text()).toBe("▼");
    // The reader turns them: no beat-skip, one page per activation.
    await windowEl(w).trigger("click");
    expect(w.emitted("beat-skip")).toBeUndefined();
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    await windowEl(w).trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("3");
    expect(pageSurface(w).text()).toBe("行動完成，繼續戰鬥。");
    expect(marker(w).text()).toBe("■");
  });

  it("restarts the response at the first beat when the round binds late", async () => {
    budget.value = 10;
    const w = await mountWindow();
    await w.setProps({ lines: [...ARRIVAL, ...ROUND_LINES] });
    await settle();
    // The response pages as an ordinary one and the reader advances.
    expect(pageSurface(w).attributes("data-pages")).toBe("2");
    expect(pageSurface(w).text()).toContain("第一擊。");
    await windowEl(w).trigger("click");
    expect(pageSurface(w).attributes("data-page")).toBe("2");
    // The round then binds: the response restarts at beat 0.
    await w.setProps({ beatPlayback: beatPlayback() });
    await settle();
    expect(pageSurface(w).attributes("data-pages")).toBe("3");
    expect(pageSurface(w).attributes("data-page")).toBe("1");
    expect(pageSurface(w).text()).toBe("第一擊。");
  });

  it("announces each beat page once, when it starts", async () => {
    const w = await arriveRound(beatPlayback(), undefined);
    expect(wrapper.props("textSpeed")).toBe("instant");
    expect(live(w)).toBe("第一擊。");
    await w.setProps({ beatPlayback: beatPlayback({ index: 1 }) });
    await settle();
    expect(live(w)).toBe("第二擊。");
  });

  it("types a beat page at the reader's speed and reports it when it completes", async () => {
    wrapper = mount(MessageWindow, {
      attachTo: document.body,
      props: { lines: ARRIVAL, marks: [], pageFit: codePointFit(budget), textSpeed: "normal" },
    });
    await settle();
    await wrapper.setProps({ lines: [...ARRIVAL, ...ROUND_LINES], beatPlayback: beatPlayback() });
    await settle();
    expect(windowEl(wrapper).attributes("data-typing")).toBe("true");
    expect(shownBeats(wrapper)).toEqual([]);
    // A press while typing ends the round rather than completing the page.
    await pageSurface(wrapper).trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("beat-skip")).toHaveLength(1);
  });
});
