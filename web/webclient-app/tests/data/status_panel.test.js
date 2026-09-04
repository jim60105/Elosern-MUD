import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import StatusPanel from "../../components/StatusPanel.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_MINIMAL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// StatusPanel (H2, webclient-hud-02-status-islands, design D1): the
// `hud-left` island stack. It composes three separately-chromed islands —
// CharacterHead, VitalsTrack, and ConditionChips — and keeps the preserved
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
    wrapper = mount(StatusPanel, {
      props: {
        status: STATUS_PANEL_SAMPLE,
        character: CHARACTER_PANEL_SAMPLE,
        lowHp: false,
        revision: 1,
        epoch: 0,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the head card, the vitals, and the conditions as three sibling islands in fixed order", () => {
    const w = mountPanel();
    const head = w.get('[data-testid="character-head"]');
    const vitals = w.get('[data-testid="vitals-track"]');
    const conditions = w.get('[data-testid="status-panel__conditions"]');
    // The three islands are siblings of the preserved stack root, in the
    // head → vitals → conditions order (design D1).
    expect(head.exists()).toBe(true);
    expect(vitals.exists()).toBe(true);
    expect(conditions.exists()).toBe(true);
    const root = w.get('[data-testid="status-panel"]');
    const children = root.element.children;
    expect(children).toHaveLength(3);
    // The island testids are on the children themselves (not descendants),
    // so assert the attribute on the child element directly.
    expect(children[0].getAttribute("data-testid")).toBe("character-head");
    expect(children[1].getAttribute("data-testid")).toBe("vitals-track");
    expect(children[2].getAttribute("data-testid")).toBe("status-panel__conditions");
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

  it("relocates every pre-change row so no row loses its only home", () => {
    const w = mountPanel();
    // magic_power badge + guild rank/merit + wallet moved to the head card's
    // badge, rank, and wallet lines (design D1/D11); no rank word remains.
    const rank = w.get('[data-testid="character-head__rank"]').text();
    expect(rank).not.toMatch(/學徒|術師|大師|賢者|主宰/);
    expect(rank).toContain("公會 E");
    expect(rank).toContain("功績 140");
    expect(w.get('[data-testid="character-head__wallet"]').text()).toBe("錢包 3,240 銅");
    // The disguise flag moved to the head card's marker.
    expect(w.get('[data-testid="character-head__disguise"]').text()).toBe("目前有偽裝");
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
