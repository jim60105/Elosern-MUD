// The campfire beat (OpenSpec change wilderness-camping; design §5): a
// presentation-only beat. Bars move from the committed before to the after
// value over 1.6 s; an early key or click only finishes it; Continue/Enter
// emits once; motion off shows the final state at once. Synthetic data.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CampfireCard from "../../components/travel/CampfireCard.vue";

const wrappers = [];
beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  while (wrappers.length) wrappers.pop().unmount();
  document.body.innerHTML = "";
});

function result(overrides = {}) {
  return {
    camp_id: "c".repeat(64),
    phase: "complete",
    timing: { elapsed_seconds: 36000, result_tick: 900, result_time: "第 2 日 06:00", wake_tick: 900, wake_time: "第 2 日 06:00" },
    members: [
      { member_id: "42", name: "旅人", reserve_before: 180000, reserve_after: 360000, reserve_max: 360000, before_percent: 50, after_percent: 100, sleeping: false, wake_tick: 900 },
      { member_id: "7", name: "守夜人", reserve_before: 360000, reserve_after: 300000, reserve_max: 360000, before_percent: 100, after_percent: 83, sleeping: false, wake_tick: null },
    ],
    events: [{ kind: "daily_reset", due_tick: 864, interactive: false, text: "新的一天開始了。" }],
    interrupted: false,
    interruption_reason: null,
    ...overrides,
  };
}

function beat(props = {}) {
  const w = mount(CampfireCard, {
    attachTo: document.body,
    props: { result: result(), message: "夜裡無事。", motionLevel: "full", ...props },
  });
  wrappers.push(w);
  return w;
}

const percents = (w) => w.findAll('[data-testid="campfire-member"]').map((m) => m.attributes("data-percent"));

describe("the campfire beat", () => {
  it("fills from before to after over 1.6 s, then shows the server lines", async () => {
    const w = beat();
    await nextTick();
    expect(percents(w)).toEqual(["50", "100"]);
    expect(w.attributes("data-settled")).toBe("false");
    expect(w.find('[data-testid="campfire-result"]').exists()).toBe(false);
    vi.advanceTimersByTime(100);
    await nextTick();
    expect(percents(w)).toEqual(["100", "83"]);
    expect(w.attributes("data-settled")).toBe("false");
    vi.advanceTimersByTime(1600);
    await nextTick();
    expect(w.attributes("data-settled")).toBe("true");
    expect(w.get('[data-testid="campfire-result"]').text()).toBe("夜裡無事。");
    expect(w.findAll('[data-testid="campfire-event"]')).toHaveLength(1);
    // Only a body that slept carries the crescent.
    expect(w.findAll('[data-testid="campfire-member"]').map((m) => m.find('[data-testid="campfire-moon"]').exists())).toEqual([true, false]);
  });

  it("an early key or click only finishes the beat and is consumed", async () => {
    const w = beat();
    await nextTick();
    const seen = [];
    const listener = (event) => seen.push(event.key);
    document.addEventListener("keydown", listener);
    await w.trigger("keydown", { key: "Enter" });
    document.removeEventListener("keydown", listener);
    await nextTick();
    expect(seen).toEqual([]);
    expect(w.attributes("data-settled")).toBe("true");
    expect(percents(w)).toEqual(["100", "83"]);
    expect(w.emitted("continue")).toBeUndefined();

    const v = beat();
    await nextTick();
    await v.trigger("pointerdown");
    await nextTick();
    expect(v.attributes("data-settled")).toBe("true");
    expect(v.emitted("continue")).toBeUndefined();
  });

  it("Continue and Enter emit once after the beat settled", async () => {
    const w = beat();
    await nextTick();
    vi.advanceTimersByTime(2000);
    await nextTick();
    await w.trigger("keydown", { key: "Enter" });
    await w.get('[data-testid="campfire-continue"]').trigger("click");
    await w.trigger("keydown", { key: "Enter", repeat: true });
    expect(w.emitted("continue")).toHaveLength(1);
  });

  it("motion off renders the final state on the first frame", async () => {
    const w = beat({ motionLevel: "off" });
    await nextTick();
    expect(w.attributes("data-settled")).toBe("true");
    expect(percents(w)).toEqual(["100", "83"]);
    expect(w.find('[data-testid="campfire-result"]').exists()).toBe(true);
    expect(w.classes()).toContain("is-still");
  });

  it("an interrupted result shows its reason line and no wake", async () => {
    const w = beat({
      motionLevel: "off",
      message: "紮營在第 1 日 21:00中斷：途中發生了需要留意的事。",
      result: result({
        phase: "interrupted", interrupted: true, interruption_reason: "interactive_event",
        timing: { elapsed_seconds: 3600, result_tick: 400, result_time: "第 1 日 21:00", wake_tick: null, wake_time: null },
      }),
    });
    await nextTick();
    expect(w.classes()).toContain("is-interrupted");
    expect(w.get('[data-testid="campfire-result"]').text()).toContain("中斷");
  });
});
