// webclient-align-08-dialogue-surface (tasks 3.2/4.2): the dock dialogue form
// — the legend swaps to the draft's dialogue hint INSIDE the same single
// legend element while the dialogue form presents, and the single `對話選項`
// tab renders without a pick leak into the tab bar.

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ActionDock from "../components/ActionDock.vue";
import { DIALOGUE_TAB_KEY, DIALOGUE_TAB_LABEL } from "../stores/dialogue-view.js";

const ROOT_ITEMS = [
  { key: "move", label: "移動", enabled: true },
  { key: "look", label: "查看", enabled: true },
];

const DIALOGUE_ROOT_ITEM = {
  key: DIALOGUE_TAB_KEY,
  label: DIALOGUE_TAB_LABEL,
  enabled: true,
  navigation: true,
  surface: DIALOGUE_TAB_KEY,
};

const VIEW = { dockDepth: 1, dockTrail: [], activeSubDock: null };

describe("dock dialogue form legend", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  function mountDock(props) {
    wrapper = mount(ActionDock, {
      props: { mode: "dialogue", rootItems: ROOT_ITEMS, view: VIEW, ...props },
    });
    return wrapper;
  }

  it("swaps to the reference dialogue hint while the dialogue form presents", () => {
    const w = mountDock({ dialogueForm: true });
    const legends = w.findAll('[data-testid="action-dock-description"]');
    expect(legends).toHaveLength(1);
    const legend = legends[0];
    expect(legend.text()).toBe("數字鍵 1–4 選 · → 指令列自由對話");
    const kbds = legend.findAll("kbd");
    expect(kbds.map((k) => k.text())).toEqual(["→"]);
  });

  it("keeps the regular legend and the single instance outside the dialogue form", () => {
    const w = mountDock({ mode: "exploration", dialogueForm: false });
    const legends = w.findAll('[data-testid="action-dock-description"]');
    expect(legends).toHaveLength(1);
    expect(legends[0].text()).toBe("數字鍵 1–4 · Enter 執行 · Esc 返回");
    expect(legends[0].findAll("kbd").map((k) => k.text())).toEqual(["Enter", "Esc"]);
  });

  it("flipping the form swaps the wording inside the SAME legend element", async () => {
    const w = mountDock({ dialogueForm: false });
    const before = w.get('[data-testid="action-dock-description"]').element;
    await w.setProps({ dialogueForm: true });
    const after = w.get('[data-testid="action-dock-description"]').element;
    expect(w.findAll('[data-testid="action-dock-description"]')).toHaveLength(1);
    // Same DOM element, new wording — never a second copy.
    expect(after).toBe(before);
    expect(after.textContent).toContain("指令列自由對話");
  });

  it("the dialogue root renders one inert 對話選項 tab (picks live in the pane)", () => {
    const w = mountDock({ dialogueForm: true, rootItems: [DIALOGUE_ROOT_ITEM] });
    const tabs = w.findAll(".dock-tab-bar__tab");
    expect(tabs).toHaveLength(1);
    expect(tabs[0].text()).toBe(DIALOGUE_TAB_LABEL);
    expect(tabs[0].attributes("data-item-key")).toBe(DIALOGUE_TAB_KEY);
  });

  it("clicking the sole tab requests the shared tab entry (a no-op confirm at the dialogue root)", async () => {
    const w = mountDock({ dialogueForm: true, rootItems: [DIALOGUE_ROOT_ITEM] });
    await w.findAll(".dock-tab-bar__tab")[0].trigger("click");
    // The click emits the tab key through the shared handler; the store's
    // focusItemByKey('dlg-options') fails against the dialogue root rows, so
    // nothing can confirm (asserted at store level in dialogue_store.test.js).
    expect(w.emitted("tab-click")).toEqual([[DIALOGUE_TAB_KEY]]);
  });
});
