// webclient-scene-overview-swap (task 4.5): the AppClient composition contract
// for the exploration dock's root. exploration-exit-compass moved the exits to
// the compass, exploration-presence-rail the people and objects to the
// presence rail on the stage (tests/app_client_presence_rail.test.js), and
// exploration-room-actions retired the scene overview itself: the room actions
// are the place card's and the 建議 pill's
// (tests/app_client_room_actions.test.js), so the command panel holds the
// compass, the pill, and the readout. The move/look/interact tab root is gone;
// only the combat root keeps a tab bar.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

// A room with two exits (one locked), one dialogue host, and one object — the
// same shape the live presenter ships.
function explorationPanel(overrides = {}) {
  return fx.explorationPanel(overrides);
}

describe("AppClient scene overview (webclient-scene-overview-swap)", () => {
  let store;
  let wrapper;

  function mountAppClient() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    return wrapper;
  }

  function commitPanels(panels = undefined) {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            status: fx.statusPanel(),
            exploration: panels || explorationPanel(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
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

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the compass, the pill, and the readout at the exploration root with no tab bar", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    expect(store.view.dockSource).toBe("exploration.root");
    // The root pane (exploration-room-actions D2): the compass on the left,
    // then a right column with the 建議 pill over the readout.
    const root = wrapper.get('#action-dock [data-testid="exploration-root"]');
    const [left, right] = root.element.children;
    expect(left.querySelector('[data-testid="exit-compass"]')).not.toBeNull();
    expect(Array.from(right.children).map((el) => el.getAttribute("data-testid"))).toEqual([
      "suggestions-pill",
      "exploration-readout",
    ]);
    // No retired surface: no scene overview, chip, footer, or row container.
    expect(wrapper.find('[data-testid="scene-overview"]').exists()).toBe(false);
    expect(wrapper.find("#action-dock [data-item-key]").exists()).toBe(false);
    expect(wrapper.find('#action-dock [data-testid="dock-menu"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="exploration-detail"]').exists()).toBe(false);
    expect(wrapper.find(".waiting-screen").exists()).toBe(false);
    expect(wrapper.findAll('#action-dock [data-testid="exit-compass-pip"], #action-dock [data-testid="exit-compass-portal"]').map((el) => el.attributes("data-exit-ref")).sort()).toEqual(["east", "north"]);
    // The host's medallion and the object's lozenge stand on the rail.
    expect(
      wrapper.findAll('[data-anchor="presence"] [data-testid="presence-entry"]').map((el) => el.attributes("data-presence")),
    ).toEqual(["target", "object"]);
    expect(wrapper.find('#action-dock [data-pane-kind="commands"]').exists()).toBe(false);
    // The exploration panel shows no key-hint legend.
    expect(wrapper.find('[data-testid="action-dock-description"]').exists()).toBe(false);
    // The readout idles with the exit and presence counts.
    expect(wrapper.get('[data-testid="exploration-readout-text"]').text()).toBe(
      `出口 ${fx.explorationPanel().move.length} · 在場 1`,
    );
  });

  it("entering exploration focuses the compass", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(wrapper.get('[data-testid="exit-compass"]').element);
  });

  it("a compass move submits the exit row's payload, and a disabled exit explains itself in the readout", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();
    const sender = fx.createFakeSender();
    store.setSender(sender);
    const compass = wrapper.get('[data-testid="exit-compass"]');
    // Cycle to the locked exit: Enter sends nothing and the readout shows
    // the server-authored reason.
    for (let i = 0; i < 4 && compass.attributes("data-aim-ref") !== "north"; i += 1) {
      await compass.trigger("keydown", { key: "]" });
    }
    expect(compass.attributes("data-aim-ref")).toBe("north");
    expect(wrapper.get('[data-testid="exploration-readout-lead"]').text()).toBe("無法通行");
    expect(wrapper.get('[data-testid="exploration-readout-text"]').text()).toBe("門被鎖住了");
    await compass.trigger("keydown", { key: "Enter" });
    await compass.trigger("keyup", { key: "Enter" });
    expect(sender.sent.actions).toHaveLength(0);
    // Cycle to the open exit and move once.
    while (compass.attributes("data-aim-ref") !== "east") {
      await compass.trigger("keydown", { key: "]" });
    }
    await compass.trigger("keydown", { key: "Enter" });
    await compass.trigger("keyup", { key: "Enter" });
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.move",
      payload: { exit_ref: "east", current_node: "room:42" },
    });
  });

  it("aiming lights the destination on the minimap", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();
    const compass = wrapper.get('[data-testid="exit-compass"]');
    while (compass.attributes("data-aim-ref") !== "east") {
      await compass.trigger("keydown", { key: "]" });
    }
    const destination = fx.explorationPanel().move.find((row) => row.exit_ref === "east").destination;
    const aimed = () => wrapper.findAll(".local-map .local-map__node--aimed").map((n) => n.attributes("data-node-id"));
    expect(aimed()).toEqual([destination]);
    await compass.trigger("keydown", { key: "Escape" });
    expect(aimed()).toEqual([]);
  });

  it("keeps the tab bar on the combat root", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          mode: "combat",
          panels: {
            status: fx.statusPanel(),
            context_actions: fx.combatActions(),
            local_map: fx.localMapPanel(),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    await wrapper.vm.$nextTick();

    expect(store.view.dockSource).toBe("combat.root");
    // The combat root is the pane's vertical command list
    // (webclient-combat-command-window), the only row container.
    const menus = wrapper.findAll('#action-dock [data-testid="dock-menu"]');
    expect(menus).toHaveLength(1);
    expect(menus[0].attributes("data-pane-kind")).toBe("commands");
    expect(wrapper.find('[data-testid="scene-overview"]').exists()).toBe(false);
    expect(menus[0].findAll("[data-item-key]").map((row) => row.attributes("data-item-key"))).toEqual([
      "attack", "skills", "items", "bag", "defend", "flee", "forfeit",
    ]);
  });
});
