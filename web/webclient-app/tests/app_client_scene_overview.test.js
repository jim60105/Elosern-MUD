// webclient-scene-overview-swap (task 4.5): the AppClient composition contract
// for the exploration dock's new root. The dock's root frame is ONE scene
// overview — exits, people, objects, and a footer in one frame — and a person
// chip opens that target's verb popover over the inert overview, inside the
// command region. The move/look/interact tab root and the two-step interaction
// workspace are gone; only the combat root keeps a tab bar.
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

  function chip(key) {
    return wrapper.find(`#action-dock [data-item-key="${key}"]`);
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

  it("renders the overview at the exploration root with no tab bar", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    expect(store.view.dockSource).toBe("exploration.root");
    const overview = wrapper.get('[data-testid="scene-overview"]');
    // One frame: the 出口 / 人物 / 物件 rows and the label-less footer.
    expect(overview.findAll("[data-section]").map((row) => row.attributes("data-section"))).toEqual([
      "exits",
      "people",
      "objects",
      "footer",
    ]);
    expect(chip("exit-east").exists()).toBe(true);
    expect(chip("target-7").exists()).toBe(true);
    expect(chip("object-3").exists()).toBe(true);
    expect(chip("look-room").exists()).toBe(true);
    expect(chip("wait").exists()).toBe(true);
    // The active overview listbox is the dock's row container and single tab
    // stop; the retired tab root's entries are gone.
    expect(overview.find('[data-testid="dock-menu"]').exists()).toBe(true);
    expect(wrapper.find("#action-dock .dock-tab-bar").exists()).toBe(false);
    for (const gone of ["move", "look", "interact", "character"]) {
      expect(wrapper.find(`#action-dock [data-item-key="${gone}"]`).exists()).toBe(false);
    }
    // The legend renders exactly once, as the dock's own strip.
    expect(wrapper.findAll('[data-testid="action-dock-description"]')).toHaveLength(1);
  });

  it("opens the verb popover from a person chip, inerts the overview, and 查看 submits one explore.look", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();
    const sender = fx.createFakeSender();
    store.setSender(sender);

    await chip("target-7").trigger("click");
    await wrapper.vm.$nextTick();

    expect(store.view.dockSource).toBe("exploration.target");
    const popover = wrapper.get('[data-testid="verb-popover"]');
    // The target's affordances in payload order, then 查看, then back.
    expect(popover.findAll("[data-item-key]").map((row) => row.attributes("data-item-key"))).toEqual([
      "talk-open",
      "look-target",
      "back",
    ]);
    // The overview beneath is inert ancestor chrome: no focus, no tab stop,
    // no second row container.
    const overview = wrapper.get('[data-testid="scene-overview"]');
    expect(overview.attributes("inert")).toBeDefined();
    expect(overview.attributes("aria-hidden")).toBe("true");
    expect(overview.find('[data-testid="dock-menu"]').exists()).toBe(false);
    expect(popover.find('[data-testid="dock-menu"]').exists()).toBe(true);
    // The popover's card renders inside the command region, in the dock's
    // overlay layer (a sibling of the pane), never inside the pane host.
    expect(wrapper.find('#action-dock [data-testid="verb-popover-layer"]').exists()).toBe(true);
    expect(wrapper.find('.action-dock__pane [data-testid="verb-popover"]').exists()).toBe(false);

    // 查看 submits exactly one explore.look for the target and pushes nothing.
    expect(sender.sent.actions).toHaveLength(0);
    await popover.find('[data-item-key="look-target"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.look",
      payload: { target_id: 7 },
    });
    expect(store.router.depth()).toBe(2);
  });

  it("closes the popover on an outside press and on Escape, with the chip focused and the dock holding DOM focus", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    for (const close of ["outside-press", "escape"]) {
      await chip("target-7").trigger("click");
      await wrapper.vm.$nextTick();
      expect(store.router.depth()).toBe(2);

      if (close === "outside-press") {
        // A press on the layer outside the card closes exactly as the back row
        // does.
        await wrapper.get('[data-testid="verb-popover-layer"]').trigger("pointerdown");
      } else {
        // Escape is the keyboard bridge's claim (installed in main.js, not by
        // the component tree): the store entry is the same router press.
        expect(store.focusEscape()).toBe(true);
      }
      await wrapper.vm.$nextTick();

      expect(store.view.dockSource, close).toBe("exploration.root");
      expect(store.router.depth(), close).toBe(1);
      expect(store.view.focus.key, close).toBe("target-7");
      expect(wrapper.find('[data-testid="verb-popover"]').exists(), close).toBe(false);
      // The dock element keeps DOM focus across the popover (design D5).
      const active = document.activeElement;
      const dock = document.getElementById("action-dock");
      expect(dock.contains(active) || active === dock, close).toBe(true);
    }
  });

  it("returns to the overview when the committed room changes under the popover", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPanels();
    await wrapper.vm.$nextTick();

    await chip("target-7").trigger("click");
    await wrapper.vm.$nextTick();
    expect(store.router.depth()).toBe(2);

    // A move from anywhere — the minimap or a typed command — commits a new
    // room identity: the dock returns to the new room's overview.
    const result = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 3,
          panels: {
            exploration: explorationPanel({
              look: { room: { identity: 77, display_name: "渡口", room: true } },
            }),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    await wrapper.vm.$nextTick();

    expect(store.router.depth()).toBe(1);
    expect(store.view.dockSource).toBe("exploration.root");
    expect(wrapper.find('[data-testid="verb-popover"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="scene-overview"]').exists()).toBe(true);
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
    expect(wrapper.find("#action-dock .dock-tab-bar").exists()).toBe(true);
    expect(wrapper.find('[data-testid="scene-overview"]').exists()).toBe(false);
    expect(wrapper.find("#action-dock .dock-tab-bar [data-item-key='attack']").exists()).toBe(true);
  });
});
