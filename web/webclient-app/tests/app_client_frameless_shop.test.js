// make-shop-drawer-frameless (task 3.3): composition contract for the
// frameless 商店 drawer. With the shop drawer open -- including when a
// shop-family descriptor is forced current -- no hosted row container
// ([data-testid="dock-menu"]) or detail pane ([data-testid="dock-detail"])
// renders inside the drawer and the body's only child surface is
// [data-testid="shop-panel"]; no reference drawer hosts router rows.
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { SERVICES_PANEL_SAMPLE } from "../stories/fixtures.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("frameless 商店 drawer (composition contract)", () => {
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
          mode: "exploration",
          panels: {
            status: fx.statusPanel(),
            services: SERVICES_PANEL_SAMPLE,
            context_actions: fx.explorationActions(),
            exploration: fx.explorationPanel({
              interact: [
                {
                  identity: 7,
                  display_name: "店長",
                  portrait_ref: null,
                  affordances: [
                    { kind: "action", action_id: "explore.talk_scripted", label: "交談", enabled: true, disabled_reason: null },
                    { kind: "navigate", surface: "shop", label: "商店", enabled: true, disabled_reason: null },
                  ],
                },
              ],
            }),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
  });

  it("renders only shop-panel and zero dock-menu/dock-detail inside drawer", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    // Open shop drawer from 店長 navigate row: the dock root is the scene
    // overview (webclient-scene-overview-swap), so the person chip is one
    // activation away.
    expect(store.focusItemByKey("target-7")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.focusItemByKey("service-shop")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    await wrapper.vm.$nextTick();

    let drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.find('[data-testid="shop-panel"]').exists()).toBe(true);
    expect(drawer.findAll('[data-testid="dock-menu"]').length).toBe(0);
    expect(drawer.findAll('[data-testid="dock-detail"]').length).toBe(0);
  });

  it("no drawer ever renders dock-menu or dock-detail inside hud-drawer (task 4.3)", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    const drawers = ["skill", "inventory", "shop", "quest", "lore", "status", "party"];
    const descriptors = [
      { source: "exploration.move", params: {} },
      { source: "exploration.interact", params: {} },
    ];

    for (const drawerName of drawers) {
      for (const descriptor of descriptors) {
        store.router.pushFrame(descriptor);
        store.openHudDrawer(drawerName);
        await wrapper.vm.$nextTick();

        const drawer = wrapper.get('[data-testid="hud-drawer"]');
        expect(drawer.findAll('[data-testid="dock-menu"]').length, `${drawerName} with ${descriptor.source}`).toBe(0);
        expect(drawer.findAll('[data-testid="dock-detail"]').length, `${drawerName} with ${descriptor.source}`).toBe(0);

        // The dock itself still renders exactly the router's current frame
        const dock = wrapper.get('#action-dock');
        expect(dock.find('[data-testid="dock-menu"]').exists(), `dock with ${descriptor.source}`).toBe(true);

        store.closeHudDrawer();
        await wrapper.vm.$nextTick();
      }
    }
  });
});
