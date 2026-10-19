// render-equipment-breakdown-webclient (task 3.2): the breakdown-rendering
// contract for the manifest components. The chip block is a pure
// projection of the v5 payload — payload order, verbatim names, kind-
// formatted signed amounts, ALL layers (≤ 16) rendered, no sorting, no
// recomputation, no truncation; layer-free rows render no breakdown element
// at all. Equipment adjustment strings print verbatim where equipment is
// listed (the bag tab's per-member server deltas). An
// unknown layer source/kind is wire-rejected; the neutral 其他 chip is
// direct-render defense only, proven here by mounting hand-built props.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import CharacterStatusDrawer from "../../components/CharacterStatusDrawer.vue";
import PartyBagTab from "../../components/PartyBagTab.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../../stories/fixtures.js";
import { PARTY_BAG_HOLDINGS_EQUIPMENT, PARTY_BAG_INVENTORY_SAMPLE } from "../../stories/fixtures/party_panels.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";

// A trait row builder with the closed breakdown shape.
function trait(overrides) {
  return Object.assign(
    { key: "defense", label: "防禦", base: 10, current: 12, max: null, effective: 12, layers: [] },
    overrides,
  );
}

function characterWith(traits, equipment) {
  return {
    ...CHARACTER_PANEL_SAMPLE,
    traits: traits ?? CHARACTER_PANEL_SAMPLE.traits,
    equipment: equipment ?? CHARACTER_PANEL_SAMPLE.equipment,
  };
}

function mountDrawer(props = {}) {
  return mount(CharacterStatusDrawer, {
    props: {
      // The gauge-layer guard only attaches the character breakdown when both
      // panels name the same member, so this suite pins the status actor to
      // the character fixture's member_id.
      status: {
        ...STATUS_PANEL_SAMPLE,
        actor: {
          ...STATUS_PANEL_SAMPLE.actor,
          identity: String(CHARACTER_PANEL_SAMPLE.member_id),
        },
      },
      character: CHARACTER_PANEL_SAMPLE,
      lowHp: false,
      ...props,
    },
  });
}

describe("CharacterStatusDrawer breakdown chips", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("renders one chip per layer in payload order with verbatim names and kind-formatted amounts", () => {
    wrapper = mountDrawer({
      character: characterWith([
        trait({
          layers: [
            { source: "skill", name: "防衛本能（2/3）", kind: "mult", amount: 1.5 },
            { source: "condition", name: "護盾", kind: "flat", amount: 4 },
            { source: "equipment", name: "壁衛板甲", kind: "flat", amount: -2 },
          ],
        }),
      ]),
    });
    const chips = wrapper.findAll('[data-testid^="character-status-drawer__layer--defense--"]');
    expect(chips).toHaveLength(3);
    // Payload order, verbatim names, formatting by kind only (re-signed for
    // display, never recomputed): mult ×1.2-style, flat ±N, pct ±N%.
    expect(chips[0].text()).toBe("防衛本能（2/3）×1.5");
    expect(chips[0].attributes("data-source")).toBe("skill");
    expect(chips[1].text()).toBe("護盾+4");
    expect(chips[1].attributes("data-source")).toBe("condition");
    expect(chips[2].text()).toBe("壁衛板甲−2");
    expect(chips[2].attributes("data-source")).toBe("equipment");
    // The value line keeps the existing static text (total-display field).
    expect(
      wrapper.get('[data-testid="character-status-drawer__trait--defense"]').text(),
    ).toContain("12");
  });

  it("strips mult trailing zeros and formats pct with the U+2212 minus", () => {
    wrapper = mountDrawer({
      character: characterWith([
        trait({
          layers: [
            { source: "skill", name: "巨型化", kind: "mult", amount: 2.5 },
            { source: "condition", name: "高露出", kind: "pct", amount: -15 },
            { source: "skill", name: "硬皮", kind: "mult", amount: 1.0 },
            // The wire accepts signed non-zero mult factors; the factor
            // sign is projection, not recomputation (server prose keeps it).
            { source: "skill", name: "腐蝕", kind: "mult", amount: -1.2 },
          ],
        }),
      ]),
    });
    const chips = wrapper.findAll('[data-testid^="character-status-drawer__layer--defense--"]');
    expect(chips[0].text()).toBe("巨型化×2.5");
    expect(chips[1].text()).toBe("高露出−15%");
    expect(chips[2].text()).toBe("硬皮×1");
    expect(chips[3].text()).toBe("腐蝕×−1.2");
  });

  it("renders ALL 16 layers at the payload bound with no truncation", () => {
    const layers = Array.from({ length: 16 }, (_, i) => ({
      source: "equipment",
      name: `層${i + 1}`,
      kind: "flat",
      amount: i + 1,
    }));
    wrapper = mountDrawer({ character: characterWith([trait({ layers })]) });
    const chips = wrapper.findAll('[data-testid^="character-status-drawer__layer--defense--"]');
    expect(chips).toHaveLength(16);
    expect(chips[15].text()).toBe("層16+16");
    // Payload order preserved (no sorting).
    expect(chips.map((c) => c.text())).toEqual(
      layers.map((l) => `${l.name}+${l.amount}`),
    );
  });

  it("renders no breakdown element at all for a layer-free row", () => {
    wrapper = mountDrawer({ character: characterWith([trait({ layers: [] })]) });
    expect(
      wrapper.find('[data-testid="character-status-drawer__layers--defense"]').exists(),
    ).toBe(false);
    expect(
      wrapper.find('[data-testid^="character-status-drawer__layer--defense"]').exists(),
    ).toBe(false);
    // The value row itself renders unchanged.
    expect(wrapper.find('[data-testid="character-status-drawer__trait--defense"]').exists()).toBe(true);
  });

  it("keeps the fixture's 16-layer defense row fully rendered", () => {
    // The showcase fixture itself must sit at the bound and render every
    // layer (the D4 fixture contract).
    wrapper = mountDrawer();
    const layers = CHARACTER_PANEL_SAMPLE.traits.find((row) => row.key === "defense").layers;
    expect(layers).toHaveLength(16);
    expect(
      wrapper.findAll('[data-testid^="character-status-drawer__layer--defense--"]'),
    ).toHaveLength(16);
  });

  it("attaches gauge chips to the maximum only when both panels agree on it", () => {
    // Agreement: the hp trait row's max equals status.resources.hp.maximum.
    const hpTrait = trait({
      key: "hp",
      label: "生命",
      base: 390,
      current: 231,
      max: STATUS_PANEL_SAMPLE.resources.hp.maximum,
      effective: STATUS_PANEL_SAMPLE.resources.hp.maximum,
      layers: [{ source: "equipment", name: "壁衛板甲", kind: "flat", amount: 15 }],
    });
    wrapper = mountDrawer({
      character: characterWith(CHARACTER_PANEL_SAMPLE.traits.map((row) => (row.key === "hp" ? hpTrait : row))),
    });
    const chip = wrapper.get('[data-testid="character-status-drawer__layer--hp--0"]');
    expect(chip.text()).toBe("壁衛板甲+15");
    // The existing gauge text stays byte-identical (chips never replace it).
    expect(
      wrapper.get('[data-testid="character-status-drawer__vital-value--hp"]').text(),
    ).toBe("231 / 405");
    wrapper.unmount();

    // Disagreement (a stale pair): no breakdown element on the vital row.
    const disagree = trait({
      ...hpTrait,
      max: STATUS_PANEL_SAMPLE.resources.hp.maximum + 1,
      effective: STATUS_PANEL_SAMPLE.resources.hp.maximum + 1,
    });
    wrapper = mountDrawer({
      character: characterWith(CHARACTER_PANEL_SAMPLE.traits.map((row) => (row.key === "hp" ? disagree : row))),
    });
    expect(
      wrapper.find('[data-testid="character-status-drawer__layers--hp"]').exists(),
    ).toBe(false);
    wrapper.unmount();

    // A static trait row (null max) never attaches to a gauge.
    const staticRow = trait({ key: "hp", label: "生命", current: 231, max: null, effective: 231 });
    wrapper = mountDrawer({
      character: characterWith(CHARACTER_PANEL_SAMPLE.traits.map((row) => (row.key === "hp" ? staticRow : row))),
    });
    expect(
      wrapper.find('[data-testid="character-status-drawer__layers--hp"]').exists(),
    ).toBe(false);
  });

  it("renders no gauge chips when the character panel is unavailable", () => {
    wrapper = mountDrawer({
      character: { schema_version: 5, available: false, kind: "character", reason: { code: "no_puppet", message: "你已離開角色" } },
    });
    for (const key of ["hp", "mp", "sp"]) {
      expect(wrapper.find(`[data-testid="character-status-drawer__layers--${key}"]`).exists()).toBe(false);
    }
    // The vitals still render from the status panel.
    expect(wrapper.find('[data-testid="character-status-drawer__vitals"]').exists()).toBe(true);
  });

  it("renders a neutral 其他 chip for unknown enums while the value line stays correct", () => {
    // Direct-render defense ONLY (task 1.4): the wire validators reject an
    // unknown source/kind; a hand-built props object must still render a
    // text-bearing neutral chip and an untouched value line — for an
    // unknown source OR an unknown kind (design D1).
    wrapper = mountDrawer({
      character: characterWith([
        trait({
          layers: [
            { source: "divine", name: "神恩", kind: "flat", amount: 3 },
            { source: "skill", name: "未知形態", kind: "omega", amount: 7 },
          ],
        }),
      ]),
    });
    const chips = wrapper.findAll('[data-testid^="character-status-drawer__layer--defense--"]');
    expect(chips).toHaveLength(2);
    // Unknown source → 其他 marker text (never colour alone).
    expect(chips[0].text()).toContain("（其他）");
    expect(chips[0].classes().join(" ")).toContain("character-status-drawer__layer--other");
    // Unknown kind → neutral 其他 chip too (an unrecognised formatting
    // rule is not a trusted skill chip) with the signed verbatim amount.
    expect(chips[1].text()).toBe("未知形態（其他）+7");
    expect(chips[1].classes().join(" ")).toContain("character-status-drawer__layer--other");
    // The value line is untouched.
    expect(wrapper.get('[data-testid="character-status-drawer__trait--defense"]').text()).toContain("12");
  });
});

describe("PartyBagTab adjustment rendering (webclient-party-bag-retire)", () => {
  // The bag tab replaced the doll and the inventory inspector: an equipment
  // row's adjustment strings are the server's `item_holdings` delta changes,
  // printed verbatim per member (label and signed amount with a shape
  // prefix), never recomputed or reordered.
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it("prints every member's server delta in payload order", () => {
    wrapper = mount(PartyBagTab, {
      props: {
        partyInventory: PARTY_BAG_INVENTORY_SAMPLE,
        itemHoldings: PARTY_BAG_HOLDINGS_EQUIPMENT,
        members: [
          { id: 42, name: "影行者" },
          { id: 101, name: "蕾娜" },
          { id: 102, name: "幽" },
          { id: 103, name: "蓋文" },
        ],
        memberId: 101,
      },
    });
    const cell = (id) => wrapper.get(`[data-testid="holdings-strip__cell--${id}"]`);
    expect(cell(42).findAll(".holdings-strip__change").map((node) => node.text())).toEqual(["▲ 攻擊 +6"]);
    expect(cell(101).findAll(".holdings-strip__change").map((node) => node.text())).toEqual(["▼ 攻擊 −2", "▲ 敏捷 +3"]);
    expect(cell(102).get('[data-testid="holdings-strip__delta-reason"]').text()).toBe("幽無法使用這類武器。");
  });
});

describe("v5-only wire acceptance (Vue store path)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  function openSession() {
    const store = useElosernStore();
    store.setSender(fx.createFakeSender());
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    expect(store.receive(1, "ui_snapshot", [fx.snapshot()], {}).accepted).toBe(true);
    return store;
  }

  it("commits a v5 character panel and rejects a v4 one", () => {
    const store = openSession();
    const v5 = { ...CHARACTER_PANEL_SAMPLE };
    expect(
      store.receive(1, "ui_update", [fx.update({ revision: 2, panels: { character: v5 } })], {}).accepted,
    ).toBe(true);

    const v4 = { ...CHARACTER_PANEL_SAMPLE, schema_version: 4 };
    const result = store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 3, panels: { character: v4 } })],
      {},
    );
    expect(result.accepted).toBe(false);
    expect(result.reason).toBe("invalid");
  });

  it("rejects a layer with a source outside the closed set on the wire", () => {
    const store = openSession();
    const smuggled = {
      ...CHARACTER_PANEL_SAMPLE,
      traits: CHARACTER_PANEL_SAMPLE.traits.map((row) =>
        row.key === "defense"
          ? { ...row, layers: [{ source: "divine", name: "神恩", kind: "flat", amount: 3 }] }
          : row,
      ),
    };
    const result = store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, panels: { character: smuggled } })],
      {},
    );
    expect(result.accepted).toBe(false);
    expect(result.reason).toBe("invalid");
  });
});
