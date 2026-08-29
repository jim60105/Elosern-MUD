// render-equipment-breakdown-webclient (task 3.2): the breakdown-rendering
// contract for the three manifest components. The chip block is a pure
// projection of the v5 payload — payload order, verbatim names, kind-
// formatted signed amounts, ALL layers (≤ 16) rendered, no sorting, no
// recomputation, no truncation; layer-free rows render no breakdown element
// at all. Equipment adjustment strings print verbatim where equipment is
// listed (doll rows and the inventory inspector joined on item_key). An
// unknown layer source/kind is wire-rejected; the neutral 其他 chip is
// direct-render defense only, proven here by mounting hand-built props.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import CharacterStatusDrawer from "../../components/CharacterStatusDrawer.vue";
import EquipmentDoll from "../../components/EquipmentDoll.vue";
import InventoryPanel from "../../components/InventoryPanel.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../../stories/fixtures.js";
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
      status: STATUS_PANEL_SAMPLE,
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
            { source: "equipment", name: "騎士全套板甲", kind: "flat", amount: -2 },
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
    expect(chips[2].text()).toBe("騎士全套板甲−2");
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
          ],
        }),
      ]),
    });
    const chips = wrapper.findAll('[data-testid^="character-status-drawer__layer--defense--"]');
    expect(chips[0].text()).toBe("巨型化×2.5");
    expect(chips[1].text()).toBe("高露出−15%");
    expect(chips[2].text()).toBe("硬皮×1");
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
      layers: [{ source: "equipment", name: "騎士全套板甲", kind: "flat", amount: 15 }],
    });
    wrapper = mountDrawer({
      character: characterWith(CHARACTER_PANEL_SAMPLE.traits.map((row) => (row.key === "hp" ? hpTrait : row))),
    });
    const chip = wrapper.get('[data-testid="character-status-drawer__layer--hp--0"]');
    expect(chip.text()).toBe("騎士全套板甲+15");
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
    // text-bearing neutral chip and an untouched value line.
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
    // Unknown kind → signed verbatim amount, source tint kept.
    expect(chips[1].text()).toBe("未知形態+7");
    // The value line is untouched.
    expect(wrapper.get('[data-testid="character-status-drawer__trait--defense"]').text()).toContain("12");
  });
});

describe("EquipmentDoll adjustment rendering", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("prints the armor adjustment verbatim in the description row", () => {
    wrapper = mount(EquipmentDoll, { props: { character: CHARACTER_PANEL_SAMPLE } });
    // The U+2212 minus must survive verbatim (no ASCII replacement).
    expect(
      wrapper.get('[data-testid="equipment-doll__adjustment--armor"]').text(),
    ).toBe("攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15");
  });

  it("renders nothing for an empty adjustment", () => {
    wrapper = mount(EquipmentDoll, { props: { character: CHARACTER_PANEL_SAMPLE } });
    expect(wrapper.find('[data-testid="equipment-doll__adjustment--weapon_main"]').exists()).toBe(false);
  });

  it("prints accessory adjustments verbatim", () => {
    wrapper = mount(EquipmentDoll, { props: { character: CHARACTER_PANEL_SAMPLE } });
    expect(
      wrapper.get('[data-testid="equipment-doll__adjustment--sister_vestments"]').text(),
    ).toBe("治療 +10%");
  });

  it("prints duplicate and other-slot row adjustments verbatim", () => {
    wrapper = mount(EquipmentDoll, {
      props: {
        character: {
          ...CHARACTER_PANEL_SAMPLE,
          equipment: [
            { slot: "armor", item_key: "leather_armor", display_name: "皮甲", adjustment: "防禦 +3" },
            { slot: "armor", item_key: "spare_mail", display_name: "備用鏈甲", adjustment: "防禦 +5" },
            { slot: "mount", item_key: "mount_ash", display_name: "灰驛", adjustment: "敏捷 +10%" },
          ],
        },
      },
    });
    expect(wrapper.get('[data-testid="equipment-doll__adjustment--spare_mail"]').text()).toBe("防禦 +5");
    expect(wrapper.get('[data-testid="equipment-doll__adjustment--mount_ash"]').text()).toBe("敏捷 +10%");
  });
});

describe("InventoryPanel joined adjustment", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  function mountPanel(props = {}) {
    wrapper = mount(InventoryPanel, {
      props: {
        services: SERVICES_PANEL_SAMPLE,
        character: CHARACTER_PANEL_SAMPLE,
        wallet: CHARACTER_PANEL_SAMPLE.wallet,
        ...props,
      },
    });
    return wrapper;
  }

  function hover(key) {
    return wrapper.get(`[data-testid="inventory-panel__tile--${key}"]`).trigger("focus");
  }

  it("joins the same server string on item_key for an equipped bag row", async () => {
    // A bag listing whose row shares the character row's item_key.
    const services = {
      ...SERVICES_PANEL_SAMPLE,
      inventory: {
        ...SERVICES_PANEL_SAMPLE.inventory,
        rows: [
          { item_key: "knight_platemail", display_name: "騎士全套板甲", held: 1, equipped: true, presentation: null, action: null },
        ],
      },
    };
    mountPanel({ services });
    await hover("knight_platemail");
    expect(
      wrapper.get('[data-testid="inventory-panel__inspector-adjustment"]').text(),
    ).toBe("攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15");
  });

  it("renders no adjustment line for a bag-only item or an empty string", async () => {
    const services = {
      ...SERVICES_PANEL_SAMPLE,
      inventory: {
        ...SERVICES_PANEL_SAMPLE.inventory,
        rows: [
          { item_key: "loose_rope", display_name: "繩索", held: 1, equipped: false, presentation: null, action: null },
        ],
      },
    };
    mountPanel({ services });
    await hover("loose_rope");
    expect(wrapper.find('[data-testid="inventory-panel__inspector-adjustment"]').exists()).toBe(false);
    // An equipped item whose character row carries an EMPTY adjustment.
    const empty = {
      ...SERVICES_PANEL_SAMPLE,
      inventory: {
        ...SERVICES_PANEL_SAMPLE.inventory,
        rows: [
          { item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true, presentation: null, action: null },
        ],
      },
    };
    wrapper.unmount();
    mountPanel({ services: empty });
    await hover("short_sword_lost");
    expect(wrapper.find('[data-testid="inventory-panel__inspector-adjustment"]').exists()).toBe(false);
  });

  it("renders no adjustment line when the character panel is unavailable", async () => {
    const services = {
      ...SERVICES_PANEL_SAMPLE,
      inventory: {
        ...SERVICES_PANEL_SAMPLE.inventory,
        rows: [
          { item_key: "knight_platemail", display_name: "騎士全套板甲", held: 1, equipped: true, presentation: null, action: null },
        ],
      },
    };
    mountPanel({
      services,
      character: { schema_version: 5, available: false, kind: "character", reason: { code: "no_puppet", message: "你已離開角色" } },
    });
    await hover("knight_platemail");
    expect(wrapper.find('[data-testid="inventory-panel__inspector-adjustment"]').exists()).toBe(false);
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
