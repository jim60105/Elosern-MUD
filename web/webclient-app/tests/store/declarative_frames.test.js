// webclient-declarative-frame-stack (task 4.1): the store-level declarative
// frame contract. Open exploration frames are descriptors, never copies — a
// committed snapshot RE-RESOLVES them at the next access (the open verb
// popover shows the target's new affordances with key-tracked focus), a
// vanished target identity closes the verb popover and lands focus on the
// nearest surviving chip, whole-stack loss cascades to the root, the
// suggestions frame survives generating→ready and exits to the root on
// `unavailable` with no reason row, pointer activation writes the focus key
// before dispatch, and a mode switch yields the one-frame stack.
//
// webclient-retire-exploration-submenus: the move/look/interact frames are
// gone, so the pushed frame these contracts ride is the verb popover, reached
// through the real path (person chip → verb popover). The file also pins the
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

// One interact target carrying the given v3 affordances: the panel shape the
// verb popover re-resolves from on every commit.
function target(identity, affordances) {
  return { identity, display_name: "店長", portrait_ref: null, affordances };
}

function affordance(action_id, label) {
  return { kind: "action", action_id, label, enabled: true, disabled_reason: null };
}

// A person chip's verb popover: one deliberate activation from the overview.
function openVerbPopover(store) {
  expect(store.focusItemByKey("target-7")).toBe(true);
  expect(store.focusConfirm("keyboard")).toBe(true);
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
// (webclient-talk-open-dock): the conversation the popover's `talk-open` row
// opened.
function dialoguePanel() {
  return {
    schema_version: 1,
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

  describe("commit-driven re-resolution", () => {
    it("a snapshot commit updates the open verb popover with key-tracked focus", () => {
      openExploration(store, {
        interact: [
          target(7, [
            affordance("explore.talk_open", "交談"),
            affordance("explore.party_invite", "邀請"),
          ]),
        ],
      });
      // Open the 交談 popover and focus its second affordance row.
      openVerbPopover(store);
      expect(store.view.focus.key).toBe("talk-open");
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("party-invite");

      // The target's affordances change under the open frame: a longer list
      // where the focused key survives at a DIFFERENT index. No re-push
      // exists — the next read resolves it.
      const result = store.receive(
        1,
        "ui_update",
        [
          explorationCommit(3, {
            interact: [
              target(7, [
                affordance("explore.engage", "戰鬥"),
                affordance("explore.talk_open", "交談"),
                affordance("explore.party_invite", "邀請"),
              ]),
            ],
          }),
        ],
        {},
      );
      expect(result.accepted).toBe(true);

      // The popover lists the new affordance rows and the focus KEY survived.
      const keys = store.router.currentMenu().items.map((item) => item.key);
      expect(keys).toEqual(["engage", "talk-open", "party-invite", "look-target", "back"]);
      expect(store.view.focus.key).toBe("party-invite");

      // Re-activation submits the NEW row's payload (the committed
      // npc_id), never a copy captured when the frame opened.
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      expect(sender.sent.actions[0].action_id).toBe("explore.party_invite");
      expect(sender.sent.actions[0].payload).toEqual({ npc_id: 7, message: "" });
    });

    it("a lost focus key lands on the nearest surviving row", () => {
      openExploration(store, {
        interact: [
          target(7, [
            affordance("explore.talk_open", "交談"),
            affordance("explore.party_invite", "邀請"),
          ]),
        ],
      });
      openVerbPopover(store);
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("party-invite");
      // The focused row disappears: the re-derived frame is
      // [talk-open, look-target, back]; the router-private cached row index
      // was 1, and the nearest surviving index takes focus.
      store.receive(
        1,
        "ui_update",
        [
          explorationCommit(3, {
            interact: [target(7, [affordance("explore.talk_open", "交談")])],
          }),
        ],
        {},
      );
      expect(store.view.focus.key).toBe("look-target");
    });
  });

  describe("identity loss", () => {
    it("a vanished target identity closes the popover and lands focus on the nearest chip", () => {
      openExploration(store);
      // The overview's person chip opens target 7's verb popover.
      openVerbPopover(store);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.target",
        params: { identity: 7 },
      });

      // The committed panel no longer lists identity 7.
      store.receive(1, "ui_update", [explorationCommit(3, { interact: [] })], {});

      // The popover closed in that commit and the overview is current; the
      // vanished chip's slot takes the nearest surviving chip — the same
      // person's look chip.
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.focus.key).toBe("entity-7");
    });

    it("consecutive unresolvable frames cascade in one access down to the parent", () => {
      openExploration(store, {
        interact: [
          target(7, [affordance("explore.talk_open", "交談")]),
          target(9, [affordance("explore.talk_open", "交談")]),
        ],
      });
      // Person chip -> target 7's verb popover, plus target 9's popover pushed
      // directly on top: both frames resolve from the same committed interact
      // list, so one commit can invalidate both.
      openVerbPopover(store);
      store.router.pushFrame({ source: "exploration.target", params: { identity: 9 } });
      expect(store.router.depth()).toBe(3);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.target",
        params: { identity: 9 },
      });

      // One commit removes every identity: BOTH frames become unresolvable at
      // once.
      store.receive(1, "ui_update", [explorationCommit(3, { interact: [] })], {});

      // Both frames cascaded to the root in a single access (no timer).
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.dockTrail.length).toBe(1);
    });

    it("whole-stack loss cascades to a degraded root that submits nothing", () => {
      openExploration(store);
      // The verb popover dispatches nothing, so the assertion below isolates
      // the degraded root's own submission behaviour.
      openVerbPopover(store);

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
      expect(store.view.focus.key).toBe("exit-east");
    });
  });

  describe("suggestions status split", () => {
    it("generating keeps the frame across commits; unavailable exits to the root with no reason row", () => {
      openExploration(store);
      // The 建議 root row (the envelope commits `generating`).
      expect(store.focusItemByKey("suggestions")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(2);
      expect(store.view.focus.key).toBe("suggestions-generating");

      // An unrelated commit while still `generating`: the frame keeps its
      // content and focus (a muted row, never a pop).
      store.receive(1, "ui_update", [explorationCommit(3)], {});
      expect(store.router.depth()).toBe(2);
      expect(store.view.focus.key).toBe("suggestions-generating");

      // The envelope commits `unavailable`: the no-pane rule exits the WHOLE
      // stack to the root — deterministically, with no reason row.
      store.receive(
        1,
        "ui_update",
        [explorationCommit(4, undefined, { suggestions: { status: "unavailable" } })],
        {},
      );
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.root",
        params: {},
      });
      expect(store.view.degradedRoot).toBeNull();
      const labels = store.router.currentMenu().items.map((item) => item.label);
      expect(labels).not.toContain("畫面狀態已更新，請返回上層");
      // The root's 建議 row is gone with the unavailable status.
      expect(store.router.currentMenu().items.some((item) => item.key === "suggestions")).toBe(false);
    });
  });

  describe("activation", () => {
    it("a pointer pick writes the frame focus key before dispatching", () => {
      openExploration(store, {
        interact: [
          target(7, [
            affordance("explore.talk_open", "交談"),
            affordance("explore.party_invite", "邀請"),
          ]),
        ],
      });
      openVerbPopover(store);
      // Pointer selection of the second row, then a pointer confirm.
      expect(store.focusItemByKey("party-invite")).toBe(true);
      expect(store.focusConfirm("pointer")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      expect(sender.sent.actions[0].payload).toEqual({ npc_id: 7, message: "" });

      // The written-back key survives the next re-resolution: a commit keeps
      // focus on the ACTIVATED row, not on the row the frame first opened.
      store.receive(
        1,
        "ui_update",
        [
          explorationCommit(3, {
            interact: [
              target(7, [
                affordance("explore.engage", "戰鬥"),
                affordance("explore.talk_open", "交談"),
                affordance("explore.party_invite", "邀請"),
              ]),
            ],
          }),
        ],
        {},
      );
      expect(store.view.focus.key).toBe("party-invite");
    });
  });

  describe("teardown", () => {
    it("a mode switch to combat and back yields exactly one frame", () => {
      openExploration(store);
      openVerbPopover(store);

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
      expect(store.view.focus.key).toBe("exit-east");
    });

    // The named teardown triggers beyond the mode switch. The no-puppet case
    // is the sharp one: the reducer retains mode AND epoch on a `no_puppet`
    // protocol error, so a stack would survive the character leaving unless
    // the detach transition is its own teardown event.
    it("a no_puppet detach at depth 2 collapses the stack to the root frame", () => {
      openExploration(store);
      openVerbPopover(store);

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
      expect(store.focusItemByKey("wait")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true); // depth 2 (wait)
      expect(store.router.depth()).toBe(2);

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
      expect(store.view.focus.key).toBe("exit-east");
    });

    it("a transport loss at depth 2 yields exactly one root frame", () => {
      openExploration(store);
      openVerbPopover(store);

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
    it("a popover and a wait frame each reset to the overview", () => {
      // The verb popover.
      openExploration(store);
      openVerbPopover(store);
      store.receive(1, "ui_update", [roomChange(3, 99)], {});
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.focus.key).toBe("exit-east");

      // The waiting frame.
      expect(store.focusItemByKey("wait")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.currentDescriptor().source).toBe("exploration.wait");
      store.receive(1, "ui_update", [roomChange(4, 100)], {});
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");

      // The verb popover again, one deliberate activation from the overview.
      openVerbPopover(store);
      expect(store.router.currentDescriptor().source).toBe("exploration.target");
      store.receive(1, "ui_update", [roomChange(5, 101)], {});
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.dockTrail.length).toBe(1);
    });

    it("a same-room commit keeps the frame open", () => {
      openExploration(store);
      openVerbPopover(store);
      // The same room, a new revision: the popover re-resolves in place.
      store.receive(1, "ui_update", [explorationCommit(3)], {});
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.target",
        params: { identity: 7 },
      });
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
      expect(store.focusItemByKey("wait")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(2);

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
                schema_version: 3,
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
  // `dialogue`, so no popover stays open over the conversation. The reset is
  // the store's ONE mode-change teardown (`syncHudDrawer` ->
  // `resetFramesToRoot`, webclient-services-combat-creation-frames): it posts
  // the committed mode's root descriptor, which for dialogue is the ordinary
  // exploration root. These cases pin the transition at the store level; the
  // dock's own contract is stated by `webclient-exploration-menu`.
  describe("the conversation-open reset", () => {
    it("a popover open when the commit changes the mode to dialogue resets to the overview", () => {
      openExploration(store, {
        interact: [target(7, [affordance("explore.talk_open", "交談")])],
      });
      openVerbPopover(store);
      expect(store.router.depth()).toBe(2);

      const result = store.receive(1, "ui_snapshot", [dialogueSnapshot(3)], {});
      expect(result.accepted).toBe(true);
      expect(store.view.mode).toBe("dialogue");
      // The popover closed IN that commit: the dock is at the overview and no
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
      // root, so its popover is reachable mid-conversation.
      store.beginTransport(1);
      store.setConnected(true);
      store.receive(1, "ui_snapshot", [dialogueSnapshot(1)], {});
      expect(store.view.mode).toBe("dialogue");
      expect(store.router.depth()).toBe(1);
      expect(store.focusItemByKey("target-7")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(2);

      // No mode transition: the frame re-resolves in place.
      store.receive(1, "ui_update", [fx.update({ revision: 2, mode: "dialogue" })], {});
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor().source).toBe("exploration.target");
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
      expect(store.focusItemByKey("target-7")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(2);

      // The conversation ends: the same mode-change teardown returns the dock
      // to the overview rather than leaving a popover over the exploration
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
