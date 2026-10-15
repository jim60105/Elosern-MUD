// webclient-declarative-frame-stack (task 4.1): the store-level declarative
// frame contract. Open exploration frames are descriptors, never copies — a
// committed snapshot RE-RESOLVES them at the next access (the open
// frame re-resolves in place), whole-stack loss cascades to the root, and a
// mode switch yields the one-frame stack.
//
// webclient-retire-exploration-submenus retired the move/look/interact
// frames, exploration-presence-rail retired the verb popover (a target's
// verbs are the client-local verb card, never a frame; its own contracts live
// in tests/store/presence_card.test.js), and exploration-room-actions retired
// the waiting and suggestions frames (the client-local wait and suggestions
// cards; tests/store/room_cards.test.js). The exploration family pushes no
// frame of its own any more, so the generic stack contracts here ride a
// resolvable exploration child frame pushed straight onto the router (the
// top navigation's own source), and the combat family's real frames. The
// file also pins the
// new room-change reset (design D2) and — webclient-talk-open-dock — the
// conversation-open reset: the commit that changes the mode to `dialogue`
// returns the dock to the overview (see the describe block at the end).

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

// The exploration commit pair the production server ships together: the
// `exploration` panel plus its `local_map` anchor, on top of the snapshot's
// status/context_actions panels.
function explorationCommit(revision, explorationOverrides, contextActionsOverrides) {
  return fx.update({
    revision,
    panels: {
      exploration: fx.explorationPanel(explorationOverrides),
      local_map: fx.localMapPanel(),
      context_actions: fx.explorationActions(contextActionsOverrides),
    },
  });
}

function openExploration(store, explorationOverrides) {
  store.beginTransport(1);
  store.setConnected(true);
  const result = store.receive(
    1,
    "ui_snapshot",
    [
      fx.snapshot({
        revision: 1,
        panels: {
          status: fx.statusPanel(),
          exploration: fx.explorationPanel(explorationOverrides),
          local_map: fx.localMapPanel(),
          context_actions: fx.explorationActions(),
        },
      }),
    ],
    {},
  );
  expect(result.accepted).toBe(true);
}

// A resolvable exploration child frame at depth 2. The exploration family
// pushes no frame of its own any more (exploration-room-actions), so the
// stack contracts push the top navigation's own source, which resolves from
// the same committed exploration panel.
const CHILD = Object.freeze({ source: "exploration.navigation", params: {} });
function openChildFrame(store) {
  store.router.pushFrame(CHILD, { openerKey: null, unresolvableAction: "pop" });
  store.refreshView();
  expect(store.router.depth()).toBe(2);
}

// A commit that moves the actor: `look.room.identity` is the panel's own
// stable movement key (webclient-scene-overview-swap D2).
function roomChange(revision, identity) {
  return explorationCommit(revision, {
    look: { room: { identity, display_name: "另一個房間", room: true } },
  });
}

// The committed dialogue panel a successful 交談 commits
// (webclient-talk-open-dock).
function dialoguePanel() {
  return {
    schema_version: 2,
    available: true,
    kind: "dialogue",
    host: { identity: 7, display_name: "店長", portrait_ref: null },
    bond_stage: "親睦",
    line: "「渡河要五枚銅板。」",
    choices: [{ keyword_id: "fare", label: "「就五枚，走嗎？」" }],
  };
}

// The presentation the server publishes when a conversation opens: the same
// exploration/local-map pair with the committed mode `dialogue` and the
// dialogue panel.
function dialogueSnapshot(revision) {
  return fx.snapshot({
    revision,
    mode: "dialogue",
    panels: {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      local_map: fx.localMapPanel(),
      context_actions: fx.explorationActions(),
      dialogue: dialoguePanel(),
    },
  });
}

describe("declarative frame stack (store contract)", () => {
  let store;
  let sender;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  describe("frame loss", () => {
    // A frame bound to one server-authored subject (here a combat skill
    // frame bound to its skill key) whose subject vanishes pops exactly one
    // level, and the parent restores focus toward the vanished row.
    function skillCategory(keys) {
      return [
        {
          category: "martial_arts",
          label: "武技",
          groups: [
            {
              group: null,
              label: null,
              skills: keys.map((key, index) => ({
                key,
                label: `招式${index + 1}`,
                description: `第 ${index + 1} 式的合成描述。`,
                cost: { mp: index },
                target_spec: "self",
                element: null,
                enabled: true,
                disabled_reason: null,
                targets: [],
                shorthands: [],
                hostile: false,
                beneficial: false,
              })),
            },
          ],
        },
      ];
    }

    function combatCommit(revision, keys) {
      return fx.update({
        revision,
        mode: "combat",
        panels: { context_actions: fx.combatActions({ skills: skillCategory(keys) }) },
      });
    }

    it("a vanished subject pops exactly one level and restores the opener row", () => {
      openExploration(store);
      store.receive(1, "ui_update", [combatCommit(2, ["t_one", "t_two", "t_three"])], {});
      expect(store.focusItemByKey("skills")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.focusItemByKey("skill-cat-0")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      const parentDepth = store.router.depth();
      expect(store.focusItemByKey("t_two")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.currentDescriptor()).toEqual({ source: "combat.skill", params: { skillKey: "t_two" } });

      // The committed panel no longer lists t_two: its frame pops one level.
      store.receive(1, "ui_update", [combatCommit(3, ["t_one", "t_three"])], {});
      expect(store.router.depth()).toBe(parentDepth);
      expect(store.view.focus.key).toBe("t_three");
    });

    it("consecutive unresolvable frames cascade in one access down to the parent", () => {
      openExploration(store);
      // Two exploration child frames, both resolving from the committed
      // exploration panel, so one commit can invalidate both.
      openChildFrame(store);
      store.router.pushFrame(CHILD, { openerKey: null, unresolvableAction: "pop" });
      expect(store.router.depth()).toBe(3);

      // One commit makes the exploration panel unavailable: BOTH frames
      // become unresolvable at once.
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 3,
            panels: {
              exploration: {
                schema_version: 4,
                available: false,
                reason: { code: "scene_lost", message: "這片區域暫時不可用。" },
              },
            },
          }),
        ],
        {},
      );

      // Both frames cascaded to the root in a single access (no timer).
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.dockTrail.length).toBe(1);
    });

    it("whole-stack loss cascades to a degraded root that submits nothing", () => {
      openExploration(store);
      // The child frame dispatches nothing when it opens, so the assertion
      // below isolates the degraded root's own submission behaviour.
      openChildFrame(store);

      // A FULL snapshot without the exploration panel (updates replace only
      // the named panels, so only a snapshot drops it): every exploration
      // frame resolves to the marker; the cascade ends at the root frame.
      const result = store.receive(
        1,
        "ui_snapshot",
        [fx.snapshot({ revision: 3, panels: { status: fx.statusPanel() } })],
        {},
      );
      expect(result.accepted).toBe(true);
      expect(store.router.depth()).toBe(1);

      // The unresolvable root presents the single disabled marker row with
      // the local fallback line (no server reason was committed).
      const menu = store.router.currentMenu();
      expect(menu.items.length).toBe(1);
      expect(menu.items[0].enabled).toBe(false);
      expect(store.view.focus.key).toBe("degraded-root");
      expect(store.view.degradedRoot).toEqual({
        key: "degraded-root",
        reason: null,
        fallback: "畫面狀態已更新，請返回上層",
      });
      // Activating it submits nothing.
      expect(store.focusConfirm("keyboard")).toBe(false);
      expect(sender.sent.actions.length).toBe(0);

      // The panel returns: the same root frame re-resolves and recovers.
      store.receive(1, "ui_update", [explorationCommit(4)], {});
      expect(store.view.degradedRoot).toBeNull();
      // The recovered root is the empty exploration root: nothing focused.
      expect(store.view.focus.key).toBeNull();
      expect(store.router.currentMenu().items).toEqual([]);
    });
  });

  describe("teardown", () => {
    it("a mode switch to combat and back yields exactly one frame", () => {
      openExploration(store);
      openChildFrame(store);

      // Mode switch to combat: one combat root frame (legacy copy until the
      // combat family migrates), the exploration stack gone.
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 3,
            mode: "combat",
            panels: { context_actions: fx.combatActions(), local_map: fx.localMapPanel() },
          }),
        ],
        {},
      );
      expect(store.router.depth()).toBe(1);
      expect(store.view.focus.key).toBe("attack");

      // Back to exploration: exactly the declarative root frame returns.
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 4,
            mode: "exploration",
            panels: {
              exploration: fx.explorationPanel(),
              local_map: fx.localMapPanel(),
              context_actions: fx.explorationActions(),
            },
          }),
        ],
        {},
      );
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.root",
        params: {},
      });
      expect(store.view.focus.key).toBeNull();
    });

    // The named teardown triggers beyond the mode switch. The no-puppet case
    // is the sharp one: the reducer retains mode AND epoch on a `no_puppet`
    // protocol error, so a stack would survive the character leaving unless
    // the detach transition is its own teardown event.
    it("a no_puppet detach at depth 2 collapses the stack to the root frame", () => {
      openExploration(store);
      openChildFrame(store);

      const result = store.receive(1, "ui_protocol_error", [fx.protocolError()], {});
      expect(result.accepted).toBe(true);
      expect(store.view.phase).toBe("detached");

      // One frame, still the declarative exploration root (the mode did not
      // change). With the panels cleared the root degrades in place to the
      // marker-reason row instead of sitting empty.
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.root",
        params: {},
      });
      expect(store.view.degradedRoot).not.toBeNull();
    });

    it("an epoch-reset snapshot with an open submenu yields exactly one root frame", () => {
      openExploration(store);
      openChildFrame(store);

      // The production epoch-reset path: a fresh transport generation
      // retires the active epoch, and the new-epoch snapshot establishes
      // the new one — the store sees `epochChanged` on that commit.
      store.beginTransport(2);
      const result = store.receive(
        2,
        "ui_snapshot",
        [
          fx.snapshot({
            revision: 1,
            presentation_epoch: fx.EPOCH_B,
            panels: {
              status: fx.statusPanel(),
              exploration: fx.explorationPanel(),
              local_map: fx.localMapPanel(),
              context_actions: fx.explorationActions(),
            },
          }),
        ],
        {},
      );
      expect(result.accepted).toBe(true);
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.root",
        params: {},
      });
      expect(store.view.focus.key).toBeNull();
    });

    it("a transport loss at depth 2 yields exactly one root frame", () => {
      openExploration(store);
      openChildFrame(store);

      store.setConnected(false);

      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.root",
        params: {},
      });
    });
  });

  // webclient-scene-overview-swap D2: the dock returns to the scene overview
  // whenever the committed room changes, whatever opened the frame — the
  // dock's own chips, the minimap, or a typed command.
  describe("room-change reset", () => {
    it("an open child frame resets to the exploration root on every move", () => {
      openExploration(store);
      openChildFrame(store);
      store.receive(1, "ui_update", [roomChange(3, 99)], {});
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.focus.key).toBeNull();

      // Again from the next room.
      openChildFrame(store);
      expect(store.router.currentDescriptor()).toEqual(CHILD);
      store.receive(1, "ui_update", [roomChange(5, 101)], {});
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.dockTrail.length).toBe(1);
    });

    it("a same-room commit keeps the frame open", () => {
      openExploration(store);
      openChildFrame(store);
      // The same room, a new revision: the frame re-resolves in place.
      store.receive(1, "ui_update", [explorationCommit(3)], {});
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor()).toEqual(CHILD);
    });

    it("the first room identity a store ever sees is recorded, never treated as a move", () => {
      // The dock is on the combat form and no exploration panel has committed
      // yet, so no room identity has been recorded (the D2 read is scoped to
      // the exploration form).
      store.beginTransport(1);
      store.setConnected(true);
      const mount = store.receive(
        1,
        "ui_snapshot",
        [
          fx.snapshot({
            revision: 1,
            panels: {
              status: fx.statusPanel(),
              context_actions: fx.combatActions(),
              local_map: fx.localMapPanel(),
            },
          }),
        ],
        {},
      );
      expect(mount.accepted).toBe(true);
      expect(store.focusItemByKey("skills")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(2);

      // The exploration panel arrives while the stack is deeper than the
      // root: the identity is NEW (there is no previous one), so the settle
      // records it instead of resetting the stack.
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 2,
            panels: {
              exploration: fx.explorationPanel(),
              local_map: fx.localMapPanel(),
              context_actions: fx.combatActions(),
            },
          }),
        ],
        {},
      );
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor().source).toBe("combat.categories");
    });

    it("an unavailable exploration panel records null and never resets", () => {
      openExploration(store);
      openChildFrame(store);

      // The panel goes unavailable: every exploration frame resolves to the
      // marker, so the stack cascades to the degraded root in one access, and
      // the room identity records `null` rather than a room.
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 3,
            panels: {
              exploration: {
                schema_version: 4,
                available: false,
                reason: { code: "scene_lost", message: "這片區域暫時不可用。" },
              },
              local_map: fx.localMapPanel(),
              context_actions: fx.explorationActions(),
            },
          }),
        ],
        {},
      );
      expect(store.router.depth()).toBe(1);
      expect(store.view.degradedRoot).not.toBeNull();

      // The panel returns: the root is already current and the unavailable
      // commit's `null` record is not a move, so nothing resets.
      store.receive(1, "ui_update", [explorationCommit(4)], {});
      expect(store.view.degradedRoot).toBeNull();
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
    });
  });

  // webclient-talk-open-dock: 交談 submits `explore.talk_open` in one step and
  // the dock returns to the overview in the commit that makes the mode
  // `dialogue`, so no child frame stays open over the conversation. The reset is
  // the store's ONE mode-change teardown (`syncHudDrawer` ->
  // `resetFramesToRoot`, webclient-services-combat-creation-frames): it posts
  // the committed mode's root descriptor, which for dialogue is the ordinary
  // exploration root. These cases pin the transition at the store level; the
  // dock's own contract is stated by `webclient-exploration-menu`.
  describe("the conversation-open reset", () => {
    it("a frame open when the commit changes the mode to dialogue resets to the overview", () => {
      openExploration(store);
      openChildFrame(store);
      expect(store.router.depth()).toBe(2);

      const result = store.receive(1, "ui_snapshot", [dialogueSnapshot(3)], {});
      expect(result.accepted).toBe(true);
      expect(store.view.mode).toBe("dialogue");
      // The frame closed IN that commit: the dock is at the overview and no
      // deeper frame remains activatable over the conversation.
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.root",
        params: {},
      });
      expect(store.view.dockSource).toBe("exploration.root");
      // The conversation itself presents: the committed dialogue panel.
      expect(store.view.panels.dialogue.line).toBe("「渡河要五枚銅板。」");
    });

    it("a commit that keeps the mode dialogue leaves the open frame alone", () => {
      // A session already in dialogue: the dock is the ordinary exploration
      // root, so its child frames are reachable mid-conversation.
      store.beginTransport(1);
      store.setConnected(true);
      store.receive(1, "ui_snapshot", [dialogueSnapshot(1)], {});
      expect(store.view.mode).toBe("dialogue");
      expect(store.router.depth()).toBe(1);
      openChildFrame(store);

      // No mode transition: the frame re-resolves in place.
      store.receive(1, "ui_update", [fx.update({ revision: 2, mode: "dialogue" })], {});
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor()).toEqual(CHILD);
    });

    it("the first commit of a dialogue session mounts the one root frame and resets nothing", () => {
      store.beginTransport(1);
      store.setConnected(true);
      const mount = store.receive(1, "ui_snapshot", [dialogueSnapshot(1)], {});
      expect(mount.accepted).toBe(true);
      // A conversation already live at the first commit: the dock mounts its
      // committed mode's root (the exploration root — dialogue has no dock form
      // of its own), degraded to nothing, with no teardown to run.
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.root",
        params: {},
      });
      expect(store.view.degradedRoot).toBeNull();
      expect(store.view.mode).toBe("dialogue");
    });

    it("leaving dialogue also returns the dock to the overview in that commit", () => {
      store.beginTransport(1);
      store.setConnected(true);
      store.receive(1, "ui_snapshot", [dialogueSnapshot(1)], {});
      openChildFrame(store);

      // The conversation ends: the same mode-change teardown returns the dock
      // to the overview rather than leaving a frame over the exploration
      // surface.
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 2,
            mode: "exploration",
            panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() },
          }),
        ],
        {},
      );
      expect(store.view.mode).toBe("exploration");
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
    });
  });
});
