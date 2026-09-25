// webclient-scene-overview-component (task 4.4): the scene overview renders
// the real `overviewMenu` as chip rows through the shared row renderer.

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import SceneOverview from "../../components/SceneOverview.vue";
import {
  AFFORDANCES,
  explorationPanelFixture,
  localMapFixture,
  overviewArgs,
} from "../../stories/fixtures/scene_overview.js";

const ROOM = explorationPanelFixture({
  exits: [
    { ref: "n", label: "北", destination: "room:1" },
    { ref: "door", label: "櫃檯門", destination: "room:2", enabled: false, reason: "門鎖著。" },
  ],
  targets: [{ identity: 11, name: "試驗守衛", affordances: [AFFORDANCES.talk] }],
  objects: [{ identity: 31, name: "試驗箱" }],
});
const MAP = localMapFixture([
  ["room:1", "北側大道"],
  ["room:2", "櫃檯"],
]);

describe("SceneOverview", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  function mountOverview(panel = ROOM, options = {}, props = {}) {
    wrapper = mount(SceneOverview, {
      attachTo: document.body,
      props: { ...overviewArgs(panel, { localMap: MAP, ...options }), ...props },
    });
    return wrapper;
  }

  const chipKeys = (w) =>
    w.findAll('[data-testid="dock-item"]').map((chip) => chip.attributes("data-item-key"));

  it("renders the rows in reading order and no row or label for an absent section", () => {
    const panel = explorationPanelFixture({
      exits: [{ ref: "n", label: "北", destination: "room:1" }],
      objects: [{ identity: 31, name: "試驗箱" }],
    });
    const w = mountOverview(panel);
    const rows = w.findAll(".scene-overview__row").map((row) => row.attributes("data-section"));
    expect(rows).toEqual(["exits", "objects", "footer"]);
    expect(w.find('[data-testid="scene-overview-people"]').exists()).toBe(false);
    expect(w.text()).not.toContain("人物");
    expect(w.get('[data-testid="scene-overview-exits"] .scene-overview__label').text()).toBe("出口");
    expect(w.get('[data-testid="scene-overview-footer"]').find(".scene-overview__label").exists()).toBe(false);
  });

  it("gives every chip its row key and a row id in reading order", () => {
    const w = mountOverview();
    expect(chipKeys(w)).toEqual([
      "exit-n",
      "exit-door",
      "target-11",
      "object-31",
      "look-room",
      "wait",
    ]);
    w.findAll('[data-testid="dock-item"]').forEach((chip, index) => {
      expect(chip.attributes("id")).toBe(`exploration-row-${index}`);
    });
  });

  it("shows the direction glyph and destination name, and a disabled exit keeps its own label", () => {
    const w = mountOverview();
    const north = w.get('[data-item-key="exit-n"]');
    expect(north.get(".dock-menu-item__glyph").text()).toBe("↑");
    expect(north.get(".dock-menu-item__label").text()).toBe("北側大道");
    const door = w.get('[data-item-key="exit-door"]');
    expect(door.get(".dock-menu-item__label").text()).toBe("櫃檯門");
    expect(door.text()).toContain("（無法使用）");
    expect(door.text()).not.toContain("（無法通行）");
    expect(door.attributes("aria-describedby")).toBe("exploration-row-1-reason");
    expect(w.get("#exploration-row-1-reason").text()).toBe("門鎖著。");
  });

  it("focuses a disabled chip on click without activating it, and the reason strip explains it", async () => {
    const w = mountOverview();
    expect(w.find('[data-testid="exploration-detail"]').exists()).toBe(false);
    await w.get('[data-item-key="exit-door"]').trigger("click");
    expect(w.emitted("focus-change")).toEqual([["exit-door"]]);
    expect(w.emitted("activate")).toBeUndefined();
    await w.setProps({ focusedKey: "exit-door" });
    expect(w.get('[data-testid="exploration-detail"]').text()).toBe("門鎖著。");
  });

  it("emits focus-change then activate for an enabled chip", async () => {
    const w = mountOverview();
    await w.get('[data-item-key="target-11"]').trigger("click");
    expect(w.emitted("focus-change")).toEqual([["target-11"]]);
    const [[payload]] = w.emitted("activate");
    expect(payload.key).toBe("target-11");
    expect(payload.item.openTarget).toBe(11);
  });

  it("follows focusedKey with aria-activedescendant and scrolls the chip into view", async () => {
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    const w = mountOverview();
    const list = w.get('[data-testid="dock-menu"]');
    expect(list.attributes("aria-activedescendant")).toBeUndefined();
    await w.setProps({ focusedKey: "object-31" });
    await nextTick();
    expect(list.attributes("aria-activedescendant")).toBe("exploration-row-3");
    expect(w.get('[data-item-key="object-31"]').classes()).toContain("dock-menu-item--focused");
    expect(scroll).toHaveBeenCalledWith({ block: "nearest", inline: "nearest" });
    expect(scroll.mock.contexts.at(-1)).toBe(w.get('[data-item-key="object-31"]').element);
    delete Element.prototype.scrollIntoView;
  });

  it("is the single tab stop while active, and inert with no dock-menu hook while inactive", async () => {
    const w = mountOverview();
    const list = w.get('[role="listbox"]');
    expect(list.attributes("tabindex")).toBe("0");
    expect(list.attributes("data-testid")).toBe("dock-menu");
    expect(w.get('[data-testid="scene-overview"]').attributes("inert")).toBeUndefined();
    await w.setProps({ active: false });
    expect(list.attributes("tabindex")).toBe("-1");
    expect(list.attributes("data-testid")).toBeUndefined();
    const root = w.get('[data-testid="scene-overview"]');
    expect(root.attributes("inert")).toBeDefined();
    expect(root.attributes("aria-hidden")).toBe("true");
  });
});
