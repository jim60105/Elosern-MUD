// webclient-declarative-frame-stack (task 4.1): the store-level declarative
// frame contract. Open exploration frames are descriptors, never copies — a
// committed snapshot RE-RESOLVES them at the next access (the open
// suggestions frame shows the envelope's new cards with key-tracked focus),
// whole-stack loss cascades to the root, the
// suggestions frame survives generating→ready and exits to the root on
// `unavailable` with no reason row, pointer activation writes the focus key
// before dispatch, and a mode switch yields the one-frame stack.
//
// webclient-retire-exploration-submenus retired the move/look/interact
// frames, and exploration-presence-rail retired the verb popover (a target's
// verbs are the client-local verb card, never a frame; its own contracts live
// in tests/store/presence_card.test.js), so the pushed frames these contracts
// ride are the waiting and suggestions frames, reached through the real path
// (a footer chip). The file also pins the
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

// A ready suggestions envelope carrying the given known-action cards: the
// shape the suggestions frame re-resolves from on every commit.
function readySuggestions(...cards) {
  return {
    suggestions: {
      status: "ready",
      cards: cards.map(([action_code, label, params]) => ({ kind: "known_action", action_code, label, params })),
    },
  };
}

const LOOK_CARD = ["explore.look", "看看木箱", { target_id: 3 }];
const WAIT_CARD = ["explore.wait", "等到天亮", { daypart: "dawn" }];
const ROOM_CARD = ["explore.look", "環顧四周", { room: true }];
const TALK_CARD = ["explore.talk_scripted", "與店長交談", { npc_id: 7, keyword_id: "問候" }];

// The waiting frame: one deliberate activation of its footer chip.
function openWaitFrame(store) {
  expect(store.focusItemByKey("wait")).toBe(true);
  expect(store.focusConfirm("keyboard")).toBe(true);
  expect(store.router.depth()).toBe(2);
}

// The suggestions frame: one deliberate activation of its footer chip.
function openSuggestionsFrame(store) {
  expect(store.focusItemByKey("suggestions")).toBe(true);
  expect(store.focusConfirm("keyboard")).toBe(true);
  expect(store.router.depth()).toBe(2);
}

// The exploration snapshot with a ready suggestions envelope.
function openWithSuggestions(store, contextActionsOverrides) {
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
          exploration: fx.explorationPanel(),
          local_map: fx.localMapPanel(),
          context_actions: fx.explorationActions(contextActionsOverrides),
        },
      }),
    ],
    {},
  );
  expect(result.accepted).toBe(true);
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

  describe("commit-driven re-resolution", () => {
    it("a snapshot commit updates the open suggestions frame with key-tracked focus", () => {
      openWithSuggestions(store, readySuggestions(LOOK_CARD, WAIT_CARD, TALK_CARD));
      openSuggestionsFrame(store);
      expect(store.view.focus.key).toBe("action-explore.look");
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("action-explore.wait");

      // The envelope's cards change under the open frame: a longer list
      // where the focused key survives at a DIFFERENT index. No re-push
      // exists — the next read resolves it.
      const result = store.receive(
        1,
        "ui_update",
        [explorationCommit(3, undefined, readySuggestions(ROOM_CARD, TALK_CARD, WAIT_CARD))],
        {},
      );
      expect(result.accepted).toBe(true);

      const keys = store.router.currentMenu().items.map((item) => item.key);
      expect(keys).toEqual([
        "action-explore.look",
        "action-explore.talk_scripted",
        "action-explore.wait",
        "action-options.dismiss",
        "back",
      ]);
      expect(store.view.focus.key).toBe("action-explore.wait");

      // Re-activation submits the NEW card's payload, never a copy captured
      // when the frame opened.
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      expect(sender.sent.actions[0].action_id).toBe("explore.wait");
      expect(sender.sent.actions[0].payload).toEqual({ daypart: "dawn" });
    });

    it("a lost focus key lands on the nearest surviving row", () => {
      openWithSuggestions(store, readySuggestions(LOOK_CARD, WAIT_CARD, TALK_CARD));
      openSuggestionsFrame(store);
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("action-explore.wait");
      // The focused card disappears: the re-derived frame is
      // [look, talk, look-2, dismiss, back]; the router-private cached row
      // index was 1, and the nearest surviving index takes focus.
      store.receive(1, "ui_update", [explorationCommit(3, undefined, readySuggestions(LOOK_CARD, TALK_CARD, ROOM_CARD))], {});
      expect(store.view.focus.key).toBe("action-explore.talk_scripted");
    });
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
      // The waiting frame, plus the suggestions frame pushed directly on top:
      // both resolve from the committed exploration panel, so one commit can
      // invalidate both.
      openWaitFrame(store);
      store.router.pushFrame({ source: "exploration.suggestions", params: {} });
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
                schema_version: 3,
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
      // The waiting frame dispatches nothing when it opens, so the assertion
      // below isolates the degraded root's own submission behaviour.
      openWaitFrame(store);

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
      expect(store.view.focus.key).toBe("look-room");
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
      openWithSuggestions(store, readySuggestions(LOOK_CARD, WAIT_CARD, TALK_CARD));
      openSuggestionsFrame(store);
      // Pointer selection of the second row, then a pointer confirm.
      expect(store.focusItemByKey("action-explore.wait")).toBe(true);
      expect(store.focusConfirm("pointer")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      expect(sender.sent.actions[0].payload).toEqual({ daypart: "dawn" });

      // The written-back key survives the next re-resolution: a commit keeps
      // focus on the ACTIVATED row, not on the row the frame first opened.
      store.receive(
        1,
        "ui_update",
        [explorationCommit(3, undefined, readySuggestions(ROOM_CARD, LOOK_CARD, WAIT_CARD, TALK_CARD))],
        {},
      );
      expect(store.view.focus.key).toBe("action-explore.wait");
    });
  });

  describe("teardown", () => {
    it("a mode switch to combat and back yields exactly one frame", () => {
      openExploration(store);
      openWaitFrame(store);

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
      expect(store.view.focus.key).toBe("look-room");
    });

    // The named teardown triggers beyond the mode switch. The no-puppet case
    // is the sharp one: the reducer retains mode AND epoch on a `no_puppet`
    // protocol error, so a stack would survive the character leaving unless
    // the detach transition is its own teardown event.
    it("a no_puppet detach at depth 2 collapses the stack to the root frame", () => {
      openExploration(store);
      openWaitFrame(store);

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
      expect(store.view.focus.key).toBe("look-room");
    });

    it("a transport loss at depth 2 yields exactly one root frame", () => {
      openExploration(store);
      openWaitFrame(store);

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
    it("a wait frame and a suggestions frame each reset to the overview", () => {
      // The waiting frame.
      openExploration(store);
      openWaitFrame(store);
      store.receive(1, "ui_update", [roomChange(3, 99)], {});
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.focus.key).toBe("look-room");

      // The suggestions frame.
      openSuggestionsFrame(store);
      expect(store.router.currentDescriptor().source).toBe("exploration.suggestions");
      store.receive(1, "ui_update", [roomChange(4, 100)], {});
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");

      // The waiting frame again, one deliberate activation from the overview.
      openWaitFrame(store);
      expect(store.router.currentDescriptor().source).toBe("exploration.wait");
      store.receive(1, "ui_update", [roomChange(5, 101)], {});
      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor().source).toBe("exploration.root");
      expect(store.view.dockTrail.length).toBe(1);
    });

    it("a same-room commit keeps the frame open", () => {
      openExploration(store);
      openWaitFrame(store);
      // The same room, a new revision: the frame re-resolves in place.
      store.receive(1, "ui_update", [explorationCommit(3)], {});
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.wait",
        params: {},
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
  // `dialogue`, so no child frame stays open over the conversation. The reset is
  // the store's ONE mode-change teardown (`syncHudDrawer` ->
  // `resetFramesToRoot`, webclient-services-combat-creation-frames): it posts
  // the committed mode's root descriptor, which for dialogue is the ordinary
  // exploration root. These cases pin the transition at the store level; the
  // dock's own contract is stated by `webclient-exploration-menu`.
  describe("the conversation-open reset", () => {
    it("a frame open when the commit changes the mode to dialogue resets to the overview", () => {
      openExploration(store);
      openWaitFrame(store);
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
      expect(store.focusItemByKey("wait")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(2);

      // No mode transition: the frame re-resolves in place.
      store.receive(1, "ui_update", [fx.update({ revision: 2, mode: "dialogue" })], {});
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor().source).toBe("exploration.wait");
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
      expect(store.focusItemByKey("wait")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(2);

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
