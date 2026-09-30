import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import ReadingSample from "../../components/ReadingSample.vue";
import SettingsOverlay from "../../components/SettingsOverlay.vue";

// ReadingSample (webclient-settings-reading-preview): the settings overlay's
// local reading preview. It types one fixed line at the message window's
// effective rate, restarts once per preference change, replays on request,
// never loops, and stops its clock when unmounted. It reaches no store and
// emits nothing, so the live reader and the narrative log are untouched.

const SAMPLE = "晨霧自河面升起，鐘樓敲過第七聲。櫃檯後的書記抬起頭：「今天也來接委託嗎？」";
const UNITS = Array.from(SAMPLE).length;

// Advance the fake rAF clock in frame-sized steps (the typewriter clamps
// each frame to 100ms).
async function run(ms) {
  for (let t = 0; t < ms; t += 16) {
    vi.advanceTimersByTime(16);
  }
  await nextTick();
}

function shownLength(wrapper) {
  const text = wrapper.get('[data-testid="settings-sample-text"]');
  const tail = text.find(".reading-sample__tail").text();
  return Array.from(text.text().replace("■", "")).length - Array.from(tail).length;
}

describe("ReadingSample", () => {
  let wrapper;

  beforeEach(() => {
    vi.useFakeTimers({
      toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance", "setTimeout", "clearTimeout"],
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    vi.useRealTimers();
  });

  it("plays once at the chosen speed, then stops with the end marker", async () => {
    wrapper = mount(ReadingSample, { props: { textSpeed: "normal", motionLevel: "full" } });
    await nextTick();
    const sample = wrapper.get('[data-testid="settings-sample"]');
    expect(sample.attributes("data-typing")).toBe("true");
    expect(wrapper.get('[data-testid="settings-sample-caption"]').text()).toBe("標準 · 每秒 45 字");
    await run(400);
    const midway = shownLength(wrapper);
    expect(midway).toBeGreaterThan(0);
    expect(midway).toBeLessThan(UNITS);
    await run(1200);
    expect(sample.attributes("data-typing")).toBe("false");
    expect(shownLength(wrapper)).toBe(UNITS);
    expect(wrapper.get(".reading-sample__marker").classes()).toContain("is-shown");
    // It never loops: no frame stays scheduled once the line is out.
    expect(vi.getTimerCount()).toBe(0);
  });

  it("shows the line at once for 瞬間 and whenever the motion level is not 完整", async () => {
    for (const [props, caption] of [
      [{ textSpeed: "instant", motionLevel: "full" }, "瞬間 · 立即顯示"],
      [{ textSpeed: "slow", motionLevel: "reduced" }, "動態效果「減少」· 立即顯示"],
      [{ textSpeed: "slow", motionLevel: "off" }, "動態效果「關閉」· 立即顯示"],
    ]) {
      const w = mount(ReadingSample, { props });
      await nextTick();
      expect(w.get('[data-testid="settings-sample"]').attributes("data-typing")).toBe("false");
      expect(shownLength(w)).toBe(UNITS);
      expect(w.get('[data-testid="settings-sample-caption"]').text()).toBe(caption);
      // Replay shows it at once too.
      await w.get('[data-testid="settings-sample-replay"]').trigger("click");
      await nextTick();
      expect(w.get('[data-testid="settings-sample"]').attributes("data-typing")).toBe("false");
      expect(shownLength(w)).toBe(UNITS);
      w.unmount();
    }
  });

  it("restarts once when the scale, speed or motion level changes", async () => {
    wrapper = mount(ReadingSample, { props: { fontScale: 1, textSpeed: "fast", motionLevel: "full" } });
    await run(1000);
    expect(shownLength(wrapper)).toBe(UNITS);
    for (const change of [{ fontScale: 1.12 }, { textSpeed: "slow" }, { motionLevel: "full", fontScale: 0.92 }]) {
      await wrapper.setProps(change);
      await nextTick();
      expect(wrapper.get('[data-testid="settings-sample"]').attributes("data-typing")).toBe("true");
      expect(shownLength(wrapper)).toBe(0);
      await run(2500);
      expect(shownLength(wrapper)).toBe(UNITS);
    }
    // The restart reads the new rate: slow types 20 characters a second.
    await wrapper.setProps({ fontScale: 1 });
    await run(500);
    expect(shownLength(wrapper)).toBeLessThanOrEqual(11);
    expect(wrapper.get('[data-testid="settings-sample"]').attributes("style")).toContain("--prose-scale: 1");
  });

  it("replays on request", async () => {
    wrapper = mount(ReadingSample, { props: { textSpeed: "normal", motionLevel: "full" } });
    await run(1500);
    await wrapper.get('[data-testid="settings-sample-replay"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="settings-sample"]').attributes("data-typing")).toBe("true");
    await run(1500);
    expect(shownLength(wrapper)).toBe(UNITS);
  });

  it("stops its clock when unmounted mid-type", async () => {
    wrapper = mount(ReadingSample, { props: { textSpeed: "slow", motionLevel: "full" } });
    await run(200);
    expect(vi.getTimerCount()).toBeGreaterThan(0);
    wrapper.unmount();
    wrapper = null;
    expect(vi.getTimerCount()).toBe(0);
  });

  it("gives assistive technology the whole line, never a partly typed one", async () => {
    wrapper = mount(ReadingSample, { props: { textSpeed: "slow", motionLevel: "full" } });
    await run(200);
    expect(wrapper.get(".reading-sample__sr").text()).toBe(SAMPLE);
    expect(wrapper.get('[data-testid="settings-sample-text"]').attributes("aria-hidden")).toBe("true");
    expect(wrapper.find('[aria-live]').exists()).toBe(false);
  });
});

describe("SettingsOverlay reading sample and switches", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("hands the sample the preferences and emits nothing when it replays", async () => {
    wrapper = mount(SettingsOverlay, { props: { fontScale: 1.12, textSpeed: "instant", motionLevel: "full" } });
    const sample = wrapper.getComponent(ReadingSample);
    expect(sample.props()).toEqual({ fontScale: 1.12, textSpeed: "instant", motionLevel: "full" });
    await wrapper.get('[data-testid="settings-sample-replay"]').trigger("click");
    expect(wrapper.emitted()).not.toHaveProperty("scale-change");
    expect(Object.keys(wrapper.emitted()).filter((name) => name.endsWith("-change"))).toEqual([]);
  });

  it("exposes each toggle as a native switch named by its label and described by its help", () => {
    wrapper = mount(SettingsOverlay, { attachTo: document.body, props: { autoAdvance: true } });
    for (const [testid, label] of [
      ["settings-overlay-text-to-html", "HTML 敘事渲染"],
      ["settings-overlay-auto-advance", "自動翻頁"],
      ["settings-overlay-colorblind", "色盲配色"],
    ]) {
      const input = wrapper.get(`[data-testid="${testid}"]`);
      expect(input.attributes("type")).toBe("checkbox");
      expect(input.attributes("role")).toBe("switch");
      expect(input.attributes("aria-checked")).toBeUndefined();
      expect(document.getElementById(input.attributes("aria-labelledby")).textContent).toBe(label);
      expect(document.getElementById(input.attributes("aria-describedby")).textContent.length).toBeGreaterThan(0);
    }
    expect(wrapper.get('[data-testid="settings-overlay-auto-advance"]').element.checked).toBe(true);
  });

  it("emits exactly one change per toggle", async () => {
    wrapper = mount(SettingsOverlay);
    const toggle = wrapper.get('[data-testid="settings-overlay-auto-advance"]');
    toggle.element.checked = true;
    await toggle.trigger("change");
    expect(wrapper.emitted("auto-advance-change")).toEqual([[true]]);
  });
});
