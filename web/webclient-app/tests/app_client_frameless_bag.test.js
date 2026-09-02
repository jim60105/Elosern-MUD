// make-inventory-drawer-frameless (task 3.4): the composition contract. With
// the bag drawer open — including after hosted-style navigation — no hosted
// row container or detail pane renders inside the drawer body while the
// 商店 drawer still hosts its frame's rows (regression). The 背包 dock row
// carries no `›` nav chevron (the chevronless 角色 precedent), and each of
// the three close routes — Escape, the close control, the scrim — restores
// focus to the 背包 entry that opened it with the router untouched.
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { CHARACTER_PANEL_SAMPLE, SERVICES_PANEL_SAMPLE } from "../stories/fixtures.js";
import ServiceMenu from "../lib/service_menu.js";
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

  function openBagFromRow(rowEl) {
    rowEl.focus();
    expect(store.focusItemByKey("inventory")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
  });

  it("opens the bag frameless with no hosted row region and returns focus on every close route", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    const row = wrapper.get('[data-item-key="inventory"]');
    // The frameless drawer-open row follows the chevronless 角色 precedent:
    // the `›` chevron means "opens a deeper frame" and must not render.
    expect(row.find(".dock-menu__nav-chevron").exists()).toBe(false);

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
      openBagFromRow(row.element);
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
      expect(store.router.currentMenu().title, name).toBe("探索");
    }
  });

  it("keeps 商店 hosting intact and renders no row region in the bag after hosted-style navigation", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    // Hosted-style navigation into the shop surface: the 貨架 frame stays
    // hosted in the 商店 drawer (regression — the frozen hosting surface).
    store.setActiveSubDock("services");
    store.router.pushFrame({ source: "services.root", params: {} });
    expect(store.focusItemByKey("shop")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.focusItemByKey("stock")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    await wrapper.vm.$nextTick();
    let drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.find('[data-testid="shop-panel"]').exists()).toBe(true);
    expect(drawer.find('[data-testid="dock-menu"]').exists()).toBe(true);
    // The hosted drawer's close follows the declarative contract
    // (webclient-services-combat-creation-frames): exactly one pop of the
    // hosted 貨架 frame, the drawer closes once, and the hosted parent
    // 商店 frame stays current with its sub-dock — no root re-home.
    const hostedDepth = store.router.depth();
    await wrapper.get('[data-testid="hud-drawer-close"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(store.router.depth()).toBe(hostedDepth - 1);
    expect(store.view.activeSubDock).toBe("services");
    expect(store.router.currentDescriptor().source).toBe("services.shop");
    // The player then escapes the remaining shop levels back to the root
    // (the bag entry row lives in the root dock).
    store.router.popMenu();
    store.router.popMenu();
    await wrapper.vm.$nextTick();
    expect(store.router.currentDescriptor().source).toBe("exploration.root");

    // The bag opened after that hosted navigation still renders no row
    // region, and its close leaves the router alone (the re-homed root
    // frame may still sit above the popped stack from the store-constructed
    // services root: the contract is that open+close change nothing).
    const depthBeforeBag = store.router.depth();
    openBagFromRow(wrapper.get('[data-item-key="inventory"]').element);
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
