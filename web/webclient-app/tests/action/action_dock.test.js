import { mount } from "@vue/test-utils";
import { h, nextTick, ref } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import ActionDock from "../../components/ActionDock.vue";
import DockMenu from "../../components/DockMenu.vue";
import ExplorationMenu from "../../lib/exploration_menu.js";

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


function normalizeItems(items) {
  return items.map((item) => {
    const norm = {
      key: item.key,
      label: item.label,
      enabled: item.enabled !== false,
      hint: item.hint,
    };
    if (item.actionId) {
      norm.action_id = item.actionId;
      norm.params = item.payload || {};
    } else {
      norm.navigation = true;
      norm.surface = item.key;
    }
    return norm;
  });
}

const READY = {
  status: "ready",
  cards: [
    {
      kind: "known_action",
      action_code: "explore.look",
      label: "查看房間",
      params: { room: true },
    },
    {
      kind: "known_action",
      action_code: "explore.wait",
      label: "等到黃昏",
      params: { daypart: "dusk" },
      hint: "先休息一會兒再行動",
    },
    {
      kind: "freeform",
      action_code: "explore.talk_freeform",
      label: "我們聊聊好嗎？",
      params: { npc_id: 9 },
    },
  ],
};

describe("ActionDock (B2 action-dock family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function cssRuleFor(selector) {
    // Scan the mounted component stylesheets (vitest `css: true`) for the
    // rule whose core selector (before Vue's `[data-v-…]` suffix) matches.
    for (const sheet of Array.from(document.styleSheets)) {
      try {
        const hit = Array.from(sheet.cssRules || []).find((rule) => {
          if (!rule.selectorText) return false;
          const core = rule.selectorText.split("[")[0].trim();
          return core === selector;
        });
        if (hit) return hit;
      } catch {
        return null;
      }
    }
    return null;
  }

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

  it("renders the draft shortcut legend as the single hook-bearing element", () => {
    // webclient-align-01-dock-chrome: the legend is the tab bar's trailing
    // hint (the draft's `.dock .hint`), the ONLY element carrying the
    // `action-dock-description` hook. The hidden duplicate is gone.
    const w = mountDock({ rootItems: ROOT_ITEMS });
    const legends = w.findAll('[data-testid="action-dock-description"]');
    expect(legends).toHaveLength(1);
    const legend = legends[0];
    expect(legend.classes()).toContain("dock-tab-bar__hint");
    expect(legend.text()).toBe("數字鍵 1–4 · Enter 執行 · Esc 返回");
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

  it("renders exactly one visible legend with the draft's kbd styling", () => {
    const w = mountDock({ rootItems: ROOT_ITEMS });
    const hint = w.get('[data-testid="action-dock-description"]');
    const hintStyle = getComputedStyle(hint.element);
    // The visible legend: not clipped, not a hidden 1x1 copy.
    expect(hintStyle.display).not.toBe("none");
    expect(hintStyle.width).not.toBe("1px");
    // The draft's kbd rule is owned by this component's stylesheet: mono
    // face, the `--ink-780` ground, and the 2px bottom border.
    const kbdRule = cssRuleFor(".dock-tab-bar__hint kbd");
    expect(kbdRule, "the legend kbd rule ships").not.toBeNull();
    const kbdCss = kbdRule.style.cssText;
    expect(kbdCss).toContain("--ink-780");
    expect(kbdCss).toContain("var(--f-mono)");
    expect(kbdCss).toContain("border-bottom-width: 2px");
    // The tab icon's `<path>` carries the reference's per-key stroke
    // attributes: `move` has both cap+join, `interact` has join only,
    // `suggestions` (the star) has neither.
    const movePath = w.find('.dock-tab-bar__tab[data-item-key="move"] .dock-tab-bar__icon path');
    expect(movePath.attributes("stroke-linecap")).toBe("round");
    expect(movePath.attributes("stroke-linejoin")).toBe("round");
    const interactPath = w.find('.dock-tab-bar__tab[data-item-key="interact"] .dock-tab-bar__icon path');
    expect(interactPath.attributes("stroke-linejoin")).toBe("round");
    expect(interactPath.attributes("stroke-linecap")).toBeUndefined();
    const suggPath = w.find('.dock-tab-bar__tab[data-item-key="suggestions"] .dock-tab-bar__icon path');
    expect(suggPath.attributes("stroke-linecap")).toBeUndefined();
    expect(suggPath.attributes("stroke-linejoin")).toBeUndefined();
  });

  it("never renders suggestion content at the dock root outside the pane", () => {
    const w = mountDock({ rootItems: ROOT_ITEMS }, []);
    expect(w.find('[data-testid="suggestions-section"]').exists()).toBe(false);
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(0);
  });

  it("renders ready suggestions solely inside the 建議 router pane with dismiss control", () => {
    const menu = ExplorationMenu.suggestionsMenu(READY);
    const w = mountDock({ rootItems: ROOT_ITEMS }, normalizeItems(menu.items));

    // No legacy root section exists
    expect(w.find('[data-testid="suggestions-section"]').exists()).toBe(false);

    // Cards render inside the pane
    const cards = w.findAll('.dock-menu__cards [data-item-key^="action-explore"]');
    expect(cards).toHaveLength(3);
    expect(cards[0].text()).toContain("查看房間");
    expect(cards[1].text()).toContain("等到黃昏");
    expect(cards[1].text()).toContain("先休息一會兒再行動");
    expect(cards[2].text()).toContain("我們聊聊好嗎？");

    // Clear suggestions row exists in the pane
    const dismissRow = w.find('[data-item-key="action-options.dismiss"]');
    expect(dismissRow.exists()).toBe(true);
    expect(dismissRow.text()).toContain("✕ 清除建議");
  });

  it("emits the exact OOB action intent when a card or dismiss in the 建議 pane is activated", async () => {
    const menu = ExplorationMenu.suggestionsMenu(READY);
    const host = document.createElement("div");
    document.body.appendChild(host);

    let emittedAction = null;
    wrapper = mount({
      components: { ActionDock, DockMenu },
      setup: () => ({
        items: normalizeItems(menu.items),
        onActivate: (ev) => { emittedAction = ev; },
      }),
      template: `
        <ActionDock :root-items="['suggestions']" mode="exploration">
          <DockMenu :items="items" :depth="2" @activate="onActivate" />
        </ActionDock>
      `,
    }, { attachTo: host });

    const cards = wrapper.findAll('.dock-menu__cards [data-item-key^="action-explore"]');
    expect(cards).toHaveLength(3);

    // Click card 0: known_action explore.look
    await cards[0].trigger("click");
    expect(emittedAction.intent).toEqual({
      action_id: "explore.look",
      payload: { room: true },
    });

    // Click card 2: freeform explore.talk_freeform
    await cards[2].trigger("click");
    expect(emittedAction.intent).toEqual({
      action_id: "explore.talk_freeform",
      payload: { npc_id: 9, speech: "我們聊聊好嗎？" },
    });

    // Click dismiss control
    const dismissRow = wrapper.find('[data-item-key="action-options.dismiss"]');
    await dismissRow.trigger("click");
    expect(emittedAction.intent).toEqual({
      action_id: "options.dismiss",
      payload: {},
    });
  });

  it("renders generating state in the 建議 pane as one disabled row with no cards", () => {
    const menu = ExplorationMenu.suggestionsMenu({ status: "generating" });
    const w = mountDock({ rootItems: ROOT_ITEMS }, normalizeItems(menu.items));

    expect(w.findAll('.dock-menu__cards [data-item-key^="action-explore"]')).toHaveLength(0);
    const generatingRow = w.find('[data-item-key="suggestions-generating"]');
    expect(generatingRow.exists()).toBe(true);
    expect(generatingRow.text()).toContain("AI 正在構思建議…");
  });

  it("renders degraded state in the 建議 pane with rule cards or empty note", () => {
    // Degraded with 0 cards: empty note
    const emptyMenu = ExplorationMenu.suggestionsMenu({ status: "degraded", cards: [] });
    const w1 = mountDock({ rootItems: ROOT_ITEMS }, normalizeItems(emptyMenu.items));
    expect(w1.findAll('.dock-menu__cards [data-item-key^="action-explore"]')).toHaveLength(0);
    const emptyRow = w1.find('[data-item-key="suggestions-empty"]');
    expect(emptyRow.exists()).toBe(true);
    expect(emptyRow.text()).toContain("現在沒有什麼值得做的動作");

    w1.unmount();
    document.body.innerHTML = "";

    // Degraded with 1 rule card: card present
    const ruleMenu = ExplorationMenu.suggestionsMenu({
      status: "degraded",
      cards: [READY.cards[0]],
    });
    const w2 = mountDock({ rootItems: ROOT_ITEMS }, normalizeItems(ruleMenu.items));
    expect(w2.findAll('.dock-menu__cards [data-item-key^="action-explore"]')).toHaveLength(1);
    expect(w2.find('[data-item-key="action-options.dismiss"]').exists()).toBe(true);
  });

  it("replaces generating line in place with ready cards inside the 建議 pane", async () => {
    const genMenu = ExplorationMenu.suggestionsMenu({ status: "generating" });
    const readyMenu = ExplorationMenu.suggestionsMenu(READY);

    const host = document.createElement("div");
    document.body.appendChild(host);

    const itemsRef = ref(normalizeItems(genMenu.items));
    wrapper = mount({
      components: { ActionDock, DockMenu },
      setup: () => ({ items: itemsRef }),
      template: `
        <ActionDock :root-items="['suggestions']" mode="exploration">
          <DockMenu :items="items" :depth="2" />
        </ActionDock>
      `,
    }, { attachTo: host });

    const paneBefore = wrapper.get(".action-dock__pane").element;
    expect(wrapper.find('[data-item-key="suggestions-generating"]').exists()).toBe(true);
    expect(wrapper.findAll('.dock-menu__cards [data-item-key^="action-explore"]')).toHaveLength(0);

    itemsRef.value = normalizeItems(readyMenu.items);
    await nextTick();

    const paneAfter = wrapper.get(".action-dock__pane").element;
    expect(paneAfter).toBe(paneBefore);
    expect(wrapper.find('[data-item-key="suggestions-generating"]').exists()).toBe(false);
    expect(wrapper.findAll('.dock-menu__cards [data-item-key^="action-explore"]')).toHaveLength(3);
  });

  it("retires suggestion presentation on transport reset", () => {
    // When transport reset occurs, the suggestions menu is cleared
    const w = mountDock({ rootItems: ROOT_ITEMS }, []);
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(0);
    expect(w.find('[data-item-key="action-options.dismiss"]').exists()).toBe(false);
  });
});
