// H3 (task 5.10): per-pane-kind Vitest — for each pane kind the rendered
// rows equal the committed frame's items in order, a disabled row keeps
// focus (and its reason stays readable), and no pane renders a field the
// payload does not carry. Mounts DockMenu at depth 2 (the pane depth).

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import DockMenu from "../../components/DockMenu.vue";

// Fixtures are hoisted (arrays of objects) to dodge the V8/Node 24 parser
// quirk on nested object-in-array literals.

describe("DockMenu per-pane-kind (task 5.10)", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountMenu(items, idPrefix = "combat-row") {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(DockMenu, {
      attachTo: host,
      props: { items, depth: 2, idPrefix },
    });
    return wrapper;
  }

  // A small helper: assert the rendered rows equal the committed items in
  // order (the `data-item-key` identity, the preserved row ids).
  function assertRowsInOrder(w, items, idPrefix) {
    const cells = w.findAll("[data-item-key]");
    expect(cells).toHaveLength(items.length);
    expect(cells.map((c) => c.attributes("data-item-key"))).toEqual(
      items.map((i) => i.key),
    );
    expect(cells.map((c) => c.attributes("id"))).toEqual(
      items.map((_, idx) => `${idPrefix}-${idx}`),
    );
  }

  const cardItems = [
    { key: "action-explore.talk_freeform", label: "交談", enabled: true, action_id: "explore.talk_freeform" },
    { key: "action-options.dismiss", label: "✕ 清除建議", enabled: true, action_id: "options.dismiss" },
  ];
  const skillItems = [
    { key: "skill-fire", label: "火球術", enabled: true, action_id: "open-skill", cost_text: "MP 20" },
    { key: "skill-heal", label: "治癒", enabled: false, action_id: "open-skill", cost_text: "MP 8", disabled_reason: { code: "cooldown", message: "冷卻中" } },
  ];
  const targetItems = [
    { key: "target-a", label: "ゴブリン", enabled: true, action_id: "toggle-target", selected: true },
    { key: "target-b", label: "オーク", enabled: true, action_id: "toggle-target", selected: false },
  ];
  const scaleItems = [
    { key: "scale-1", label: "1 倍", enabled: true, action_id: "choose-scale", scaleChoice: true, description: "MP 10" },
    { key: "scale-2", label: "2 倍", enabled: true, action_id: "choose-scale", scaleChoice: true, description: "MP 16" },
  ];
  const confirmItems = [
    { key: "confirm-forfeit", label: "確認投降", enabled: true, action_id: "combat.forfeit" },
    { key: "cancel-forfeit", label: "取消", enabled: true, navigation: true, surface: "cancel-forfeit" },
  ];
  // The character panel's read-only rows: focusable navigation cells that
  // submit nothing — the `plain` pane's production shape.
  const plainItems = [
    { key: "trait-hp", label: "HP 100 / 100", enabled: true, navigation: true, surface: "trait-hp" },
    { key: "trait-mp", label: "MP 40 / 40", enabled: true, navigation: true, surface: "trait-mp" },
  ];

  it("cards: rows equal the committed suggestion-card items in order", () => {
    const w = mountMenu(cardItems, "exploration-row");
    assertRowsInOrder(w, cardItems, "exploration-row");
  });

  it("skills: rows equal the committed skill items in order, disabled row keeps its reason", () => {
    // The detail pane (combat-detail) renders only with a focused skill; the
    // disabled skill's reason ("冷卻中") is shown beside its cost.
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(DockMenu, {
      attachTo: host,
      props: {
        items: skillItems,
        depth: 2,
        idPrefix: "combat-row",
        focusedKey: "skill-heal",
        detailTestId: "combat-detail",
      },
    });
    assertRowsInOrder(wrapper, skillItems, "combat-row");
    const detail = wrapper.find('[data-testid="combat-detail"]');
    expect(detail.exists()).toBe(true);
    expect(detail.text()).toContain("冷卻中");
  });

  it("targets: rows equal the committed combat target items in order", () => {
    const w = mountMenu(targetItems, "combat-row");
    assertRowsInOrder(w, targetItems, "combat-row");
    // The `✓` AREA selection marker is on the `selected` candidate.
    const tokens = w.findAll(".dock-menu__token");
    expect(tokens[0].classes()).toContain("dock-menu__token--pressed");
    expect(tokens[1].classes()).not.toContain("dock-menu__token--pressed");
  });

  it("scales: rows equal the committed 威力 items in order", () => {
    const w = mountMenu(scaleItems, "combat-row");
    assertRowsInOrder(w, scaleItems, "combat-row");
    // The server-computed `mp_cost` renders beside each scale row.
    const costs = w.findAll(".dock-menu__scale-cost");
    expect(costs.map((c) => c.text())).toEqual(["MP 10", "MP 16"]);
  });

  it("confirm: rows equal the committed confirm items in order", () => {
    const w = mountMenu(confirmItems, "combat-row");
    assertRowsInOrder(w, confirmItems, "combat-row");
  });

  it("plain: rows equal the committed display-only items in order", () => {
    const w = mountMenu(plainItems, "exploration-row");
    assertRowsInOrder(w, plainItems, "exploration-row");
  });

  it("no pane renders a field the payload does not carry", () => {
    // A plain frame of display-only rows has no `cost_text` / `kind` /
    // `direction`; the pane must not invent a cost, a kind sub-line, or a
    // direction glyph — the row renders its label alone.
    const w = mountMenu(plainItems, "exploration-row");
    expect(w.find(".dock-menu__skill-cost").exists()).toBe(false);
    expect(w.get('[data-item-key="trait-hp"]').text()).toBe("HP 100 / 100");
  });

  // fix-webclient-hud-dock-exploration-grid-width: the fixed keyboard column
  // count drives the rendered `grid-template-columns` template. This pins the
  // INLINE TEMPLATE ONLY: the combat panes are flex boxes, on which that
  // template has no effect, so the test makes no claim about rendered column
  // widths or equal-width columns (webclient-talk-open-dock: a fixed-column
  // pane stays inside the command region; how its form uses the width is the
  // form's own decision). The pane element's inline style is asserted on the
  // rendered element (the script-setup computed is closed, so `wrapper.vm` is
  // not relied upon).
  const PANE_SELECTORS = {
    cards: ".dock-menu__cards",
    skills: ".dock-menu__skills",
    targets: ".dock-menu__targets",
    scales: ".dock-menu__scales",
    confirm: ".dock-menu__confirm",
    plain: ".dock-menu__plain",
  };

  function mountMenuWithCols(items, cols, idPrefix = "exploration-row") {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const w = mount(DockMenu, {
      attachTo: host,
      props: { items, depth: 2, gridCols: cols, idPrefix },
    });
    return w;
  }

  it("every kind with gridCols emits repeat(n, 1fr); no gridCols emits none", () => {
    const stretchCases = [
      { items: cardItems, sel: PANE_SELECTORS.cards, expected: "repeat(2, 1fr)" },
      { items: skillItems, sel: PANE_SELECTORS.skills, expected: "repeat(2, 1fr)" },
      { items: targetItems, sel: PANE_SELECTORS.targets, expected: "repeat(2, 1fr)" },
      { items: scaleItems, sel: PANE_SELECTORS.scales, expected: "repeat(2, 1fr)" },
      { items: confirmItems, sel: PANE_SELECTORS.confirm, expected: "repeat(2, 1fr)" },
      { items: plainItems, sel: PANE_SELECTORS.plain, expected: "repeat(2, 1fr)" },
    ];
    for (const { items, sel, expected } of stretchCases) {
      const w = mountMenuWithCols(items, 2);
      const pane = w.find(sel);
      expect(pane.exists()).toBe(true, sel + " pane rendered");
      expect(pane.element.style.gridTemplateColumns).toBe(expected);
      w.unmount();
      document.body.innerHTML = "";
    }
    // No `gridCols` (null) or a zero value: the pane carries no inline grid
    // template (the computed returns an empty object).
    for (const cols of [null, 0]) {
      const w = mountMenuWithCols(plainItems, cols);
      const pane = w.find(PANE_SELECTORS.plain);
      expect(pane.element.style.gridTemplateColumns).toBe("");
      // The plain pane is not a grid container (task 2.3 re-confirmation):
      // its computed display stays block, so the inline grid template (and
      // this change) is inert on the 等待/休息 frame.
      expect(getComputedStyle(pane.element).display).toBe("block");
      w.unmount();
      document.body.innerHTML = "";
    }
  });

  it("the listbox active descendant never dangles on a focused back row", async () => {
    const backItem = { key: "back", label: "返回上一層", enabled: true, navigation: true, surface: "back" };
    // Every frame renders its `back` item as a row of its own listbox, so the
    // active descendant keeps naming its real row id.
    const plainWithBack = [...plainItems, backItem];
    const w = mountMenu(plainWithBack, "exploration-row");
    w.setProps({ focusedKey: "back" });
    await w.vm.$nextTick();
    const listbox = w.find('[role="listbox"]');
    expect(listbox.attributes("aria-activedescendant")).toBe(
      `exploration-row-${plainWithBack.length - 1}`,
    );
    w.unmount();
    document.body.innerHTML = "";
  });
});
