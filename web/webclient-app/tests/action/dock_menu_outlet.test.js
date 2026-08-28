// fix-webclient-hud-dock-outlet-tile-presentation (tasks 1.2, 2.2, 3.3):
// the outlet (exit list) pane's tile presentation — the bold headline's
// field mapping (enabled + canonical + known destination → destination's
// display name, else the exit's own label), exactly one glyph-shaped
// element per tile (no focus caret), no companion detail aside, and the
// disabled row's server-authored reason stays reachable from the tile
// itself. Mounts DockMenu at depth 2 (the pane depth) with a committed
// local-map lattice in the `view` prop.

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import DockMenu from "../../components/DockMenu.vue";

// Hoisted fixtures (arrays of objects) to dodge the V8/Node 24 parser
// quirk on nested object-in-array-in-object literals.

const LATTICE_NODES = [
  { id: "grid:capital_altoria:2:1", label: "南大道" },
  { id: "grid:capital_altoria:3:1", label: "北岸大道" },
];
const VIEW_WITH_LATTICE = { localMapModel: { nodes: LATTICE_NODES } };

const ENABLED_CANONICAL = {
  key: "exit-1",
  label: "南",
  enabled: true,
  action_id: "explore.move",
  direction: "south",
  destination: "grid:capital_altoria:2:1",
};
// A disabled move row carries no `action_id` (moveItems: `actionId: canSubmit
// ? "explore.move" : null`), so AppClient normalizes it as a navigation
// cell (`navigation: true` + `surface`) — the shape the dock item classifier
// expects.
const DISABLED_CANONICAL = {
  key: "exit-2",
  label: "南（無法通行）",
  enabled: false,
  navigation: true,
  surface: "exit-2",
  direction: "south",
  destination: "grid:capital_altoria:2:1",
  disabled_reason: { code: "blocked", message: "出口被阻擋。" },
};
const ENABLED_UNKNOWN_DEST = {
  key: "exit-3",
  label: "北",
  enabled: true,
  action_id: "explore.move",
  direction: "north",
  destination: "grid:capital_altoria:99:99",
};
const NON_CANONICAL = {
  key: "exit-4",
  label: "南門",
  enabled: true,
  action_id: "explore.move",
  direction: null,
  destination: "grid:capital_altoria:2:1",
};
const UNKNOWN_DIRECTION = {
  key: "exit-5",
  label: "秘徑",
  enabled: true,
  action_id: "explore.move",
  direction: "diagonal",
  destination: "grid:capital_altoria:2:1",
};
// An out-of-table direction that names an `Object.prototype` property would
// collide with a plain-object glyph table; the null-prototype table must
// treat it like any other unknown direction (no glyph, own label).
const PROTOTYPE_NAME_DIRECTION = {
  key: "exit-6",
  label: "迴廊",
  enabled: true,
  action_id: "explore.move",
  direction: "constructor",
  destination: "grid:capital_altoria:2:1",
};
const BACK_ROW = { key: "back", label: "返回", navigation: true, surface: "back" };

describe("DockMenu outlet tile presentation (outlet-tile-presentation)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountOutlet(items, extraProps = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(DockMenu, {
      attachTo: host,
      props: {
        items,
        depth: 2,
        idPrefix: "exploration-row",
        view: VIEW_WITH_LATTICE,
        focusedKey: items[0].key,
        ...extraProps,
      },
    });
    return wrapper;
  }

  function tiles(w) {
    return w.findAll(".dock-menu__outlet-tile");
  }

  it("renders the destination's display name as the bold headline (enabled + canonical + known destination)", () => {
    const w = mountOutlet([ENABLED_CANONICAL, BACK_ROW]);
    expect(tiles(w).at(0).find("b").text()).toBe("南大道");
  });

  it("falls back to the exit's own label when the destination is unknown", () => {
    const w = mountOutlet([ENABLED_UNKNOWN_DEST, BACK_ROW]);
    expect(tiles(w).at(0).find("b").text()).toBe("北");
  });

  it("a disabled canonical exit keeps its own label (with the （無法通行） suffix) as the bold headline", () => {
    const w = mountOutlet([DISABLED_CANONICAL, BACK_ROW]);
    expect(tiles(w).at(0).find("b").text()).toBe("南（無法通行）");
  });

  it("renders a non-canonical exit's label verbatim as the bold headline", () => {
    const w = mountOutlet([NON_CANONICAL, BACK_ROW]);
    expect(tiles(w).at(0).find("b").text()).toBe("南門");
  });

  it("a direction string outside the glyph table renders no glyph and keeps the label", () => {
    const w = mountOutlet([UNKNOWN_DIRECTION, BACK_ROW]);
    const tile = tiles(w).at(0);
    expect(tile.find(".dock-menu__outlet-glyph").exists()).toBe(false);
    expect(tile.find("b").text()).toBe("秘徑");
  });

  it("an out-of-table direction naming an Object.prototype property also renders no glyph and keeps the label", () => {
    const w = mountOutlet([PROTOTYPE_NAME_DIRECTION, BACK_ROW]);
    const tile = tiles(w).at(0);
    expect(tile.find(".dock-menu__outlet-glyph").exists()).toBe(false);
    expect(tile.find("b").text()).toBe("迴廊");
  });

  it("the focused outlet tile shows exactly one glyph and no focus caret", () => {
    const w = mountOutlet(
      [ENABLED_CANONICAL, DISABLED_CANONICAL, BACK_ROW],
      { focusedKey: "exit-1" },
    );
    const tile = tiles(w).at(0);
    expect(tile.classes()).toContain("dock-menu__outlet-tile--focused");
    expect(tile.find(".dock-menu__outlet-glyph").exists()).toBe(true);
    expect(tile.find(".dock-menu__outlet-glyph").text()).toBe("↓");
    expect(tile.text()).not.toContain("▶");
  });

  it("the outlet pane renders no dock-detail aside with a focused row", () => {
    const w = mountOutlet([ENABLED_CANONICAL, BACK_ROW], { focusedKey: "exit-1" });
    expect(w.find('[data-testid="dock-detail"]').exists()).toBe(false);
  });

  it("the outlet pane renders no dock-detail aside even when a detailMessage is set", () => {
    const w = mountOutlet([ENABLED_CANONICAL, BACK_ROW], {
      focusedKey: "exit-1",
      detailMessage: "休息時間格式錯誤",
    });
    expect(w.find('[data-testid="dock-detail"]').exists()).toBe(false);
  });

  // remove-redundant-dock-menu-layout: the listbox is the fragment root, so
  // the host holds it directly (no `.dock-menu-layout` wrapper) and — with the
  // aside suppressed for the outlet — it is the host's only dock-menu child.
  it("renders the listbox as the fragment root with no layout wrapper", () => {
    const w = mountOutlet([ENABLED_CANONICAL, BACK_ROW], { focusedKey: "exit-1" });
    expect(w.find(".dock-menu-layout").exists()).toBe(false);
    expect(w.find(".dock-detail").exists()).toBe(false);
    const list = w.get('[data-testid="dock-menu"]');
    // The host (multi-root `w.element` is the parent container) holds the
    // listbox as its only dock-menu child.
    expect(list.element.parentElement).toBe(w.element);
    expect(w.element.querySelectorAll(".dock-menu").length).toBe(1);
  });

  it("keeps a disabled outlet row's server-authored reason reachable from the tile itself", () => {
    const w = mountOutlet([DISABLED_CANONICAL, BACK_ROW], { focusedKey: "exit-2" });
    const tile = tiles(w).at(0);
    expect(tile.attributes("aria-describedby")).toBe("exploration-row-0-reason");
    const hidden = w.find("#exploration-row-0-reason");
    expect(hidden.exists()).toBe(true);
    expect(hidden.text()).toBe("出口被阻擋。");
  });

  it("a disabled row stays focusable and submits no OOB intent", async () => {
    const w = mountOutlet([ENABLED_CANONICAL, DISABLED_CANONICAL, BACK_ROW], {
      focusedKey: "exit-2",
    });
    const tile = tiles(w).at(1);
    await tile.trigger("click");
    expect(w.emitted("focus-change")).toEqual([["exit-2"]]);
    expect(w.emitted("activate")).toBeUndefined();
  });
});
