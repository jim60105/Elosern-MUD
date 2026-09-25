// make-inventory-drawer-frameless (task 3.4): the composition contract. With
// the bag drawer open — including after hosted-style navigation — no hosted
// row container or detail pane renders inside the drawer body. Each of the
// three close routes — Escape, the close control, the scrim — restores
// focus to the 背包 entry that opened it with the router untouched.
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { CHARACTER_PANEL_SAMPLE, SERVICES_PANEL_SAMPLE } from "../stories/fixtures.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("frameless 背包 drawer (composition contract)", () => {
  let store;
  let wrapper;

  function mountAppClient() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    return wrapper;
  }

  function commitPanels() {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            context_actions: fx.explorationActions(),
            services: SERVICES_PANEL_SAMPLE,
            character: CHARACTER_PANEL_SAMPLE,
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  function bagButton() {
    return wrapper.get(".desktop-navigation").findAll("button")
      .find((button) => button.text() === "背包");
  }

  async function openBagFromNavigation() {
    const button = bagButton();
    button.element.focus();
    await button.trigger("click");
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
  });

  it("keeps keyboard traversal on visible overview chips after moving reference entries", async () => {
    mountAppClient();
    commitPanels();
    await wrapper.vm.$nextTick();
    const dock = wrapper.get("#action-dock");
    // The exploration root is the scene overview (webclient-scene-overview-
    // swap): its chips are the dock's rendered rows in reading order.
    const keys = ["exit-east", "exit-north", "target-7", "object-3", "look-room", "wait", "suggestions"];
    expect(dock.findAll('[role="option"]').map((item) => item.attributes("data-item-key"))).toEqual(keys);
    for (const key of keys.slice(0, -1)) {
      expect(store.view.focus.key).toBe(key);
      expect(dock.find(`[data-item-key="${key}"][aria-selected="true"]`).exists()).toBe(true);
      store.focusPress("ArrowRight");
      await wrapper.vm.$nextTick();
    }
    expect(store.view.focus.key).toBe("suggestions");
    store.focusPress("ArrowLeft");
    expect(store.view.focus.key).toBe("wait");
    expect(wrapper.get(".desktop-navigation").text()).toContain("角色狀態");
    expect(wrapper.get(".desktop-navigation").text()).toContain("任務");
    expect(wrapper.get(".desktop-navigation").text()).toContain("背包");
  });

  it("opens the bag frameless with no hosted row region and returns focus on every close route", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    const row = bagButton();
    expect(wrapper.find('#action-dock [data-item-key="inventory"]').exists()).toBe(false);

    const routes = {
      "close control": async () => {
        await wrapper.get('[data-testid="hud-drawer-close"]').trigger("click");
      },
      Escape: async () => {
        await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
      },
      scrim: async () => {
        await wrapper.get('[data-testid="hud-drawer-scrim"]').trigger("click");
      },
    };
    for (const [name, closeRoute] of Object.entries(routes)) {
      await openBagFromNavigation();
      await wrapper.vm.$nextTick();
      const drawer = wrapper.get('[data-testid="hud-drawer"]');
      // The bag body is only its own committed-panel stack.
      expect(drawer.find('[data-testid="inventory-panel"]').exists(), name).toBe(true);
      expect(drawer.findAll('[data-testid="dock-menu"]').length, name).toBe(0);
      expect(drawer.findAll('[data-testid="dock-detail"]').length, name).toBe(0);
      expect(store.router.depth(), name).toBe(1);
      expect(store.view.activeSubDock, name).toBe(null);
      await closeRoute();
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-testid="hud-drawer"]').exists(), name).toBe(false);
      // Focus returns to the 背包 entry that opened it; the router is what
      // it was before the open.
      expect(document.activeElement, name).toBe(row.element);
      expect(store.router.depth(), name).toBe(1);
      expect(store.router.currentMenu().title, name).toBe("場景");
    }
  });

  it("renders no row region in the quest drawer or bag drawer", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    // Open quest drawer from top navigation
    store.tabToRootAndConfirm("quests", "pointer");
    await wrapper.vm.$nextTick();
    let drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.find('[data-testid="quest-drawer"]').exists()).toBe(true);
    expect(drawer.findAll('[data-testid="dock-menu"]').length).toBe(0);
    expect(drawer.findAll('[data-testid="dock-detail"]').length).toBe(0);

    const depthBefore = store.router.depth();
    await wrapper.get('[data-testid="hud-drawer-close"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(store.router.depth()).toBe(depthBefore);
    const depthBeforeBag = store.router.depth();
    await openBagFromNavigation();
    await wrapper.vm.$nextTick();
    drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.find('[data-testid="inventory-panel"]').exists()).toBe(true);
    expect(drawer.findAll('[data-testid="dock-menu"]').length).toBe(0);
    expect(drawer.findAll('[data-testid="dock-detail"]').length).toBe(0);
    expect(store.router.depth()).toBe(depthBeforeBag);
    await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="hud-drawer"]').exists()).toBe(false);
    expect(store.router.depth()).toBe(depthBeforeBag);
    expect(store.router.currentDescriptor().source).toBe("exploration.root");
  });
});
