// H4 (webclient-hud-04-reference-drawers) store drawer-controller tests:
// the single open-drawer entry (unknown names rejected), the service-frame
// hosting (a current service frame implies its drawer is open), one-level
// frame pop on close, and the commit-path teardown (mode change / transport
// loss closes the services drawers while the status drawer stays openable).
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

// A minimal services panel exposing a guild quest log (drives the 任務記錄
// service frame) so `ServiceMenu.buildMenus` yields a valid `menus.quests`.
function servicesPanel() {
  return {
    schema_version: 3,
    available: true,
    kind: "services",
    host: null,
    player: {
      wallet: 120,
      guild_registered: true,
      guild_rank: "novice",
      guild_merit: 5,
      next_rank: "adept",
      next_threshold: 10,
    },
    guild: {
      registration: {
        registered: true,
        register: {
          action_id: "guild.register",
          label: "申請入會",
          enabled: false,
          disabled_reason: { code: "already", message: "你已加入公會" },
          quantity: null,
        },
      },
      board: [],
      quests: [
        {
          quest_id: "q1",
          definition_key: "q_board_1",
          display_name: "試煉：新手任務",
          state: "in_progress",
          stage_index: 0,
          stage_progress: 0,
          objective_summary: "前往北岸大道，與店長交談",
          deadline_line: null,
          detail: "前往北岸大道，與店長交談以接受試煉。",
          abandon: {
            action_id: "guild.quest_abandon",
            label: "放棄",
            enabled: true,
            disabled_reason: null,
            quantity: null,
          },
          turnin: {
            action_id: "guild.quest_turnin",
            label: "交任務",
            enabled: false,
            disabled_reason: { code: "incomplete", message: "目標尚未完成" },
            quantity: null,
          },
        },
      ],
      rank: null,
    },
    shop: null,
    inventory: null,
    pagination: {
      board_total: 0,
      quest_total: 1,
      stock_total: 0,
      sellable_total: 0,
      inventory_total: 0,
    },
  };
}

function snapshotWithServices() {
  return {
    protocol_version: 1,
    presentation_epoch: fx.EPOCH_A,
    revision: 1,
    mode: "exploration",
    panels: {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      context_actions: fx.explorationActions(),
      services: servicesPanel(),
    },
    layout_version: 1,
    server_time: fx.serverTime(),
  };
}

describe("H4 store reference-drawer controller", () => {
  let store;

  function openSession() {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [snapshotWithServices()], {});
    expect(result.accepted).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
  });

  it("opens the named drawer and rejects an unknown drawer name (task 4.1)", () => {
    openSession();
    expect(store.openHudDrawer("skill")).toBe(true);
    expect(store.view.hudDrawer).toBe("skill");
    expect(store.openHudDrawer("bogus")).toBe(false);
    expect(store.view.hudDrawer).toBe("skill");
    expect(store.openHudDrawer("status")).toBe(true);
    expect(store.view.hudDrawer).toBe("status");
    expect(store.openHudDrawer("lore")).toBe(true);
    expect(store.view.hudDrawer).toBe("lore");
    expect(store.openHudDrawer("party")).toBe(true);
    expect(store.view.hudDrawer).toBe("party");
  });

  it("hosts a current service frame in its drawer (task 4.3): pushing the 任務記錄 frame opens the quest drawer", () => {
    openSession();
    // Navigate the exploration root's 任務 entry to push the guild quest-log
    // service frame (the realistic keyboard path; no state where a service
    // frame is current while its drawer is closed).
    expect(store.focusItemByKey("quests")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.view.hudDrawer).toBe("quest");
  });

  it("closeHudDrawer with popFrame pops exactly one menu level (task 4.2)", () => {
    openSession();
    // Enter the services dock and push the 任務記錄 service frame (the
    // realistic keyboard path), so a service frame is the current frame.
    expect(store.focusItemByKey("quests")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    const depthAtServiceFrame = store.router.depth();
    // The frame-hosting sync opened the quest drawer.
    expect(store.view.hudDrawer).toBe("quest");
    // Closing with popFrame pops exactly one router level (the 任務記錄 frame
    // returns to the services root).
    const ok = store.closeHudDrawer({ popFrame: true });
    expect(ok).toBe(true);
    expect(store.view.hudDrawer).toBe(null);
    expect(store.router.depth()).toBe(depthAtServiceFrame - 1);
  });

  it("closeHudDrawer on party drawer is frameless and leaves router depth and activeSubDock untouched", () => {
    openSession();
    store.setActiveSubDock("services");
    const initialDepth = store.router.depth();
    const initialDescriptor = store.router.currentDescriptor();

    // Open party drawer
    expect(store.openHudDrawer("party")).toBe(true);
    expect(store.view.hudDrawer).toBe("party");

    // Close with popFrame: true
    const ok = store.closeHudDrawer({ popFrame: true });
    expect(ok).toBe(true);
    expect(store.view.hudDrawer).toBe(null);

    // Frameless guarantee: activeSubDock and router stack are not mutated
    expect(store.view.activeSubDock).toBe("services");
    expect(store.router.depth()).toBe(initialDepth);
    expect(store.router.currentDescriptor()).toEqual(initialDescriptor);
  });

  it("a mode change to combat closes the services drawers and leaves the status drawer openable (task 4.4)", () => {
    openSession();
    store.openHudDrawer("quest");
    expect(store.view.hudDrawer).toBe("quest");
    // Commit a snapshot whose mode is now combat.
    const combatSnapshot = {
      protocol_version: 1,
      presentation_epoch: fx.EPOCH_A,
      revision: 2,
      mode: "combat",
      panels: {
        status: fx.statusPanel(),
        context_actions: fx.combatActions(),
      },
      layout_version: 1,
      server_time: fx.serverTime({ minute: 5 }),
    };
    const result = store.receive(1, "ui_snapshot", [combatSnapshot], {});
    expect(result.accepted).toBe(true);
    // The services-backed quest drawer closed on the mode change…
    expect(store.view.hudDrawer).toBe(null);
    // …and the status drawer is still openable in combat.
    expect(store.openHudDrawer("status")).toBe(true);
    expect(store.view.hudDrawer).toBe("status");
    // …and the party drawer is still openable in combat.
    expect(store.openHudDrawer("party")).toBe(true);
    expect(store.view.hudDrawer).toBe("party");
  });
});
