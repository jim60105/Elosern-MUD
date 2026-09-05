// webclient-align-11-dialogue-ux (task 2.4): the dock has NO dialogue form.
// In dialogue mode the dock renders its ordinary exploration chrome — the
// usual tabs, the single regular legend, and never a `對話選項` tab. (The
// mirror form these tests used to pin is deleted; the caption is the ONE
// dialogue presentation.)

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ActionDock from "../components/ActionDock.vue";

const ROOT_ITEMS = [
  { key: "move", label: "移動", enabled: true },
  { key: "look", label: "查看", enabled: true },
  { key: "interact", label: "互動", enabled: true },
  { key: "wait", label: "等待", enabled: true },
];

const VIEW = { dockDepth: 1, dockTrail: [], activeSubDock: null };

describe("dock keeps its ordinary form in dialogue mode", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  function mountDock(props = {}) {
    wrapper = mount(ActionDock, {
      props: { mode: "dialogue", rootItems: ROOT_ITEMS, view: VIEW, ...props },
    });
    return wrapper;
  }

  it("renders the ordinary tabs in dialogue mode — never a 對話選項 tab", () => {
    const w = mountDock();
    const tabs = w.findAll(".dock-tab-bar__tab");
    expect(tabs.map((t) => t.text())).toEqual(["移動", "查看", "互動", "等待"]);
    expect(w.text()).not.toContain("對話選項");
  });

  it("keeps the single regular legend while in dialogue mode", () => {
    const w = mountDock();
    const legends = w.findAll('[data-testid="action-dock-description"]');
    expect(legends).toHaveLength(1);
    expect(legends[0].text()).toBe("數字鍵 1–4 · Enter 執行 · Esc 返回");
    // The deleted dialogue legend wording never appears.
    expect(w.text()).not.toContain("指令列自由對話");
  });

  it("the legend is identical across exploration and dialogue modes", () => {
    const talk = mountDock();
    const talkLegend = talk.get('[data-testid="action-dock-description"]').text();
    const explore = mountDock({ mode: "exploration" });
    expect(explore.get('[data-testid="action-dock-description"]').text()).toBe(talkLegend);
  });

  it("tab clicks route ordinary exploration keys through the shared handler", async () => {
    const w = mountDock();
    await w.findAll(".dock-tab-bar__tab")[2].trigger("click");
    expect(w.emitted("tab-click")).toEqual([["interact"]]);
  });
});
