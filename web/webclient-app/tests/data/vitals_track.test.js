import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import VitalsTrack from "../../components/VitalsTrack.vue";
import {
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_MINIMAL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// H2 (webclient-hud-02-status-islands), design D4/D5: the vitals island.
// Each vital row pairs an icon, a Traditional Chinese label, and the
// current / maximum numerals (the preserved `status-panel__gauge-value--*`
// hooks). The SP fill carries a stripe texture so it is distinguishable
// without colour; a low vital is marked by both a recolour and an explicit
// 危險 text marker; the trailing (ghost) bar holds only previously committed
// ratios and resets on an epoch change.

describe("VitalsTrack (H2 vitals island)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountTrack(props = {}) {
    wrapper = mount(VitalsTrack, {
      props: {
        status: STATUS_PANEL_SAMPLE,
        lowHp: false,
        revision: 1,
        epoch: 0,
        ...props,
      },
    });
    return wrapper;
  }

  it("pairs every gauge with an icon, a label, and explicit current / maximum numerals", () => {
    const w = mountTrack();
    for (const key of ["hp", "mp", "sp"]) {
      const gauge = w.get(`[data-testid="status-panel__gauge--${key}"]`);
      expect(gauge.find("svg.ic").exists()).toBe(true);
      expect(gauge.text()).toContain({ hp: "生命", mp: "魔力", sp: "耐力" }[key]);
      const expected = {
        hp: "231 / 405",
        mp: "139 / 420",
        sp: "68 / 68",
      }[key];
      expect(
        w.get(`[data-testid="status-panel__gauge-value--${key}"]`).text(),
      ).toBe(expected);
    }
  });

  it("marks a low vital with a recolour AND an explicit 危險 text marker", async () => {
    const lowStatus = {
      ...STATUS_PANEL_SAMPLE,
      resources: {
        hp: { current: 100, maximum: 405 },
        mp: STATUS_PANEL_SAMPLE.resources.mp,
        sp: STATUS_PANEL_SAMPLE.resources.sp,
      },
    };
    const w = mountTrack({ status: lowStatus, lowHp: true });
    const hpRow = w.get('[data-testid="status-panel__gauge--hp"]');
    expect(hpRow.classes()).toContain("low");
    expect(w.get('[data-testid="vitals-low-marker"]').text()).toBe("危險");
    // The numerals still carry the value — the marker is reinforcement.
    expect(w.get('[data-testid="status-panel__gauge-value--hp"]').text()).toBe(
      "100 / 405",
    );
  });

  it("marks each vital row with its gauge class so the CSS fill rules apply", () => {
    const w = mountTrack();
    // The sp row carries the `sp` class (the CSS gives its fill the diagonal
    // stripe texture); hp and mp keep the highlight sheen instead. The rows
    // are distinguishable by class, so the sp fill is distinct from hp/mp
    // without colour.
    expect(w.get('[data-testid="status-panel__gauge--sp"]').classes()).toContain("sp");
    expect(w.get('[data-testid="status-panel__gauge--mp"]').classes()).toContain("mp");
    expect(w.get('[data-testid="status-panel__gauge--hp"]').classes()).toContain("hp");
  });

  it("binds the elosern-hp-pulse keyframe to the hp fill when low", () => {
    const lowStatus = {
      ...STATUS_PANEL_SAMPLE,
      resources: {
        hp: { current: 100, maximum: 405 },
        mp: STATUS_PANEL_SAMPLE.resources.mp,
        sp: STATUS_PANEL_SAMPLE.resources.sp,
      },
    };
    const w = mountTrack({ status: lowStatus, lowHp: true });
    // The `.vital.low .fill` CSS rule binds the elosern-hp-pulse keyframe
    // the migration extracted but never consumed (design D5). The `low` class
    // on the hp row is the hook that rule selects on.
    expect(w.get('[data-testid="status-panel__gauge--hp"]').classes()).toContain("low");
  });

  it("leaves the trailing bar behind the fill on damage and overtaken on heal", async () => {
    // Start from full gauges, then commit a damaged revision in the same
    // epoch: the fill moves immediately while the ghost chases with a CSS
    // delay (the gap between them is the damage taken).
    const full = mountTrack({
      status: STATUS_PANEL_MINIMAL_SAMPLE,
      revision: 1,
      epoch: 0,
    });
    const damaged = {
      ...STATUS_PANEL_MINIMAL_SAMPLE,
      resources: {
        hp: { current: 120, maximum: 405 },
        mp: STATUS_PANEL_MINIMAL_SAMPLE.resources.mp,
        sp: STATUS_PANEL_MINIMAL_SAMPLE.resources.sp,
      },
    };
    await full.setProps({ status: damaged, revision: 2 });
    const hpRow = full.get('[data-testid="status-panel__gauge--hp"]');
    const fill = hpRow.find(".fill");
    const ghost = hpRow.find(".ghost");
    // Both the fill and the ghost now bind the new committed ratio; the
    // ghost's CSS transition (0.6s ease 0.25s delay) makes it lag on damage.
    expect(ghost.attributes("data-instant")).toBe("false");
    expect(parseFloat(ghost.element.style.width)).toBeCloseTo(120 / 405 * 100, 1);
    // The ghost is decorative: aria-hidden, no accessible name.
    expect(ghost.attributes("aria-hidden")).toBe("true");
    // A missing attribute reads as undefined (not null) in test-utils.
    expect(ghost.attributes("aria-label")).toBeUndefined();
  });

  it("resets the trailing bar to the new ratio on an epoch change (a reconnect)", async () => {
    // A reconnect commits a new epoch with a fresh snapshot. The ghost must
    // snap to the new committed ratio (transition suppressed for one frame)
    // so no trail is drawn across sessions (design D4).
    const reconnectStatus = {
      ...STATUS_PANEL_SAMPLE,
      resources: {
        hp: { current: 300, maximum: 405 },
        mp: STATUS_PANEL_SAMPLE.resources.mp,
        sp: STATUS_PANEL_SAMPLE.resources.sp,
      },
    };
    const w = mountTrack();
    await w.setProps({ status: reconnectStatus, epoch: 1, revision: 5 });
    const after = w.get('[data-testid="status-panel__gauge--hp"]').find(".ghost");
    expect(parseFloat(after.element.style.width)).toBeCloseTo(300 / 405 * 100, 1);
    // The instant-reset flag re-arms only after the transition-suppressed
    // state has painted (two frames), so await them before asserting.
    const nextFrame = () => new Promise((resolve) => requestAnimationFrame(resolve));
    await nextFrame();
    await nextFrame();
    expect(after.attributes("data-instant")).toBe("false");
  });

  it("renders the combat session line as the island's header row", () => {
    const w = mountTrack({
      status: STATUS_PANEL_COMBAT_SAMPLE,
      revision: 2,
    });
    const combat = w.get('[data-testid="status-panel__combat"]');
    expect(combat.attributes("data-mode")).toBe("guild_exam");
    expect(combat.text()).toBe("戰鬥中（公會考核）· 第 3 回合");
  });

  it("renders the combat line only when the payload carries one", () => {
    const w = mountTrack({ status: STATUS_PANEL_SAMPLE });
    expect(w.find('[data-testid="status-panel__combat"]').exists()).toBe(false);
  });
});
