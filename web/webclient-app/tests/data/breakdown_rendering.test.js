// render-equipment-breakdown-webclient (task 3.2), retargeted by
// webclient-party-status-tab: the breakdown-rendering contract for the
// manifest components. The party window's 狀態 waterfall is a pure
// projection of the v9 payload — payload order, verbatim names, kind-
// formatted signed amounts, ALL layers (≤ 16) rendered, no sorting, no
// recomputation, no truncation; a layer-free trait renders only its base and
// effective steps. Equipment adjustment strings print verbatim where
// equipment is listed (the bag tab's per-member server deltas). An unknown
// layer source/kind is wire-rejected; the neutral 其他 step is direct-render
// defense only, proven here by mounting hand-built props.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import PartyBagTab from "../../components/PartyBagTab.vue";
import PartyStatusTab from "../../components/PartyStatusTab.vue";
import { CHARACTER_PANEL_SAMPLE, PARTY_PANEL_EMPTY_SAMPLE } from "../../stories/fixtures.js";
import { PARTY_BAG_HOLDINGS_EQUIPMENT, PARTY_BAG_INVENTORY_SAMPLE } from "../../stories/fixtures/party_panels.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";

const COMMANDER = PARTY_PANEL_EMPTY_SAMPLE.slots[0];

// A trait row builder with the closed breakdown shape.
function trait(overrides) {
  return Object.assign(
    { key: "defense", label: "防禦", base: 10, current: 12, max: null, effective: 12, layers: [] },
    overrides,
  );
}

function characterWith(traits) {
  return { ...CHARACTER_PANEL_SAMPLE, traits: traits ?? CHARACTER_PANEL_SAMPLE.traits };
}

function mountTab(character = CHARACTER_PANEL_SAMPLE) {
  return mount(PartyStatusTab, { props: { member: COMMANDER, character, initialTrait: "defense" } });
}

const steps = (wrapper) => wrapper.findAll('[data-testid^="party-status-tab__layer--"]');
const stepText = (node) =>
  `${node.find(".party-status-tab__step-name").element.firstChild.textContent}${node.find(".party-status-tab__amt").text()}`;

describe("PartyStatusTab breakdown waterfall", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("renders one step per layer in payload order with verbatim names and kind-formatted amounts", () => {
    wrapper = mountTab(
      characterWith([
        trait({
          layers: [
            { source: "skill", name: "防衛本能（2/3）", kind: "mult", amount: 1.5 },
            { source: "condition", name: "護盾", kind: "flat", amount: 4 },
            { source: "equipment", name: "壁衛板甲", kind: "flat", amount: -2 },
          ],
        }),
      ]),
    );
    const rows = steps(wrapper);
    expect(rows.map(stepText)).toEqual(["防衛本能（2/3）×1.5", "護盾+4", "壁衛板甲−2"]);
    expect(rows.map((node) => node.attributes("data-source"))).toEqual(["skill", "condition", "equipment"]);
    // The base and the effective total stay the committed values.
    expect(wrapper.get('[data-testid="party-status-tab__step--base"]').text()).toContain("10");
    expect(wrapper.get('[data-testid="party-status-tab__step--total"]').text()).toContain("12");
  });

  it("strips mult trailing zeros and formats pct with the U+2212 minus", () => {
    wrapper = mountTab(
      characterWith([
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
    );
    expect(steps(wrapper).map(stepText)).toEqual(["巨型化×2.5", "高露出−15%", "硬皮×1", "腐蝕×−1.2"]);
  });

  it("renders ALL 16 layers at the payload bound with no truncation", () => {
    const layers = Array.from({ length: 16 }, (_, i) => ({ source: "equipment", name: `層${i + 1}`, kind: "flat", amount: i + 1 }));
    wrapper = mountTab(characterWith([trait({ layers })]));
    const rows = steps(wrapper);
    expect(rows).toHaveLength(16);
    expect(rows.map(stepText)).toEqual(layers.map((l) => `${l.name}+${l.amount}`));
  });

  it("renders only the base and effective steps for a layer-free trait", () => {
    wrapper = mountTab(characterWith([trait({ layers: [] })]));
    expect(steps(wrapper)).toHaveLength(0);
    expect(wrapper.findAll('[data-testid="party-status-tab__waterfall"] > li')).toHaveLength(2);
  });

  it("keeps the fixture's 16-layer defense row fully rendered", () => {
    // The showcase fixture itself sits at the bound and renders every layer.
    wrapper = mountTab();
    const layers = CHARACTER_PANEL_SAMPLE.traits.find((row) => row.key === "defense").layers;
    expect(layers).toHaveLength(16);
    expect(steps(wrapper)).toHaveLength(16);
  });

  it("decomposes no gauge: the gauges render from the party row only", () => {
    wrapper = mountTab();
    // The hp trait carries a layer, but gauges are not trait rows.
    expect(CHARACTER_PANEL_SAMPLE.traits.find((row) => row.key === "hp").layers.length).toBeGreaterThan(0);
    expect(wrapper.find('[data-testid="party-status-tab__trait--hp"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="party-status-tab__gauge--hp"]').text()).toContain(`${COMMANDER.hp_current} / ${COMMANDER.hp_maximum}`);
  });

  it("renders a neutral 其他 step for unknown enums while the totals stay correct", () => {
    // Direct-render defense ONLY: the wire validators reject an unknown
    // source/kind; a hand-built props object must still render a
    // text-bearing neutral step — for an unknown source OR an unknown kind.
    wrapper = mountTab(
      characterWith([
        trait({
          layers: [
            { source: "divine", name: "神恩", kind: "flat", amount: 3 },
            { source: "skill", name: "未知形態", kind: "omega", amount: 7 },
          ],
        }),
      ]),
    );
    const rows = steps(wrapper);
    expect(rows).toHaveLength(2);
    expect(rows[0].classes()).toContain("party-status-tab__step--other");
    expect(wrapper.get('[data-testid="party-status-tab__layer-source--0"]').text()).toBe("其他 ‧ 固定值");
    expect(rows[1].classes()).toContain("party-status-tab__step--other");
    expect(wrapper.get('[data-testid="party-status-tab__layer-source--1"]').text()).toBe("其他 ‧ 其他");
    expect(stepText(rows[1])).toBe("未知形態+7");
    expect(wrapper.get('[data-testid="party-status-tab__effective--defense"]').text()).toBe("12");
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
    const blocked = cell(102).get('[data-testid="holdings-strip__delta"]');
    expect(blocked.text()).toBe("無法裝備");
    expect(blocked.attributes("data-reason-code")).toBe("malformed_equipment");
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
