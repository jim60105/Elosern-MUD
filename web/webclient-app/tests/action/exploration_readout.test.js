// exploration-exit-compass (task 3.2): the shared readout line — the live
// region and its tones, the priority helper (flash, aim, idle), the aim and
// blocked mappings, the flash timing, and the `off` motion level.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";
import ExplorationReadout from "../../components/ExplorationReadout.vue";
import {
  DEAD_END_TEXT,
  FLASH_MS,
  NO_EXIT_TEXT,
  aimReadout,
  blockedReadout,
  idleReadout,
  presentCount,
  readoutContent,
} from "../../components/exploration-readout.js";
import { useReadoutState } from "../../composables/use-exit-compass.js";

const angled = { kind: "angled", angle: 270, glyph: "←", label: "西部丘陵與谷地", enabled: true, reason: null };
const portal = { kind: "portal", slot: 0, glyph: "⇧", label: "塔樓三層", enabled: true, reason: null };
const locked = { kind: "angled", angle: 0, glyph: "↑", label: "north", enabled: false, reason: "前方的吊橋已經收起。" };

describe("aimReadout", () => {
  it("an angled target leads with 前往 and its octant glyph and names the destination", () => {
    expect(aimReadout({ angle: 270, target: angled, zone: "pad" })).toEqual({
      lead: "前往 ←",
      text: "西部丘陵與谷地",
      tone: "normal",
    });
  });

  it("a portal leads with 通道 and its bead glyph", () => {
    expect(aimReadout({ angle: 0, target: portal, zone: "ring" })).toEqual({ lead: "通道 ⇧", text: "塔樓三層", tone: "normal" });
  });

  it("a disabled target shows 無法通行 and the server reason unaltered in the warn tone", () => {
    expect(aimReadout({ angle: 0, target: locked, zone: "pad" })).toEqual({
      lead: "無法通行",
      text: "前方的吊橋已經收起。",
      tone: "warn",
    });
  });

  it("an aim at nothing shows the octant glyph over the no-exit line, quietly", () => {
    expect(aimReadout({ angle: 100, target: null, zone: "pad" })).toEqual({ lead: "→", text: NO_EXIT_TEXT, tone: "quiet" });
  });

  it("the dead zone says the direction has no exit", () => {
    expect(aimReadout({ angle: null, target: null, zone: "dead" })).toMatchObject({ text: NO_EXIT_TEXT, tone: "quiet" });
  });

  it("no aim contributes nothing", () => {
    expect(aimReadout(null)).toBeNull();
    expect(aimReadout({ angle: null, target: null, zone: "none" })).toBeNull();
  });
});

describe("blockedReadout", () => {
  it("maps each stop to a warn-tone flash", () => {
    expect(blockedReadout({ kind: "dead-end", angle: 0 })).toEqual({ lead: "↑", text: DEAD_END_TEXT, tone: "warn" });
    expect(blockedReadout({ kind: "disabled", target: locked, angle: 0 }).text).toBe("前方的吊橋已經收起。");
    expect(blockedReadout({ kind: "rejected", message: "你被荊棘纏住了。", angle: 0 }).text).toBe("你被荊棘纏住了。");
    expect(blockedReadout({ kind: "no-change", angle: 0 }, { resultMessage: "你停在原地。" }).text).toBe("你停在原地。");
    expect(blockedReadout({ kind: "no-exit", angle: null }).text).toBe(`${NO_EXIT_TEXT}。`);
    expect(blockedReadout({ kind: "suppressed", angle: 0 }).tone).toBe("warn");
    expect(blockedReadout(null)).toBeNull();
  });
});

describe("idle summary and priority", () => {
  it("counts exits and the people present", () => {
    const panel = {
      interact: [{ identity: 1 }, { identity: 2 }],
      look: { entities: [{ identity: 2 }, { identity: 3 }] },
    };
    expect(presentCount(panel)).toBe(3);
    expect(presentCount(null)).toBe(0);
    expect(idleReadout(3, 2)).toEqual({ lead: "", text: "出口 3 · 在場 2", tone: "quiet" });
    expect(idleReadout(0, 1).text).toBe("出口 0 · 在場 1");
  });

  it("chooses flash, then aim, then idle", () => {
    const flash = { lead: "無法通行", text: "x", tone: "warn" };
    const aim = { lead: "前往 ↑", text: "y", tone: "normal" };
    const idle = idleReadout(1, 0);
    expect(readoutContent({ flash, aim, idle })).toEqual({ ...flash, flash: true });
    expect(readoutContent({ aim, idle })).toEqual({ ...aim, flash: false });
    expect(readoutContent({ idle })).toEqual({ ...idle, flash: false });
  });
});

describe("the readout's flash timing", () => {
  let scope;
  beforeEach(() => {
    vi.useFakeTimers();
    scope = effectScope();
  });
  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  it("a blocked flash holds about 1.6 s over the aim, then the aim returns", () => {
    const state = scope.run(() => useReadoutState(() => idleReadout(2, 1)));
    expect(state.content.value.text).toBe("出口 2 · 在場 1");
    state.setAim({ angle: 270, target: angled, zone: "pad" });
    expect(state.content.value.lead).toBe("前往 ←");
    state.showFlash(blockedReadout({ kind: "dead-end", angle: 270 }));
    expect(FLASH_MS).toBe(1600);
    expect(state.content.value).toMatchObject({ text: DEAD_END_TEXT, tone: "warn", flash: true });
    vi.advanceTimersByTime(FLASH_MS - 1);
    expect(state.content.value.flash).toBe(true);
    vi.advanceTimersByTime(1);
    expect(state.content.value).toMatchObject({ lead: "前往 ←", flash: false });
    state.setAim(null);
    expect(state.content.value.text).toBe("出口 2 · 在場 1");
  });

  it("a new flash restarts the hold", () => {
    const state = scope.run(() => useReadoutState(() => idleReadout(0, 0)));
    state.showFlash({ lead: "a", text: "first", tone: "warn" });
    vi.advanceTimersByTime(1000);
    state.showFlash({ lead: "b", text: "second", tone: "warn" });
    vi.advanceTimersByTime(1000);
    expect(state.content.value.text).toBe("second");
    vi.advanceTimersByTime(600);
    expect(state.content.value.flash).toBe(false);
  });
});

describe("ExplorationReadout", () => {
  it("is a polite live region with a lead and a text", () => {
    const w = mount(ExplorationReadout, { props: { lead: "前往 ←", text: "西部丘陵與谷地", tone: "normal" } });
    const root = w.get('[data-testid="exploration-readout"]');
    expect(root.attributes("aria-live")).toBe("polite");
    expect(w.get('[data-testid="exploration-readout-lead"]').text()).toBe("前往 ←");
    expect(w.get('[data-testid="exploration-readout-text"]').text()).toBe("西部丘陵與谷地");
    expect(root.attributes("data-tone")).toBe("normal");
  });

  it("carries the tone and the flash", () => {
    const w = mount(ExplorationReadout, { props: { lead: "", text: "出口 0 · 在場 0", tone: "quiet" } });
    expect(w.classes()).toContain("exploration-readout--quiet");
    const flashing = mount(ExplorationReadout, { props: { lead: "無法通行", text: "x", tone: "warn", flash: true } });
    expect(flashing.classes()).toEqual(
      expect.arrayContaining(["exploration-readout--warn", "exploration-readout--flash", "exploration-readout--animated"]),
    );
  });

  it("at the off motion level the flash is static", () => {
    const w = mount(ExplorationReadout, { props: { lead: "無法通行", text: "x", tone: "warn", flash: true, motionLevel: "off" } });
    expect(w.classes()).toContain("exploration-readout--flash");
    expect(w.classes()).not.toContain("exploration-readout--animated");
  });
});
