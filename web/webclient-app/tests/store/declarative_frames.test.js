// webclient-declarative-frame-stack (task 4.1): the store-level declarative
// frame contract. Open exploration frames are descriptors, never copies — a
// committed snapshot RE-RESOLVES them at the next access (the open 移動 pane
// shows the new room's exits with key-tracked focus), a vanished target
// identity pops exactly one level with the opener's focus restored, whole-
// stack loss cascades to the root, the suggestions frame survives
// generating→ready and exits to the root on `unavailable` with no reason
// row, pointer activation writes the focus key before dispatch, and a mode
// switch yields the one-frame stack.

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

function openExploration(store) {
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
          context_actions: fx.explorationActions(),
        },
      }),
    ],
    {},
  );
  expect(result.accepted).toBe(true);
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
    it("a snapshot commit updates the open move frame with key-tracked focus", () => {
      openExploration(store);
      // Open the 移動 frame and focus the north exit row.
      expect(store.focusConfirm("keyboard")).toBe(true); // root "move" -> move frame
      expect(store.router.depth()).toBe(2);
      expect(store.view.focus.key).toBe("exit-east");
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("exit-north");

      // The room changes under the open frame: a wholly different exit list
      // where the focused key survives at a DIFFERENT index (the locked door
      // is now second). No re-push exists — the next read resolves it.
      const result = store.receive(
        1,
        "ui_update",
        [
          explorationCommit(3, {
            move: [
              { exit_ref: "south", label: "南門", destination: "room:51", enabled: true, disabled_reason: null },
              {
                exit_ref: "north",
                label: "北門",
                destination: "room:52",
                enabled: true,
                disabled_reason: null,
              },
              { exit_ref: "west", label: "西站", destination: "room:53", enabled: true, disabled_reason: null },
            ],
          }),
        ],
        {},
      );
      expect(result.accepted).toBe(true);

      // The pane lists the new room's exits and the focus KEY survived.
      const labels = store.router.currentMenu().items.map((item) => item.label);
      expect(labels).toEqual(["南門", "北門", "西站", "返回上一層"]);
      expect(store.view.focus.key).toBe("exit-north");

      // Re-activation submits the NEW row's payload (the committed
      // exit_ref/current_node), never a copy captured when the frame opened.
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      expect(sender.sent.actions[0].action_id).toBe("explore.move");
      expect(sender.sent.actions[0].payload).toEqual({ exit_ref: "north", current_node: "room:42" });
    });

    it("a lost focus key lands on the nearest surviving row", () => {
      openExploration(store);
      expect(store.focusConfirm("keyboard")).toBe(true); // move frame
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("exit-north");
      // The focused row disappears: the re-derived frame is
      // [exit-south, back]; the router-private cached row index was 1, and
      // the nearest surviving index (earlier on a tie) takes focus.
      store.receive(
        1,
        "ui_update",
        [
          explorationCommit(3, {
            move: [
              {
                exit_ref: "south",
                label: "南門",
                destination: "room:51",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
        {},
      );
      expect(store.view.focus.key).toBe("back");
    });
  });

  describe("identity loss", () => {
    it("a vanished target identity pops one level with opener focus restored", () => {
      openExploration(store);
      // 互動 -> target 7 -> (target affordance frame).
      expect(store.focusItemByKey("interact")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(2);
      expect(store.focusItemByKey("target-7")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(3);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.target",
        params: { identity: 7 },
      });

      // The committed panel no longer lists identity 7.
      store.receive(1, "ui_update", [explorationCommit(3, { interact: [] })], {});

      // Exactly one frame popped; the interact frame restores focus toward
      // the vanished target's former row (nearest rule onto the empty row).
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.interact",
        params: {},
      });
      expect(store.view.focus.key).toBe("interact-empty");
    });

    it("consecutive unresolvable frames cascade in one access down to the parent", () => {
      openExploration(store);
      // 互動 -> target 7 -> 交談關鍵詞 (keywords carries {identity}).
      expect(store.focusItemByKey("interact")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.focusItemByKey("target-7")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.focusItemByKey("talk-scripted")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(store.router.depth()).toBe(4);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.keywords",
        params: { identity: 7 },
      });

      // One commit removes the identity: BOTH the keywords and the target
      // frame become unresolvable at once.
      store.receive(1, "ui_update", [explorationCommit(3, { interact: [] })], {});

      // The pop cascaded to the interact frame in a single access (no timer).
      expect(store.router.depth()).toBe(2);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.interact",
        params: {},
      });
      expect(store.view.dockTrail.length).toBe(2);
    });

    it("whole-stack loss cascades to a degraded root that submits nothing", () => {
      openExploration(store);
      expect(store.focusConfirm("keyboard")).toBe(true); // move frame, depth 2

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
      expect(store.view.focus.key).toBe("move");
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
      openExploration(store);
      // Two enabled exits (the base fixture's north exit is disabled).
      store.receive(
        1,
        "ui_update",
        [
          explorationCommit(2, {
            move: [
              { exit_ref: "east", label: "東門", destination: "room:43", enabled: true, disabled_reason: null },
              { exit_ref: "north", label: "北門", destination: "room:44", enabled: true, disabled_reason: null },
            ],
          }),
        ],
        {},
      );
      expect(store.focusConfirm("keyboard")).toBe(true); // move frame
      // Pointer selection of the second row, then a pointer confirm.
      expect(store.focusItemByKey("exit-north")).toBe(true);
      expect(store.focusConfirm("pointer")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      expect(sender.sent.actions[0].payload).toEqual({ exit_ref: "north", current_node: "room:42" });

      // The written-back key survives the next re-resolution: a commit keeps
      // focus on the ACTIVATED row, not on the row the frame first opened.
      store.receive(
        1,
        "ui_update",
        [
          explorationCommit(3, {
            move: [
              { exit_ref: "south", label: "南門", destination: "room:51", enabled: true, disabled_reason: null },
              {
                exit_ref: "north",
                label: "北門",
                destination: "room:52",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
        {},
      );
      expect(store.view.focus.key).toBe("exit-north");
    });
  });

  describe("teardown", () => {
    it("a mode switch to combat and back yields exactly one frame", () => {
      openExploration(store);
      expect(store.focusConfirm("keyboard")).toBe(true); // depth 2
      expect(store.router.depth()).toBe(2);

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
      expect(store.view.focus.key).toBe("move");
    });

    // The named teardown triggers beyond the mode switch. The no-puppet case
    // is the sharp one: the reducer retains mode AND epoch on a `no_puppet`
    // protocol error, so a stack would survive the character leaving unless
    // the detach transition is its own teardown event.
    it("a no_puppet detach at depth 2 collapses the stack to the root frame", () => {
      openExploration(store);
      expect(store.focusConfirm("keyboard")).toBe(true); // depth 2
      expect(store.router.depth()).toBe(2);

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
      expect(store.focusConfirm("keyboard")).toBe(true); // depth 2 (move)
      store.focusEscape(); // back to the root frame
      expect(store.router.depth()).toBe(1);
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
      expect(store.view.focus.key).toBe("move");
    });

    it("a transport loss at depth 2 yields exactly one root frame", () => {
      openExploration(store);
      expect(store.focusConfirm("keyboard")).toBe(true); // depth 2
      expect(store.router.depth()).toBe(2);

      store.setConnected(false);

      expect(store.router.depth()).toBe(1);
      expect(store.router.currentDescriptor()).toEqual({
        source: "exploration.root",
        params: {},
      });
    });
  });
});
