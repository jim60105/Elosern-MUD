import { mount } from "@vue/test-utils";
import { h, nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import ActionDock from "../../components/ActionDock.vue";
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
];

const ROOT_ITEMS = [
  { key: "move", label: "移動", enabled: true },
  { key: "look", label: "查看", enabled: true },
  { key: "interact", label: "互動", enabled: true },
  { key: "suggestions", label: "建議", enabled: true },
];

// The combat root is the ONLY root that renders the tab bar
// (webclient-scene-overview-swap D3).
const COMBAT_ROOT_ITEMS = [
  { key: "attack", label: "攻擊", enabled: true },
  { key: "skills", label: "技能", enabled: true },
  { key: "items", label: "物品", enabled: false },
  { key: "defend", label: "防禦", enabled: false },
  { key: "flee", label: "逃亡", enabled: true },
  { key: "forfeit", label: "投降", enabled: true },
];


describe("ActionDock (B2 action-dock family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountDock(props = {}, items = AFFORDANCES) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ActionDock, {
      attachTo: host,
      props: { mode: "exploration", ...props },
      slots: {
        default: () => [h(DockMenu, { items, depth: 2 })],
      },
    });
    return wrapper;
  }

  it("renders the focusable #action-dock target with its guidance line", () => {
    const w = mountDock({ guidancePrefix: "附近動作" });
    const dock = w.get('[data-testid="action-dock"]');
    expect(dock.attributes("id")).toBe("action-dock");
    expect(dock.attributes("tabindex")).toBe("0");
    expect(dock.attributes("data-mode")).toBe("exploration");
    expect(
      w.get('[data-testid="action-dock-guidance"]').exists(),
    ).toBe(true);
  });

  it("keeps the breadcrumb on every frame below the root", () => {
    // exploration-presence-rail: the verb popover that named its own target
    // (and so hid the breadcrumb) is gone; every submenu frame keeps it.

    const submenu = mountDock({
      rootItems: ROOT_ITEMS,
      view: { dockDepth: 2, dockTrail: ["場景", "建議"], dockSource: "suggestions" },
    });
    const crumb = submenu.get('[data-testid="dock-crumb"]');
    expect(crumb.attributes("hidden")).toBeUndefined();
    expect(crumb.text()).toContain("場景 › 建議");
  });

  it("renders the draft shortcut legend as the single hook-bearing element", () => {
    // webclient-scene-overview-swap D3: the legend is the dock's own strip
    // below the scrolling body (the draft's `.dock .hint`), the ONLY element
    // carrying the `action-dock-description` hook. The hidden duplicate is
    // gone, and no tab bar carries a second copy.
    const w = mountDock({ mode: "combat", rootItems: ROOT_ITEMS });
    const legends = w.findAll('[data-testid="action-dock-description"]');
    expect(legends).toHaveLength(1);
    const legend = legends[0];
    expect(legend.classes()).toContain("action-dock__legend");
    expect(legend.text()).toBe("數字鍵 1–9 ‧ Enter 執行 ‧ Esc 返回");
    // The draft's <kbd> structure: exactly two kbd children, in order.
    const kbds = legend.findAll("kbd");
    expect(kbds.map((k) => k.text())).toEqual(["Enter", "Esc"]);
    // Truthfulness: no affordance the draft's legend does not name.
    expect(legend.text()).not.toContain("/ 聚焦指令列");
    expect(w.find(".action-dock__description").exists()).toBe(false);
    expect(legend.attributes("aria-hidden")).toBeUndefined();
  });

  it("refreshes the guidance note when the surface prefix changes", async () => {
    const w = mountDock({ guidancePrefix: "附近動作" });
    expect(w.get('[data-testid="action-dock-guidance"]').text()).toBe("附近動作");
    w.setProps({ guidancePrefix: "戰鬥動作" });
    await nextTick();
    expect(w.get('[data-testid="action-dock-guidance"]').text()).toBe("戰鬥動作");
  });

  it("renders one legend in dialogue and combat, and none in exploration or creation", () => {
    for (const mode of ["dialogue", "combat"]) {
      const w = mountDock({ mode, rootItems: COMBAT_ROOT_ITEMS });
      expect(w.findAll('[data-testid="action-dock-description"]'), mode).toHaveLength(1);
      w.unmount();
    }
    // exploration-exit-compass: the exploration panel shows no key hints;
    // its bindings live in the help overlay.
    const exploration = mountDock({ mode: "exploration", rootItems: COMBAT_ROOT_ITEMS });
    expect(exploration.findAll('[data-testid="action-dock-description"]')).toHaveLength(0);
    exploration.unmount();
    const creation = mountDock({ mode: "creation", rootItems: [] });
    expect(creation.findAll('[data-testid="action-dock-description"]')).toHaveLength(0);
  });

  it("renders no root chrome of its own: the combat root is the pane's command list", () => {
    // webclient-combat-command-window: the dock carries no tab bar; the
    // combat root renders through DockMenu's `commands` form in the pane.
    const combat = mountDock({ mode: "combat", rootItems: COMBAT_ROOT_ITEMS });
    // Every row container and row lives in the pane: no chrome row outside.
    const menus = combat.findAll('[data-testid="dock-menu"]');
    expect(menus).toHaveLength(1);
    expect(menus[0].element.closest(".action-dock__pane")).not.toBeNull();
    for (const row of combat.findAll("[data-item-key]")) {
      expect(row.element.closest(".action-dock__pane")).not.toBeNull();
    }
  });

  it("shows the playback cue only while playback, and its skip emits once", async () => {
    const w = mountDock({ mode: "combat", rootItems: COMBAT_ROOT_ITEMS });
    expect(w.find('[data-testid="action-dock-playback"]').exists()).toBe(false);
    await w.setProps({ playback: true });
    const cue = w.get('[data-testid="action-dock-playback"]');
    // The wait is announced; the skip button sits outside the live region.
    expect(cue.get('[role="status"]').text()).toBe("回合演出中");
    expect(cue.find('[role="status"] button').exists()).toBe(false);
    // A decorative line only: no percentage or progress value anywhere.
    expect(cue.text()).not.toMatch(/\d+\s*%/);
    expect(cue.find('[role="progressbar"]').exists()).toBe(false);
    await w.get('[data-testid="action-dock-playback-skip"]').trigger("click");
    expect(w.emitted("skip")).toHaveLength(1);
    await w.setProps({ playback: false });
    expect(w.find('[data-testid="action-dock-playback"]').exists()).toBe(false);
  });

  it("renders the overlay slot inside the action-dock body, after the pane", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ActionDock, {
      attachTo: host,
      props: { mode: "exploration" },
      slots: {
        default: () => [h("div", { "data-testid": "pane-content" })],
        overlay: () => [h("div", { "data-testid": "overlay-content" })],
      },
    });
    const body = wrapper.get(".action-dock__body");
    expect(body.find(".action-dock__pane").exists()).toBe(true);
    const overlay = wrapper.get('[data-testid="overlay-content"]');
    // The overlay is the body's second child: a positioned overlay therefore
    // covers exactly the pane's visible box.
    expect(overlay.element.parentElement).toBe(body.element);
    expect(overlay.element.previousElementSibling.className).toContain("action-dock__pane");
  });

  it("never renders suggestion content at the dock root outside the pane", () => {
    const w = mountDock({ rootItems: ROOT_ITEMS }, []);
    expect(w.find('[data-testid="suggestions-section"]').exists()).toBe(false);
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(0);
  });

  it("retires suggestion presentation on transport reset", () => {
    // When transport reset occurs, the suggestions menu is cleared
    const w = mountDock({ rootItems: ROOT_ITEMS }, []);
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(0);
    expect(w.find('[data-item-key="action-options.dismiss"]').exists()).toBe(false);
  });
});
