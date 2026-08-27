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
    delete globalThis.ResizeObserver;
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

  const outletItems = [
    { key: "exit-north", label: "北へ", enabled: true, action_id: "explore.move", direction: "north" },
    { key: "exit-east", label: "東へ", enabled: true, action_id: "explore.move", direction: "east" },
  ];
  const navItems = [
    { key: "look-room", label: "查看房間", enabled: true, action_id: "explore.look" },
    { key: "entity-1", label: "老婦", enabled: true, action_id: "explore.look", kind: "npc" },
  ];
  const affordanceItems = [
    { key: "engage", label: "交戰", enabled: true, action_id: "explore.engage" },
    { key: "party-invite", label: "邀請入隊", enabled: false, action_id: "explore.party_invite", disabled_reason: { code: "full", message: "隊員已滿員" } },
  ];
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
  const plainItems = [
    { key: "move", label: "移動", enabled: true, navigation: true, surface: "move" },
    { key: "look", label: "查看", enabled: true, navigation: true, surface: "look" },
  ];
  const LONG_LABEL = "北岸大道之北岸大道之北岸大道之北岸大道之北岸大道";
  const longOutlet = [
    { key: "exit-north", label: LONG_LABEL, enabled: true, action_id: "explore.move", direction: "north" },
  ];
  const longNavLabels = ["交戰", "查驗", "取物", "查看"];
  const longNav = [
    {
      key: "look-keeper",
      label: LONG_LABEL,
      enabled: true,
      action_id: "explore.look",
      affordanceLabels: longNavLabels,
    },
  ];

  it("outlet: rows equal the committed move items in order", () => {
    const w = mountMenu(outletItems, "exploration-row");
    assertRowsInOrder(w, outletItems, "exploration-row");
  });

  it("nav: rows equal the committed look items in order", () => {
    const w = mountMenu(navItems, "exploration-row");
    assertRowsInOrder(w, navItems, "exploration-row");
    // A look row with a `kind` renders the backed sub-line (entity kind).
    const sub = w.find(".dock-menu__nav-sub");
    expect(sub.text()).toBe("npc");
  });

  it("affordance: rows equal the committed affordance items in order", () => {
    const w = mountMenu(affordanceItems, "exploration-row");
    assertRowsInOrder(w, affordanceItems, "exploration-row");
    // The disabled affordance row keeps its reason readable.
    const reason = w.find(".dock-menu__aff-reason");
    expect(reason.exists()).toBe(true);
    expect(reason.text()).toContain("隊員已滿員");
  });

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

  it("plain: rows equal the committed root items in order", () => {
    const w = mountMenu(plainItems, "exploration-row");
    assertRowsInOrder(w, plainItems, "exploration-row");
  });

  it("no pane renders a field the payload does not carry", () => {
    // A plain root frame has no `cost_text` / `kind` / `direction`; the pane
    // must not invent a cost, kind sub-line, or direction glyph.
    const w = mountMenu(plainItems, "exploration-row");
    expect(w.find(".dock-menu__skill-cost").exists()).toBe(false);
    expect(w.find(".dock-menu__outlet-glyph").exists()).toBe(false);
    expect(w.find(".dock-menu__nav-sub").exists()).toBe(false);
  });

  // fix-webclient-hud-dock-exploration-grid-width: the fixed keyboard column
  // count drives the rendered track sizing per pane kind. The pane element's
  // inline `grid-template-columns` is asserted on the rendered element (the
  // script-setup computed is closed, so `wrapper.vm` is not relied upon).
  const PANE_SELECTORS = {
    outlet: ".dock-menu__outlet",
    nav: ".dock-menu__nav",
    affordance: ".dock-menu__aff",
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

  function cssRuleFor(selector) {
    for (const sheet of Array.from(document.styleSheets)) {
      try {
        const hit = Array.from(sheet.cssRules || []).find((rule) => {
          if (!rule.selectorText) return false;
          // Vue's `<style scoped>` appends a `[data-v-…]` attribute to each
          // selector; compare the core selector (the part before that attribute)
          // so the base tile/row rule is matched without grabbing the
          // `--focused` derivative rules.
          const core = rule.selectorText.split("[")[0].trim();
          return core === selector;
        });
        if (hit) {
          return hit;
        }
      } catch {
        return null;
      }
    }
    return null;
  }

  it("the nav pane emits content-sized tracks; the outlet pane and every other kind keep 1fr or none; no gridCols emits none", () => {
    const contentCases = [
      { items: navItems, sel: PANE_SELECTORS.nav, expected: "repeat(2, minmax(0, max-content))" },
    ];
    const outletCase = { items: outletItems, sel: PANE_SELECTORS.outlet, expected: "" };
    const stretchCases = [
      { items: affordanceItems, sel: PANE_SELECTORS.affordance, expected: "repeat(2, 1fr)" },
      { items: cardItems, sel: PANE_SELECTORS.cards, expected: "repeat(2, 1fr)" },
      { items: skillItems, sel: PANE_SELECTORS.skills, expected: "repeat(2, 1fr)" },
      { items: targetItems, sel: PANE_SELECTORS.targets, expected: "repeat(2, 1fr)" },
      { items: scaleItems, sel: PANE_SELECTORS.scales, expected: "repeat(2, 1fr)" },
      { items: confirmItems, sel: PANE_SELECTORS.confirm, expected: "repeat(2, 1fr)" },
      { items: plainItems, sel: PANE_SELECTORS.plain, expected: "repeat(2, 1fr)" },
    ];
    for (const { items, sel, expected } of [outletCase, ...contentCases, ...stretchCases]) {
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

  it("long destination and affordance labels wrap within the uncapped tile/row", () => {
    // OUTLET: a long destination name wraps inside the track (no content-width
    // cap on the tile) instead of pushing the layout past the pane.
    const w = mountMenuWithCols(longOutlet, 2, "exploration-row");
    const tile = w.find(".dock-menu__outlet-tile");
    expect(tile.exists()).toBe(true);
    expect(tile.text()).toContain(LONG_LABEL);
    const tileRule = cssRuleFor(".dock-menu__outlet-tile");
    expect(tileRule).toBeTruthy("the tile safety-net CSS rule is loaded");
    const tileCss = tileRule.style.cssText;
    // jsdom keeps the parsed declarations in `style.cssText` (its
    // camelCase accessors are unpopulated), so the safety net is asserted
    // on the declaration text. The tile carries no content-width cap: the
    // `1fr` tracks of the `auto-fit` grid stretch the tile to the track.
    expect(tileCss).not.toContain("max-width");
    expect(tileCss).toContain("min-width: 0");
    expect(tileCss).toContain("overflow-wrap: break-word");
    // The outlet grid is the width-adaptive `auto-fit` rule (empty tracks
    // collapse, the `min(150px, 100%)` floor never overflows a narrow pane).
    const outletRule = cssRuleFor(".dock-menu__outlet");
    expect(outletRule).toBeTruthy("the outlet grid CSS rule is loaded");
    expect(outletRule.style.cssText).toContain("repeat(auto-fit, minmax(min(150px, 100%), 1fr)");
    w.unmount();
    document.body.innerHTML = "";

    // NAV: a long joined affordance-label sub-line wraps inside the capped
    // row.
    const w2 = mountMenuWithCols(longNav, 2, "exploration-row");
    const row = w2.find(".dock-menu__nav-row");
    expect(row.exists()).toBe(true);
    expect(row.text()).toContain(LONG_LABEL);
    const rowRule = cssRuleFor(".dock-menu__nav-row");
    expect(rowRule).toBeTruthy("the row safety-net CSS rule is loaded");
    const rowCss = rowRule.style.cssText;
    expect(rowCss).toContain("max-width: 320px");
    expect(rowCss).toContain("min-width: 0");
    expect(rowCss).toContain("overflow-wrap: break-word");
    // The nav row's flex text block carries its own `min-width: 0` so a
    // long server-authored string wraps inside the capped row.
    const textRule = cssRuleFor(".dock-menu__nav-text");
    expect(textRule).toBeTruthy("the nav-text min-width rule is loaded");
    const textCss = textRule.style.cssText;
    expect(textCss).toContain("min-width: 0");
    expect(textCss).toContain("overflow-wrap: break-word");
    w2.unmount();
    document.body.innerHTML = "";
  });

  it("outlet: a partial last row spans its remaining columns (no blank space)", async () => {
    // 8 exits in a pane that fits 7 columns of 150px tracks: row 1 holds 7
    // tiles, row 2 holds a single tile that must span the rest of the row.
    const exits = Array.from({ length: 8 }, (_, i) => ({
      key: `exit-${i + 1}`,
      label: `出口${i + 1}`,
      enabled: true,
      action_id: "explore.move",
    }));
    // Fake the pane's own measured width (1140px → floor(1148/158) = 7 cols).
    globalThis.ResizeObserver = class {
      constructor(cb) {
        this.cb = cb;
      }
      observe(el) {
        const entry = { contentRect: { width: 1140 } };
        this.cb([entry], this);
      }
      disconnect() {}
      unobserve() {}
    };
    const w = mountMenuWithCols(exits, null, "exploration-row");
    await w.vm.$nextTick();
    const tiles = w.findAll(".dock-menu__outlet-tile");
    expect(tiles).toHaveLength(8);
    // The last tile (the lone row-2 tile) spans from its own column (1) to
    // the row's end; no tile before it carries the span.
    expect(tiles[tiles.length - 1].element.style.gridColumn).toBe("1 / -1");
    expect(tiles[0].element.style.gridColumn).toBe("");
    w.unmount();
    document.body.innerHTML = "";
  });

  it("outlet: a complete last row carries no span", async () => {
    // 14 exits at 7 columns: two complete rows, no partial row to fill.
    const exits = Array.from({ length: 14 }, (_, i) => ({
      key: `exit-${i + 1}`,
      label: `出口${i + 1}`,
      enabled: true,
      action_id: "explore.move",
    }));
    globalThis.ResizeObserver = class {
      constructor(cb) {
        this.cb = cb;
      }
      observe(el) {
        const entry = { contentRect: { width: 1140 } };
        this.cb([entry], this);
      }
      disconnect() {}
      unobserve() {}
    };
    const w = mountMenuWithCols(exits, null, "exploration-row");
    await w.vm.$nextTick();
    const tiles = w.findAll(".dock-menu__outlet-tile");
    expect(tiles).toHaveLength(14);
    for (const t of tiles) {
      expect(t.element.style.gridColumn).toBe("");
    }
    w.unmount();
    document.body.innerHTML = "";
  });

  it("the listbox active descendant never dangles on a focused back row", async () => {
    const backItem = { key: "back", label: "返回上一層", enabled: true, navigation: true, surface: "back" };
    // OUTLET: the back row is not rendered as an outlet tile, so the
    // listbox must not name a non-existent row id as its active descendant.
    const w = mountMenu([...outletItems, backItem], "exploration-row");
    w.setProps({ focusedKey: "back" });
    await w.vm.$nextTick();
    const listbox = w.find('[role="listbox"]');
    expect(listbox.attributes("aria-activedescendant")).toBeUndefined();
    w.unmount();
    document.body.innerHTML = "";

    // NAV: the back row IS rendered as a nav row, so the active descendant
    // keeps naming its real row id.
    const navWithBack = [...navItems, backItem];
    const w2 = mountMenu(navWithBack, "exploration-row");
    w2.setProps({ focusedKey: "back" });
    await w2.vm.$nextTick();
    const listbox2 = w2.find('[role="listbox"]');
    expect(listbox2.attributes("aria-activedescendant")).toBe(
      `exploration-row-${navWithBack.length - 1}`,
    );
    w2.unmount();
    document.body.innerHTML = "";
  });
});
