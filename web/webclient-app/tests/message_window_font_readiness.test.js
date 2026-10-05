// Sliced-font cold arrivals must not paginate against fallback metrics or
// let an unmeasured response drive combat/auto-advance pacing.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import MessageWindow from "../components/MessageWindow.vue";

const arrival = [{ seq: 1, kind: "out", text: "渡口的霧。" }];
const page = (wrapper) => wrapper.get('[data-testid="message-page"]');
async function settle() {
  for (let i = 0; i < 12; i += 1) {
    await Promise.resolve();
    await nextTick();
  }
}
function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

describe("MessageWindow prepares actual response and beat glyphs", () => {
  let wrapper;
  let fonts;
  let originalFonts;
  beforeEach(() => {
    originalFonts = Object.getOwnPropertyDescriptor(document, "fonts");
    fonts = { ready: Promise.resolve(), load: vi.fn(() => Promise.resolve([])) };
    Object.defineProperty(document, "fonts", { configurable: true, value: fonts });
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function () {
      return {
        x: 0, y: 0, left: 0, top: 0, width: 720, right: 720,
        height: this.classList.contains("message-window__measure")
          ? this.textContent.length * 10 : 200,
        bottom: 200,
      };
    });
  });
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
    if (originalFonts) Object.defineProperty(document, "fonts", originalFonts);
    else delete document.fonts;
    vi.restoreAllMocks();
    vi.useRealTimers();
  });
  async function mountWindow(props = {}) {
    wrapper = mount(MessageWindow, {
      attachTo: document.body,
      props: { lines: arrival, marks: [], textSpeed: "instant", ...props },
    });
    await settle();
    return wrapper;
  }

  it("prepares rendered text in both weights before committing a new response", async () => {
    const w = await mountWindow();
    const pending = deferred();
    fonts.load.mockImplementation((_font, text) => text.includes("罕見")
      ? pending.promise : Promise.resolve([]));
    await w.setProps({ lines: [...arrival,
      { seq: 2, kind: "in", text: "look" },
      { seq: 3, kind: "out", text: "<b>罕見</b>", tokens: [{ kind: "text", value: "罕見" }] },
    ] });
    await settle();
    expect(page(w).text()).toBe("渡口的霧。");
    const requested = fonts.load.mock.calls.filter(([, text]) => text.includes("罕見"));
    expect(requested.map(([font]) => font.slice(0, 3))).toEqual(["400", "700"]);
    expect(requested.every(([, text]) => text === "罕見")).toBe(true);
    pending.resolve([]);
    await settle();
    expect(page(w).text()).toBe("罕見");
    expect(w.attributes("data-reading-complete")).toBe("true");
  });

  it("loads separately published beat glyphs and never reports a stale page as a shown beat", async () => {
    const w = await mountWindow();
    const pending = deferred();
    fonts.load.mockImplementation((_font, text) => text.includes("龘")
      ? pending.promise : Promise.resolve([]));
    await w.setProps({
      lines: [...arrival, { seq: 2, kind: "in", text: "attack" },
        { seq: 3, kind: "out", text: "一般回應。" },
        { seq: 4, kind: "out", text: "尾聲。" }],
      beatPlayback: { round: "s-1/1", startSeq: 2, auto: true, index: 0,
        count: 1, phase: "text", texts: ["龘麤。"], coveredLines: 1, terminal: false },
    });
    await settle();
    expect(w.emitted("beat-shown")).toBeUndefined();
    expect(page(w).text()).toBe("渡口的霧。");
    expect(fonts.load.mock.calls.some(([, text]) => text.includes("龘麤。") && text.includes("尾聲。"))).toBe(true);
    pending.resolve([]);
    await settle();
    expect(page(w).text()).toBe("龘麤。");
    expect(w.emitted("beat-shown")).toEqual([[0]]);
  });

  it("does not commit a superseded or unmounted preparation", async () => {
    const reading = vi.fn();
    const w = await mountWindow({ onReadingChange: reading });
    const pending = deferred();
    fonts.load.mockImplementation((_font, text) => text.includes("龘")
      ? pending.promise : Promise.resolve([]));
    const slow = [...arrival, { seq: 2, kind: "in", text: "look" },
      { seq: 3, kind: "out", text: "龘。" }];
    await w.setProps({ lines: slow });
    await settle();
    await w.setProps({ lines: [...slow, { seq: 4, kind: "in", text: "look" },
      { seq: 5, kind: "out", text: "霧。" }] });
    await settle();
    expect(page(w).text()).toBe("霧。");
    pending.resolve([]);
    await settle();
    expect(page(w).text()).toBe("霧。");
    const unmounted = deferred();
    fonts.load.mockImplementation(() => unmounted.promise);
    await w.setProps({ fontScale: 1.25 });
    await settle();
    const events = reading.mock.calls.length;
    w.unmount();
    wrapper = null;
    unmounted.resolve([]);
    await settle();
    expect(reading).toHaveBeenCalledTimes(events);
  });

  it("settles a failed font face and measures available terminal metrics", async () => {
    fonts.load.mockRejectedValue(new Error("font resource failed"));
    const w = await mountWindow();
    expect(page(w).text()).toBe("渡口的霧。");
    expect(w.attributes("data-reading-complete")).toBe("true");
  });

  it("disarms old-layout auto-advance while a new beat binding prepares fonts", async () => {
    vi.useFakeTimers();
    const oldLines = [...arrival, { seq: 2, kind: "in", text: "look" },
      { seq: 3, kind: "out", text: "舊。".repeat(30) }];
    const w = await mountWindow({ autoAdvance: true });
    await w.setProps({ lines: oldLines });
    await settle();
    expect(Number(page(w).attributes("data-pages"))).toBeGreaterThan(1);
    expect(page(w).attributes("data-page")).toBe("1");
    const before = page(w).text();
    const pending = deferred();
    fonts.load.mockImplementation((_font, text) => text.includes("龘")
      ? pending.promise : Promise.resolve([]));
    await w.setProps({ beatPlayback: {
      round: "s-1/1", startSeq: 2, auto: false, index: 0, count: 1,
      phase: "done", texts: ["龘。"], coveredLines: 1, terminal: false,
    } });
    await settle();
    vi.advanceTimersByTime(10000);
    await settle();
    expect(page(w).attributes("data-page")).toBe("1");
    expect(page(w).text()).toBe(before);
    pending.resolve([]);
    await settle();
    expect(page(w).text()).toBe("龘。");
  });
});
