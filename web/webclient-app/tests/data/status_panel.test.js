import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import VitalsTrack from "../../components/VitalsTrack.vue";
import StatusPanel from "../../components/StatusPanel.vue";
import {
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_MINIMAL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// StatusPanel (H2, webclient-hud-02-status-islands, design D1): the
// `vitals` anchor's island stack. It composes two separately-chromed islands —
// VitalsTrack and ConditionChips — and keeps the preserved
// `data-testid="status-panel"` root and the three
// `status-panel__gauge-value--{hp,mp,sp}` hooks (now carried by the
// VitalsTrack rows), so the combat and transport-mount browser journeys
// need no edit.

describe("StatusPanel (H2 island-stack root)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPanel(props = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(StatusPanel, {
      attachTo: host,
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

  it("renders the vitals and the conditions as two sibling islands in fixed order", () => {
    const w = mountPanel();
    const vitals = w.get('[data-testid="vitals-track"]');
    const conditions = w.get('[data-testid="status-panel__conditions"]');
    expect(vitals.exists()).toBe(true);
    expect(conditions.exists()).toBe(true);
    const root = w.get('[data-testid="status-panel"]');
    const children = root.element.children;
    expect(children).toHaveLength(2);
    expect(children[0].getAttribute("data-testid")).toBe("vitals-track");
    expect(children[1].getAttribute("data-testid")).toBe("status-panel__conditions");
  });

  it("visible: false gives a root with display: none that is still in the DOM", () => {
    const w = mountPanel({ visible: false });
    const root = w.get('[data-testid="status-panel"]');
    expect(root.isVisible()).toBe(false);
    expect(root.element.style.display).toBe("none");
  });

  it("the trailing-bar memory survives a hidden-then-shown revision", async () => {
    const initialStatus = {
      ...STATUS_PANEL_SAMPLE,
      resources: {
        hp: { current: 100, maximum: 100 },
        mp: { current: 50, maximum: 50 },
        sp: { current: 40, maximum: 40 },
      },
    };
    const w = mountPanel({ status: initialStatus, visible: false, revision: 1, epoch: 1 });
    expect(w.get('[data-testid="status-panel"]').isVisible()).toBe(false);

    const damagedStatus = {
      ...STATUS_PANEL_SAMPLE,
      resources: {
        hp: { current: 80, maximum: 100 },
        mp: { current: 50, maximum: 50 },
        sp: { current: 40, maximum: 40 },
      },
    };
    await w.setProps({ status: damagedStatus, visible: true, revision: 2, epoch: 1 });
    expect(w.get('[data-testid="status-panel"]').element.style.display).not.toBe("none");
    expect(w.findComponent(VitalsTrack).exists()).toBe(true);
    const ghost = w.get('[data-testid="status-panel__gauge--hp"] .ghost');
    expect(ghost.attributes("data-instant")).toBe("false");
    expect(ghost.element.style.width).toBe("80%");
  });

  it("keeps the preserved root testid and the three gauge-value hooks", () => {
    const w = mountPanel();
    expect(w.get('[data-testid="status-panel"]').exists()).toBe(true);
    for (const key of ["hp", "mp", "sp"]) {
      const value = w.get(`[data-testid="status-panel__gauge-value--${key}"]`).text();
      const expected = {
        hp: "231 / 405",
        mp: "139 / 420",
        sp: "68 / 68",
      }[key];
      expect(value).toBe(expected);
    }
  });

  it("renders both condition chips when visible with beneficial and harmful conditions", () => {
    const status = {
      ...STATUS_PANEL_SAMPLE,
      conditions: [
        { code: "defense_instinct_defense_bonus", label: "防禦本能", severity: "beneficial" },
        { code: "poison", label: "中毒", severity: "harmful" },
      ],
    };
    const w = mountPanel({ status, visible: true });
    const chips = w.findAll('[data-testid^="status-panel__condition--"]');
    expect(chips).toHaveLength(2);
  });

  it("moves the combat session line into the vitals island's header row", () => {
    const w = mountPanel({ status: STATUS_PANEL_COMBAT_SAMPLE });
    const combat = w.get('[data-testid="status-panel__combat"]');
    expect(combat.attributes("data-mode")).toBe("guild_exam");
    expect(combat.text()).toBe("戰鬥中（公會考核）· 第 3 回合");
  });

  it("renders no conditions island when conditions are empty", () => {
    const w = mountPanel({ status: STATUS_PANEL_MINIMAL_SAMPLE });
    expect(w.find('[data-testid="status-panel__conditions"]').exists()).toBe(false);
    expect(w.find('[data-testid="status-panel__conditions-empty"]').exists()).toBe(false);
  });

  it("invents no intimate/adult block (no backing field, not mocked)", () => {
    const w = mountPanel();
    for (const word of ["親密", "興奮", "濕潤", "羞恥", "高潮", "露出部位"]) {
      expect(w.text()).not.toContain(word);
    }
  });
});
