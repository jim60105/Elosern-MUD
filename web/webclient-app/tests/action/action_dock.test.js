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

  function mountDock(props = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ActionDock, {
      attachTo: host,
      props: { mode: "exploration", ...props },
      slots: {
        default: () => [h(DockMenu, { items: AFFORDANCES })],
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
    expect(w.get('[data-testid="action-dock-description"]').text()).toBe(
      "附近動作　方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列",
    );
  });

  it("renders the bare shortcut legend without a prefix", () => {
    const w = mountDock();
    expect(w.get('[data-testid="action-dock-description"]').text()).toBe(
      "方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列",
    );
  });

  it("renders ready suggestions as the exact card shapes plus dismiss", () => {
    const w = mountDock({ suggestions: READY });
    const section = w.get('[data-testid="suggestions-section"]');
    expect(section.attributes("role")).toBe("region");
    expect(section.attributes("aria-label")).toBe("AI 建議");
    expect(
      w.get('[data-testid="suggestions-dismiss"]').text(),
    ).toBe("✕ 清除建議");
    const cards = w.findAll('[data-testid="option-card"]');
    expect(cards).toHaveLength(3);
    expect(cards[1].get(".option-card-hint").text()).toBe("先休息一會兒再行動");
    expect(w.find('[data-testid="suggestions-generating"]').exists()).toBe(false);
  });

  it("emits the exact OOB action intent for a ready card activation", async () => {
    const w = mountDock({ suggestions: READY });
    const cards = w.findAll('[data-testid="option-card"]');
    await cards[0].trigger("click");
    expect(w.emitted("action")).toHaveLength(1);
    expect(w.emitted("action")[0][0]).toEqual({
      action_id: "explore.look",
      payload: { room: true },
    });
    await cards[2].trigger("click");
    expect(w.emitted("action")).toHaveLength(2);
    expect(w.emitted("action")[1][0]).toEqual({
      action_id: "explore.talk_freeform",
      payload: { npc_id: 9, speech: "我們聊聊好嗎？" },
    });
  });

  it("emits the options.dismiss intent with the exact empty payload", async () => {
    const w = mountDock({ suggestions: READY });
    await w.get('[data-testid="suggestions-dismiss"]').trigger("click");
    expect(w.emitted("action")[0][0]).toEqual({
      action_id: "options.dismiss",
      payload: {},
    });
  });

  it("renders the generating state as one muted line with no cards", () => {
    const w = mountDock({ suggestions: { status: "generating" } });
    expect(
      w.get('[data-testid="suggestions-generating"]').text(),
    ).toBe("AI 正在構思建議…");
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(0);
    expect(w.find('[data-testid="suggestions-dismiss"]').exists()).toBe(false);
  });

  it("renders degraded 0 cards as the note plus the empty-state line", () => {
    const w = mountDock({ suggestions: { status: "degraded", cards: [] } });
    expect(
      w.get('[data-testid="suggestions-note"]').text(),
    ).toBe("AI 建議目前不可用");
    expect(
      w.get('[data-testid="suggestions-empty"]').text(),
    ).toBe("現在沒有什麼值得做的動作");
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(0);
  });

  it("renders degraded rule cards with the note present", () => {
    const w = mountDock({
      suggestions: {
        status: "degraded",
        cards: [
          {
            kind: "known_action",
            action_code: "explore.look",
            label: "查看房間",
            params: { room: true },
          },
        ],
      },
    });
    expect(w.get('[data-testid="suggestions-note"]').exists()).toBe(true);
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(1);
    expect(w.find('[data-testid="suggestions-empty"]').exists()).toBe(false);
  });

  it("renders nothing for the unavailable suggestions state", () => {
    const w = mountDock({ suggestions: { status: "unavailable" } });
    expect(w.find('[data-testid="suggestions-section"]').exists()).toBe(false);
  });

  it("omits the suggestions section entirely when the slice is absent", () => {
    const w = mountDock();
    expect(w.find('[data-testid="suggestions-section"]').exists()).toBe(false);
  });

  it("reacts to committed slice changes without remounting the dock", async () => {
    const w = mountDock({ suggestions: { status: "generating" } });
    const root = w.get('[data-testid="action-dock"]').element;
    expect(w.get('[data-testid="suggestions-generating"]').exists()).toBe(true);
    w.setProps({ suggestions: READY });
    await nextTick();
    expect(w.find('[data-testid="action-dock"]').element).toBe(root);
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(3);
    w.setProps({ suggestions: { status: "unavailable" } });
    await nextTick();
    expect(w.find('[data-testid="action-dock"]').element).toBe(root);
    expect(w.find('[data-testid="suggestions-section"]').exists()).toBe(false);
  });

  it("refreshes the guidance note when the surface prefix changes", async () => {
    const w = mountDock({ guidancePrefix: "附近動作" });
    expect(w.get('[data-testid="action-dock-description"]').text()).toBe(
      "附近動作　方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列",
    );
    w.setProps({ guidancePrefix: "戰鬥動作" });
    await nextTick();
    expect(w.get('[data-testid="action-dock-description"]').text()).toBe(
      "戰鬥動作　方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列",
    );
  });

  it("renders exactly one visible legend: the description is hidden, the tab-bar hint is the visible copy", () => {
    // Mount with rootItems so the tab bar (and its trailing hint) renders;
    // the default mount has no tabs, so the duplicate copy check needs the
    // tab-bar present to be meaningful.
    const w = mountDock({ rootItems: ROOT_ITEMS });
    const desc = w.get('[data-testid="action-dock-description"]');
    const descStyle = getComputedStyle(desc.element);
    // Assert the rendered state, not merely the class-name presence: the
    // element is 1x1, absolutely positioned, and clipped.
    expect(desc.attributes("aria-hidden")).toBe("true");
    expect(desc.classes()).toContain("visually-hidden");
    expect(descStyle.position).toBe("absolute");
    expect(descStyle.width).toBe("1px");
    expect(descStyle.height).toBe("1px");
    if (descStyle.clip) {
      expect(descStyle.clip).toMatch(/0px,\s*0px,\s*0px,\s*0px/);
    }
    const hint = w.find(".dock-tab-bar__hint");
    expect(hint.exists()).toBe(true);
    expect(hint.text()).toBe("方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列");
    const hintStyle = getComputedStyle(hint.element);
    expect(hintStyle.display).not.toBe("none");
    expect(hintStyle.width).not.toBe("1px");
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
});
