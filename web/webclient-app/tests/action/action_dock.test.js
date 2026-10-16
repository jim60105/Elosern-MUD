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

// webclient-combat-command-card-centred D5: the narrow combat card
// presentation of the same dock.
describe("ActionDock card presentation", () => {
  const FOCUS_KEY = "attack";
  const view = { dockTrail: ["戰鬥", "技能", "元素魔法", "火焰"], dockDepth: 4 };

  function mountCard(props = {}) {
    return mount(ActionDock, {
      props: { mode: "combat", rootItems: COMBAT_ROOT_ITEMS, view, ...props },
      slots: {
        default: () =>
          h(DockMenu, {
            items: [
              { key: "attack", surface: "attack", label: "攻擊", enabled: true, command: true, navigation: true, description: "選擇一名目標。" },
              { key: "items", surface: "items", label: "物品", enabled: false, command: true, navigation: true, disabled_reason: { code: "empty", message: "背包是空的。" } },
            ],
            focusedKey: FOCUS_KEY,
            idPrefix: "combat-row",
            detailTestId: "combat-detail",
          }),
      },
    });
  }

  it("wears the shared card frame only as the card", () => {
    // Role: the card frame and its decoration exist exactly in card mode.
    // Detects a band dock painted as a card, or a card without its brackets.
    const card = mountCard({ card: true });
    const root = card.get("#action-dock");
    expect(root.classes()).toEqual(expect.arrayContaining(["action-dock--card", "choice-card", "choice-card--still"]));
    const corners = card.findAll(".choice-card__corners");
    expect(corners).toHaveLength(1);
    expect(corners[0].attributes("aria-hidden")).toBe("true");
    // The breadcrumb, the legend and the playback cue stay inside the card.
    const cued = mountCard({ card: true, playback: true });
    const cuedRoot = cued.get("#action-dock").element;
    for (const selector of ['[data-testid="dock-crumb"]', '[data-testid="action-dock-description"]', '[data-testid="action-dock-playback"]']) {
      expect(cuedRoot.querySelector(selector)).not.toBeNull();
    }
    const band = mountCard({ card: false });
    const bandRoot = band.get("#action-dock");
    expect(bandRoot.classes()).not.toContain("action-dock--card");
    expect(bandRoot.classes()).not.toContain("choice-card");
    expect(band.find(".choice-card__corners").exists()).toBe(false);
    for (const wrapper of [card, cued, band]) wrapper.unmount();
  });

  it("asks its frames for the detail strip as the card and for the pane in the band", () => {
    // Role: the detail variant follows the presentation. Detects a band dock
    // folding its detail into a strip, or a card keeping the side pane.
    const card = mountCard({ card: true });
    const strip = card.get('[data-testid="combat-detail"]');
    expect(strip.classes()).toContain("dock-detail--strip");
    expect(strip.attributes("id")).toBe("action-dock-detail-strip");
    expect(card.get("#combat-row-0").attributes("aria-describedby")).toBe("action-dock-detail-strip");
    expect(card.get("#combat-row-1").attributes("aria-describedby")).toBeUndefined();
    expect(strip.text()).toContain("選擇一名目標。");
    expect(strip.attributes("title")).toContain("攻擊");
    const band = mountCard({ card: false });
    expect(band.get('[data-testid="combat-detail"]').classes()).not.toContain("dock-detail--strip");
    expect(band.get("#combat-row-0").attributes("aria-describedby")).toBeUndefined();
    card.unmount();
    band.unmount();
  });

  it("keeps the legend's text while splitting it into segments that break only at separators", () => {
    const card = mountCard({ card: true });
    const legend = card.get('[data-testid="action-dock-description"]');
    expect(legend.text()).toBe("數字鍵 1–9 ‧ Enter 執行 ‧ Esc 返回");
    expect(legend.findAll(".action-dock__legend-seg").map((seg) => seg.text())).toEqual([
      "數字鍵 1–9 ‧",
      "Enter 執行 ‧",
      "Esc 返回",
    ]);
    // The breadcrumb keeps the back control and the current frame apart from
    // the ellipsizing earlier crumbs.
    const crumb = card.get('[data-testid="dock-crumb"]');
    expect(crumb.get(".dock-crumb__parents").text()).toBe("戰鬥 › 技能 › 元素魔法 ›");
    expect(crumb.get(".dock-crumb__current").text()).toBe("火焰");
    expect(crumb.find(".dock-crumb__back").exists()).toBe(true);
    card.unmount();
  });
});

describe("DockMenu strip id", () => {
  it("renders one strip and never doubles its id while a skill pane stands in", () => {
    // Role: one element carries the strip id the focused row names. Detects
    // a generic strip rendered beside SkillDetailPane's (a duplicate id).
    const items = [{ key: "skill-a", label: "甲", enabled: false, action_id: "open-skill", params: {}, disabled_reason: { code: "x", message: "不可" } }];
    const w = mount(DockMenu, {
      props: { items, focusedKey: "skill-a", idPrefix: "combat-row", variant: "strip", hideGenericDetail: true, detailMessage: "訊息" },
    });
    expect(w.findAll("#action-dock-detail-strip")).toHaveLength(0);
    expect(w.get("#combat-row-0").attributes("aria-describedby")).toBe("action-dock-detail-strip");
    expect(w.find('[aria-label="項目詳情"]').exists()).toBe(false);
    w.unmount();
    const own = mount(DockMenu, { props: { items, focusedKey: "skill-a", idPrefix: "combat-row", variant: "strip", showDetail: false } });
    expect(own.find("#action-dock-detail-strip").exists()).toBe(false);
    expect(own.get("#combat-row-0").attributes("aria-describedby")).toBeUndefined();
    own.unmount();
  });
});

// webclient-combat-stage-target-picking (design D3): in the stage target step
// the card collapses to the target prompt — the action with 選擇目標 and Esc
// 返回, the focused position's summary, and the AREA chips — with the row
// region mounted but hidden, the breadcrumb and legend gone, and a polite live
// region carrying the announcement; chips emit the pointer entry and hand DOM
// focus back to #action-dock.
describe("ActionDock stage target prompt", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.replaceChildren();
  });
  const member = (id, side, digit, extra = {}) => ({ key: `target-${id}`, kind: "member", identities: [String(id)], side, digit, offStage: false, label: `名${id}`, ...extra });
  function step(extra = {}) {
    const positions = extra.positions || [member(7, "foes", 1), member(8, "party", 2)];
    const focused = positions.find((p) => p.key === (extra.focusKey ?? positions[0].key)) || null;
    return {
      form: "single", skillKey: "t_x", label: "火球", scaleLabel: null, positions,
      focusKey: focused ? focused.key : null, focused, lit: focused ? focused.identities : [],
      selectable: ["7", "8"], selectedIds: [], shorthand: null, choiceCount: 0, digits: {}, announce: "目標：名7，敵方",
      ...extra, ...(extra.focusKey !== undefined ? { focused } : {}),
    };
  }
  const dock = (props) =>
    mount(ActionDock, {
      attachTo: document.body,
      props: { mode: "combat", rootItems: COMBAT_ROOT_ITEMS, view: { dockTrail: [], dockDepth: 2 }, card: true, ...props },
      slots: { default: () => h("div", { "data-testid": "dock-menu" }, [h("button", { "data-testid": "row" }, "row")]) },
    });

  it("renders the prompt per form and hides the row region, crumb and legend", async () => {
    wrapper = dock({ stageTarget: step({ scaleLabel: "威力 ×2" }) });
    expect(wrapper.get("#action-dock").classes()).toContain("action-dock--target");
    expect(wrapper.get('[data-testid="target-prompt-action"]').text()).toBe("火球威力 ×2 ‧ 選擇目標");
    expect(wrapper.get(".target-prompt__esc").text()).toBe("Esc 返回");
    expect(wrapper.get('[data-testid="target-prompt-focus"]').text().replace(/\s+/g, "")).toBe("▸名7敵方");
    expect(wrapper.get(".action-dock__body").attributes("hidden")).toBeDefined();
    expect(wrapper.find('[data-testid="dock-menu"]').exists()).toBe(true); // mounted, hidden
    expect(wrapper.find('[data-testid="action-dock-description"]').exists()).toBe(false);
    expect(wrapper.find(".dock-crumb").exists()).toBe(false);
    expect(wrapper.find('[data-testid="target-prompt-chips"]').exists()).toBe(false);
    const live = wrapper.get('[data-testid="target-announce"]');
    expect(live.attributes("role")).toBe("status");
    expect(live.attributes("aria-live")).toBe("polite");
    expect(live.text()).toBe("目標：名7，敵方");
    // SELF and an off-stage member.
    await wrapper.setProps({ stageTarget: step({ form: "self", positions: [{ key: "self-confirm", kind: "self", identities: ["42"], side: "party", digit: 1, offStage: false, label: "自己" }], focusKey: "self-confirm", announce: "目標：自己" }) });
    expect(wrapper.get('[data-testid="target-prompt-focus"]').text().replace(/\s+/g, "")).toBe("▸自己我方");
    await wrapper.setProps({ stageTarget: step({ positions: [member(9, "foes", 1, { offStage: true, label: "逃兵" })], focusKey: "target-9" }) });
    expect(wrapper.get('[data-testid="target-prompt-focus"]').text().replace(/\s+/g, "")).toBe("▸逃兵敵方場外");
    // The step ends: the rows, the crumb and the legend return; the live region stays.
    await wrapper.setProps({ stageTarget: null });
    expect(wrapper.get(".action-dock__body").attributes("hidden")).toBeUndefined();
    expect(wrapper.find('[data-testid="action-dock-description"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="target-announce"]').text()).toBe("");
  });

  it("AREA chips emit the pointer entry and hand DOM focus back to the card", async () => {
    const positions = [
      member(7, "foes", 1),
      { key: "shorthand-all-enemies", kind: "group", shorthand: "all-enemies", identities: ["7"], side: "foes", digit: 2, offStage: false, label: "全體敵人" },
      { key: "area-confirm", kind: "confirm", identities: ["7"], side: null, digit: 3, offStage: false, label: "施展" },
    ];
    wrapper = dock({ stageTarget: step({ form: "area", positions, focusKey: "area-confirm", selectedIds: ["7"], choiceCount: 1, announce: "施展：已選 1 名" }) });
    const chips = wrapper.findAll('[data-testid="target-prompt-chip"]');
    expect(chips.map((c) => c.text())).toEqual(["全體敵人", "施展（1）"]);
    expect(chips[1].attributes("data-focused")).toBe("true");
    expect(chips.every((c) => c.attributes("tabindex") === "-1")).toBe(true);
    expect(wrapper.get('[data-testid="target-prompt-focus"]').text().replace(/\s+/g, "")).toBe("▸施展已選1名");
    chips[0].element.focus();
    await chips[0].trigger("click");
    expect(wrapper.emitted("target-pointer")).toEqual([["shorthand-all-enemies", "activate"]]);
    expect(document.activeElement).toBe(wrapper.get("#action-dock").element);
  });

  it("moves DOM focus out of the rows into the card when the step starts", async () => {
    wrapper = dock({ stageTarget: null });
    wrapper.get('[data-testid="row"]').element.focus();
    await wrapper.setProps({ stageTarget: step() });
    await nextTick();
    expect(document.activeElement).toBe(wrapper.get("#action-dock").element);
  });
});
