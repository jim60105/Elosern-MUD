// webclient-services-combat-creation-frames (tasks 4.1): the store-level
// declarative-surface contracts after the final cutover. Every family pushes
// ONLY a descriptor, so:
//   - closing a hosted drawer pops exactly one level and discards the
//     surface's local state (the quantity form) with it;
//   - a committed panel removing the hosted surface's frames closes the
//     drawer through the commit-time settle, while a pop that leaves the
//     hosted parent frame current keeps the drawer open (the abandon-
//     confirmation scenario of the drawer-coupling requirement);
//   - a mid-combat panel replacement refreshes the open skill frame by
//     RESOLUTION (no re-push) while the client-local selection survives;
//   - the creation confirm content resolves from the committed state instead
//     of a stored copy;
//   - teardown posts exactly one root DESCRIPTOR per mode.
// The empty-stack read throw is a router contract asserted in the Node gate
// (`keyboard_router_declarative.test.js`).
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import { SERVICES_PANEL_SAMPLE, CREATION_PANEL_SAMPLE } from "../../stories/fixtures.js";
import * as fx from "./protocol_fixtures.js";
import CombatMenu from "../../lib/combat_menu.js";

// The attack row's key is wire vocabulary owned by the combat model
// (BASIC_ATTACK_KEY — the root attack opener resolves it), so the fixture and
// the descriptor assertions below carry the model constant rather than a
// catalog literal (test-data-independence).
const T_ATTACK_KEY = CombatMenu.BASIC_ATTACK_KEY;

// The 店長 carries a navigate-kind shop affordance so the keyboard path can
// reach the shop surface (the affordance row pushes the services.shop frame).
function explorationPanelWithShop(overrides = {}) {
  return fx.explorationPanel(
    deepMergeLocal(
      {
        interact: [
          {
            identity: 7,
            display_name: "店長",
            portrait_ref: null,
            affordances: [
              { kind: "action", action_id: "explore.talk_scripted", label: "交談", enabled: true, disabled_reason: null },
              { kind: "navigate", surface: "shop", label: "商店", enabled: true, disabled_reason: null },
             { kind: "navigate", surface: "guild", label: "公會服務", enabled: true, disabled_reason: null },
            ],
          },
        ],
      },
      overrides,
    ),
  );
}

function deepMergeLocal(base, patch) {
  if (Array.isArray(patch)) return patch;
  const out = { ...base };
  for (const [key, value] of Object.entries(patch)) {
    out[key] =
      value && typeof value === "object" && !Array.isArray(value) && base && typeof base[key] === "object"
        ? deepMergeLocal(base[key], value)
        : value;
  }
  return out;
}

function servicesPanel(overrides = {}) {
  return deepMergeLocal(SERVICES_PANEL_SAMPLE, overrides);
}

function snapshot(overrides = {}) {
  return {
    protocol_version: 1,
    presentation_epoch: fx.EPOCH_A,
    revision: 1,
    mode: "exploration",
    panels: {
      status: fx.statusPanel(),
      exploration: explorationPanelWithShop(),
      context_actions: fx.explorationActions(),
      local_map: fx.localMapPanel(),
      services: servicesPanel(),
    },
    layout_version: 1,
    server_time: fx.serverTime(),
    ...overrides,
  };
}

describe("declarative service/combat/creation surfaces (store)", () => {
  let store;
  let sender;

  function openSession(overrides = {}) {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [snapshot(overrides)], {});
    expect(result.accepted).toBe(true);
  }

  // Open the quest drawer through the top navigation.
  function enterQuests() {
    store.tabToRootAndConfirm("quests", "pointer");
    expect(store.router.currentDescriptor().source).toBe("exploration.root");
    expect(store.view.hudDrawer).toBe("quest");
  }

  // Open the quest drawer via the 店長's navigate affordance.
  function enterGuildSurface() {
    expect(store.focusItemByKey("interact")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.focusItemByKey("target-7")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.focusItemByKey("service-guild")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.router.currentDescriptor().source).toBe("exploration.target");
    expect(store.view.hudDrawer).toBe("quest");
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  describe("frameless quest drawer", () => {
    it("activating service-guild opens quest drawer leaving frame stack and depth unchanged", () => {
      openSession();
      expect(store.focusItemByKey("interact")).toBe(true);
      expect(store.focusConfirm()).toBe(true);
      expect(store.focusItemByKey("target-7")).toBe(true);
      expect(store.focusConfirm()).toBe(true);

      const depthBefore = store.router.depth();
      const descriptorBefore = store.router.currentDescriptor();
      const trailBefore = store.router.trail();

      expect(store.focusItemByKey("service-guild")).toBe(true);
      expect(store.focusConfirm()).toBe(true);

      // Quest drawer opens without pushing a frame or recording a service surface
      expect(store.view.hudDrawer).toBe("quest");
      expect(store.router.depth()).toBe(depthBefore);
      expect(store.router.currentDescriptor()).toEqual(descriptorBefore);
      expect(store.router.trail()).toEqual(trailBefore);
      expect(store.view.activeSubDock).toBe(null);
      expect(store.serviceSurface).toBe(null);

      // A services-panel commit while the quest drawer is open never records a hosted surface or pushes a frame
      const updateSnap = snapshot({ revision: 2 });
      expect(store.receive(1, "ui_snapshot", [updateSnap], {}).accepted).toBe(true);

      expect(store.view.hudDrawer).toBe("quest");
      expect(store.router.depth()).toBe(depthBefore);
      expect(store.router.currentDescriptor()).toEqual(descriptorBefore);
      expect(store.view.activeSubDock).toBe(null);
      expect(store.serviceSurface).toBe(null);
    });

    it("tabToRootAndConfirm('quests') from depth > 1 pops to root and opens quest drawer with depth 1", () => {
      openSession();
      expect(store.focusItemByKey("interact")).toBe(true);
      expect(store.focusConfirm()).toBe(true);
      expect(store.router.depth()).toBe(2);

      store.tabToRootAndConfirm("quests", "pointer");
      expect(store.view.hudDrawer).toBe("quest");
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.activeSubDock).toBe(null);
    });

    it("closing the quest drawer pops nothing and leaves the router unchanged", () => {
      openSession();
      enterGuildSurface();
      const depth = store.router.depth();
      const descriptor = store.router.currentDescriptor();

      expect(store.closeHudDrawer({ popFrame: true })).toBe(true);
      expect(store.view.hudDrawer).toBe(null);
      expect(store.router.depth()).toBe(depth);
      expect(store.router.currentDescriptor()).toEqual(descriptor);
      expect(sender.sent.actions.length).toBe(0);
    });

    it("forced service frame settle-time hosting backward compatibility", () => {
      openSession();
      store.setActiveSubDock("services");
      store.router.pushFrame({ source: "services.root", params: {} });
      expect(store.focusItemByKey("guild")).toBe(true);
      expect(store.focusConfirm()).toBe(true);
      expect(store.router.currentDescriptor().source).toBe("services.guild");
      expect(store.view.hudDrawer).toBe("quest");
      const withoutServices = snapshot();
      delete withoutServices.panels.services;
      withoutServices.revision = 2;
      expect(
        store.receive(1, "ui_snapshot", [withoutServices], {}).accepted,
      ).toBe(true);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.hudDrawer).toBe(null);
    });
  });

  describe("combat frames refresh by resolution", () => {
    const skillsFixture = (targets) => [
      {
        category: "martial_arts",
        label: "武技",
        groups: [
          {
            group: null,
            label: null,
            skills: [
              {
                key: T_ATTACK_KEY,
                label: "攻擊",
                description: "基本攻擊，對單一目標造成傷害。",
                cost: {},
                target_spec: "single",
                element: null,
                enabled: true,
                disabled_reason: null,
                targets,
                shorthands: [],
              },
            ],
          },
        ],
      },
    ];

    it("a mid-fight panel replacement refreshes the open target frame while the selection survives", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { context_actions: fx.combatActions({ skills: skillsFixture([7, 8]) }) } })],
        {},
      );
      expect(store.view.focus.key).toBe("attack");
      // Open the skill: the frame is ONLY the {skillKey} descriptor.
      expect(store.focusPress("Enter")).toBe(true);
      expect(store.router.currentDescriptor()).toEqual({ source: "combat.skill", params: { skillKey: T_ATTACK_KEY } });
      expect(store.view.focus.key).toBe("target-7");
      // Replace the panel mid-fight (the old combatants fall, new ones join).
      const replaced = fx.combatActions({
        skills: skillsFixture([8, 9]),
        participants: [
          {
            identity: 8,
            token: "a1",
            display_name: "同行劍士",
            team: "party",
            state: "active",
            hp_current: 100,
            hp_maximum: 100,
            portrait_ref: null,
          },
          {
            identity: 9,
            token: "e2",
            display_name: "弓手",
            team: "foes",
            state: "active",
            hp_current: 100,
            hp_maximum: 100,
            portrait_ref: null,
          },
        ],
      });
      store.receive(1, "ui_update", [fx.update({ revision: 3, panels: { context_actions: replaced } })], {});
      // The SAME open frame re-resolves: the stack is untouched (no re-push)
      // yet the rows follow the committed panel, and the focused skill key
      // (selection state) is preserved.
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor().source).toBe("combat.skill");
      const rows = store.view.combatMenu.items.map((i) => i.key);
      expect(rows).toEqual(["target-8", "target-9"]);
      expect(store.view.focusedSkill && store.view.focusedSkill.key).toBe(T_ATTACK_KEY);
    });
  });

  describe("creation confirm resolves from the committed state", () => {
    it("the reset-confirm frame posts the descriptor and the overlay slice follows the resolve", () => {
      openSession();
      // A mode change into creation (the teardown re-homes to creation.root).
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, mode: "creation", panels: { creation: CREATION_PANEL_SAMPLE } })],
        {},
      );
      expect(store.router.currentDescriptor().source).toBe("creation.root");
      expect(store.requestCreationReset()).toBe(true);
      expect(store.router.currentDescriptor()).toEqual({
        source: "creation.confirm",
        params: { kind: "reset", presetKey: null },
      });
      expect(store.view.creationView.stage).toBe("confirm");
      expect(store.view.creationView.confirmItems.length).toBeGreaterThan(0);
      expect(store.view.creationView.confirmItems[0].actionId).toBe("creation.reset");
      // The confirm content is resolved, never stored: cancelling pops the
      // confirm descriptor and the overlay slice loses the confirm rows.
      const cancel = store.resolveFrame({ source: "creation.confirm", params: { kind: "reset", presetKey: null } });
      const cancelRow = cancel.items.find((i) => i.key === "cancel-creation.reset");
      expect(store.focusItemByKey(cancelRow.key)).toBe(true);
      expect(store.focusConfirm()).toBe(true);
      expect(store.view.creationView.confirmItems).toEqual([]);
      expect(store.router.currentDescriptor().source).toBe("creation.root");
    });
  });

  describe("teardown posts one root descriptor per mode", () => {
    it("transport loss under an open submenu re-posts the exploration root", () => {
      openSession();
      expect(store.focusItemByKey("move")).toBe(true);
      expect(store.focusConfirm()).toBe(true);
      expect(store.router.depth()).toBe(2);
      store.setConnected(false);
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
    });

    it("transport loss in combat re-posts the combat root descriptor", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { context_actions: fx.combatActions() } })],
        {},
      );
      expect(store.router.currentDescriptor().source).toBe("combat.root");
      expect(store.focusItemByKey("skills")).toBe(true);
      expect(store.focusConfirm()).toBe(true);
      expect(store.router.depth()).toBe(2);
      store.setConnected(false);
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("combat.root");
    });

    it("a mode switch to combat re-posts the combat root while a services drawer is open", () => {
      openSession();
      enterQuests();
      // The committed combat adoption is a teardown: exactly one
      // combat.root descriptor, drawer closed.
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, mode: "combat", panels: { context_actions: fx.combatActions() } })],
        {},
      );
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("combat.root");
      expect(store.view.hudDrawer).toBe(null);
    });
  });

 describe("frameless shop drawer", () => {
   it("activating service-shop opens shop drawer leaving frame stack and depth unchanged", () => {
     openSession();
     expect(store.focusItemByKey("interact")).toBe(true);
     expect(store.focusConfirm()).toBe(true);
     expect(store.focusItemByKey("target-7")).toBe(true);
     expect(store.focusConfirm()).toBe(true);

     const depthBefore = store.router.depth();
     const descriptorBefore = store.router.currentDescriptor();
     const trailBefore = store.router.trail();

     expect(store.focusItemByKey("service-shop")).toBe(true);
     expect(store.focusConfirm()).toBe(true);

     // Shop drawer opens without pushing a frame or recording a service surface
     expect(store.view.hudDrawer).toBe("shop");
     expect(store.router.depth()).toBe(depthBefore);
     expect(store.router.currentDescriptor()).toEqual(descriptorBefore);
     expect(store.router.trail()).toEqual(trailBefore);
     expect(store.view.activeSubDock).toBe(null);
     expect(store.serviceSurface).toBe(null);

     // A services-panel commit while the shop drawer is open never records a hosted surface or pushes a frame
     const updateSnap = snapshot({ revision: 2 });
     expect(store.receive(1, "ui_snapshot", [updateSnap], {}).accepted).toBe(true);

     expect(store.view.hudDrawer).toBe("shop");
     expect(store.router.depth()).toBe(depthBefore);
     expect(store.router.currentDescriptor()).toEqual(descriptorBefore);
     expect(store.view.activeSubDock).toBe(null);
     expect(store.serviceSurface).toBe(null);
});
 });
});
