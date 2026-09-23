// make-shop-drawer-frameless (task 3.3): composition contract for the
// frameless 商店 drawer. With the shop drawer open -- including when a
// shop-family descriptor is forced current -- no hosted row container
// ([data-testid="dock-menu"]) or detail pane ([data-testid="dock-detail"])
// renders inside the drawer and the body's only child surface is
// [data-testid="shop-panel"]; the 任務 drawer still hosts its guild frame's
// rows (regression).
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

  it("renders only shop-panel and zero dock-menu/dock-detail inside drawer, even with shop frame forced current", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    // Open shop drawer from 店長 navigate row
    expect(store.focusItemByKey("interact")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.focusItemByKey("target-7")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.focusItemByKey("service-shop")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    await wrapper.vm.$nextTick();

    let drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.find('[data-testid="shop-panel"]').exists()).toBe(true);
    expect(drawer.findAll('[data-testid="dock-menu"]').length).toBe(0);
    expect(drawer.findAll('[data-testid="dock-detail"]').length).toBe(0);

    // Defensive check: force a shop-family descriptor current while shop drawer is open
    store.setActiveSubDock("services");
    store.router.pushFrame({ source: "services.stock", params: {} });
    await wrapper.vm.$nextTick();

    drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.find('[data-testid="shop-panel"]').exists()).toBe(true);
    expect(drawer.findAll('[data-testid="dock-menu"]').length).toBe(0);
    expect(drawer.findAll('[data-testid="dock-detail"]').length).toBe(0);

    // Assert no production handler activation ever sets serviceSurface to "shop"
    expect(store.serviceSurface).not.toBe("shop");
  });

  it("the quest drawer still hosts its guild frame rows (regression)", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    // Hosted-style navigation into guild frame
    store.setActiveSubDock("services");
    store.router.pushFrame({ source: "services.root", params: {} });
    expect(store.focusItemByKey("guild")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.focusItemByKey("board")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    await wrapper.vm.$nextTick();

    const drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.find('[data-testid="quest-drawer"]').exists()).toBe(true);
    expect(drawer.find('[data-testid="dock-menu"]').exists()).toBe(true);
  });
});
