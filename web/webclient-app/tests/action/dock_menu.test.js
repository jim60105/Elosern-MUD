import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import DockMenu from "../../components/DockMenu.vue";

const AFFORDANCES = [
  {
    action_id: "explore.move",
    label: "走往北岸大道",
    params: { exit_ref: "north", current_node: 42 },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.wait",
    label: "等待",
    params: { daypart: "dusk" },
    freeform: false,
    navigation: false,
    enabled: false,
    disabled_reason: { code: "recovery", message: "正在調息，無法行動" },
  },
  {
    surface: "guild",
    label: "公會",
    navigation: true,
    enabled: true,
    disabled_reason: null,
  },
];

const TARGETS = [
  { identity: "e1", label: "灰袍盜賊", enabled: true, disabled_reason: null },
  { identity: "e2", label: "斷刃巡衛", enabled: false, disabled_reason: null },
];

describe("DockMenu (B2 action-dock family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountMenu(props = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(DockMenu, {
      attachTo: host,
      props: { items: AFFORDANCES, ...props },
    });
    return wrapper;
  }

  it("renders a finite framed grid with the preserved item keys", () => {
    const w = mountMenu();
    const grid = w.get('[data-testid="dock-menu"]');
    expect(grid.attributes("role")).toBe("listbox");
    expect(grid.attributes("tabindex")).toBe("0");
    const cells = w.findAll('[data-testid="dock-item"]');
    expect(cells).toHaveLength(3);
    expect(cells.map((cell) => cell.attributes("data-item-key"))).toEqual([
      "action-explore.move",
      "action-explore.wait",
      "action-guild",
    ]);
    expect(
      cells.map((cell) => cell.attributes("id")),
    ).toEqual(["dock-row-0", "dock-row-1", "dock-row-2"]);
  });

  it("uses the target- keys and the preserved idPrefix for target frames", () => {
    const w = mountMenu({ items: TARGETS, idPrefix: "combat-row" });
    const cells = w.findAll('[data-testid="dock-item"]');
    expect(cells.map((cell) => cell.attributes("data-item-key"))).toEqual([
      "target-e1",
      "target-e2",
    ]);
    expect(
      cells.map((cell) => cell.attributes("id")),
    ).toEqual(["combat-row-0", "combat-row-1"]);
  });

  it("points aria-activedescendant at the focusedKey cell", () => {
    const w = mountMenu({ focusedKey: "action-explore.wait" });
    expect(
      w.get('[data-testid="dock-menu"]').attributes("aria-activedescendant"),
    ).toBe("dock-row-1");
    const cells = w.findAll('[data-testid="dock-item"]');
    expect(cells[1].classes()).toContain("dock-menu-item--focused");
    const w2host = document.createElement("div");
    document.body.appendChild(w2host);
    const w2 = mount(DockMenu, {
      attachTo: w2host,
      props: { items: AFFORDANCES, focusedKey: null },
    });
    // No focused cell: the aria-activedescendant attribute is absent.
    expect(
      w2.get('[data-testid="dock-menu"]').attributes("aria-activedescendant"),
    ).toBeUndefined();
    w2.unmount();
  });

  it("activating the focused enabled cell emits the exact OOB action intent", async () => {
    const w = mountMenu({ focusedKey: "action-explore.move" });
    const cell = w.get('[data-item-key="action-explore.move"]');
    await cell.trigger("click");
    expect(w.emitted("focus-change")[0]).toEqual(["action-explore.move"]);
    expect(w.emitted("activate")).toHaveLength(1);
    const { key, item, intent } = w.emitted("activate")[0][0];
    expect(key).toBe("action-explore.move");
    expect(intent).toEqual({
      action_id: "explore.move",
      payload: { exit_ref: "north", current_node: 42 },
    });
    expect(item.label).toBe("走往北岸大道");
  });

  it("emits no activate intent for a disabled cell (focus change only)", async () => {
    const w = mountMenu({ focusedKey: "action-explore.move" });
    await w.get('[data-item-key="action-explore.wait"]').trigger("click");
    expect(w.emitted("focus-change")).toEqual([["action-explore.wait"]]);
    expect(w.emitted("activate")).toBeUndefined();
  });

  it("emits no OOB intent for a local navigation surface activation", async () => {
    const w = mountMenu();
    await w.get('[data-item-key="action-guild"]').trigger("click");
    expect(w.emitted("activate")).toHaveLength(1);
    expect(w.emitted("activate")[0][0].intent).toBeNull();
  });

  it("applies the fixed framed-grid geometry when gridCols is set", () => {
    const w = mountMenu({ gridCols: 3 });
    const grid = w.get('[data-testid="dock-menu"]');
    expect(grid.attributes("style")).toContain(
      "grid-template-columns: repeat(3, 1fr)",
    );
  });
});
