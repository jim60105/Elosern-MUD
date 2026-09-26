// webclient-align-11-dialogue-ux (task 2.4): the dock has NO dialogue form.
// In dialogue mode the dock renders its ordinary exploration chrome — the
// scene overview (webclient-scene-overview-swap), the single regular legend,
// and never a `對話選項` tab or a tab bar. (The mirror form these tests used
// to pin is deleted; the caption is the ONE dialogue presentation.)
import { h } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ActionDock from "../components/ActionDock.vue";
import SceneOverview from "../components/SceneOverview.vue";
import ExplorationMenu from "../lib/exploration_menu.js";
import { explorationPanel } from "./store/protocol_fixtures.js";

const ROOT_ITEMS = [
  { key: "exit-east", label: "西風酒館", enabled: true },
  { key: "target-7", label: "店長", enabled: true },
  { key: "wait", label: "等待／休息", enabled: true },
];

const VIEW = { dockDepth: 1, dockTrail: [], activeSubDock: null };

// The scene overview the AppClient pane host renders in dialogue mode: the
// same `overviewMenu` the exploration root's resolver returns.
const OVERVIEW = ExplorationMenu.overviewMenu(explorationPanel(), {
  currentNode: "room:42",
  suggestions: null,
});

describe("dock keeps its ordinary form in dialogue mode", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  function mountDock(props = {}) {
    wrapper = mount(ActionDock, {
      props: { mode: "dialogue", rootItems: ROOT_ITEMS, view: VIEW, ...props },
      slots: { default: () => [h(SceneOverview, { menu: OVERVIEW })] },
    });
    return wrapper;
  }

  it("renders the scene overview in dialogue mode — never a tab bar or a 對話選項 tab", () => {
    const w = mountDock();
    expect(w.find(".dock-tab-bar").exists()).toBe(false);
    const overview = w.get('[data-testid="scene-overview"]');
    const keys = overview.findAll("[data-item-key]").map((el) => el.attributes("data-item-key"));
    expect(keys).toEqual([
      "exit-east",
      "exit-north",
      "target-7",
      "object-3",
      "look-room",
      "wait",
    ]);
    expect(w.text()).not.toContain("對話選項");
  });

  it("keeps the single regular legend while in dialogue mode", () => {
    const w = mountDock();
    const legends = w.findAll('[data-testid="action-dock-description"]');
    expect(legends).toHaveLength(1);
    expect(legends[0].text()).toBe("數字鍵 1–9 · Enter 執行 · Esc 返回");
    // The deleted dialogue legend wording never appears.
    expect(w.text()).not.toContain("指令列自由對話");
  });

  it("the legend is identical across exploration and dialogue modes", () => {
    const talk = mountDock();
    const talkLegend = talk.get('[data-testid="action-dock-description"]').text();
    const explore = mountDock({ mode: "exploration" });
    expect(explore.get('[data-testid="action-dock-description"]').text()).toBe(talkLegend);
  });

  it("an overview chip activation routes through the shared dock handler", async () => {
    const w = mountDock();
    const chip = w
      .findAll("[data-item-key]")
      .find((el) => el.attributes("data-item-key") === "wait");
    await chip.trigger("click");
    const overview = w.findComponent(SceneOverview);
    expect(overview.emitted("activate")[0][0].key).toBe("wait");
    expect(w.emitted("action")).toBeUndefined();
  });
});
