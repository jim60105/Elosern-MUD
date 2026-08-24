// C1 (webclient-vue-07-wire-store) dispatch + focus tests: the single
// dispatch entry (dispatch-only, one mutation in flight) with the tested
// lock semantics, and the keyboard-router focus slice driven by the
// committed `context_actions` panel (the preserved `action-`/`target-` item
// keys as the single key contract).

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

describe("store dispatch + focus", () => {
  let store;
  let sender;

  function openSession() {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [fx.snapshot()], {});
    expect(result.accepted).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  describe("the single dispatch entry", () => {
    it("dispatches the exact ui_action envelope through one entry", () => {
      openSession();
      const requestId = store.dispatchAction("explore.wait", { daypart: "dusk" });
      expect(requestId).toBe("session:1");
      expect(sender.sent.actions).toEqual([
        {
          protocol_version: 1,
          presentation_epoch: fx.EPOCH_A,
          request_id: "session:1",
          base_revision: 1,
          action_id: "explore.wait",
          payload: { daypart: "dusk" },
        },
      ]);
      expect(store.view.dispatch.inFlight).toEqual({ requestId: "session:1", presentationRevision: null });
    });

    it("keeps one mutation in flight and rejects a second dispatch", () => {
      openSession();
      store.dispatchAction("explore.wait", { daypart: "dusk" });
      expect(store.dispatchAction("explore.wait", { sleep: true })).toBe(null);
      expect(sender.sent.actions.length).toBe(1);
    });

    it("refuses dispatch while locked (disconnected, mutation-locked, or not active)", () => {
      // Not connected yet.
      store.beginTransport(1);
      expect(store.dispatchAction("explore.wait", {})).toBe(null);
      store.setConnected(true);
      // Awaiting the first snapshot: not active → locked.
      expect(store.dispatchAction("explore.wait", {})).toBe(null);
      const result = store.receive(1, "ui_snapshot", [fx.snapshot()], {});
      expect(result.accepted).toBe(true);
      expect(store.dispatchAction("explore.wait", {})).toBe("session:1");

      store.setConnected(false);
      expect(store.view.mutationsLocked).toBe(true);
      expect(store.dispatchAction("explore.wait", {})).toBe(null);
    });

    it("holds the mutation lock until the committed revision reaches the declared presentation revision", () => {
      openSession();
      const requestId = store.dispatchAction("explore.wait", { daypart: "dusk" });
      expect(requestId).toBe("session:1");

      // The result declares the presentation revision the recovery must reach.
      store.receive(1, "ui_action_result", [fx.actionResult()], {});
      expect(store.view.dispatch.inFlight).toEqual({ requestId: "session:1", presentationRevision: 2 });
      expect(store.dispatchAction("explore.wait", { sleep: true })).toBe(null);

      // The recovery snapshot/update (a C3 resync) commits revision 2: the
      // lock releases only when the committed revision reaches the target.
      store.receive(1, "ui_update", [fx.update({ revision: 2, presentation_epoch: fx.EPOCH_A })], {});
      expect(store.view.dispatch.inFlight).toBe(null);
      expect(store.dispatchAction("explore.wait", { sleep: true })).toBe("session:2");
    });

    it("releases the lock unconditionally on a no_puppet action-result rejection", () => {
      openSession();
      store.dispatchAction("explore.wait", { daypart: "dusk" });
      store.receive(
        1,
        "ui_action_result",
        [
          fx.actionResult({
            request_id: "session:1",
            outcome: "rejected",
            code: "no_puppet",
            message: "前一個操作的結果無法確認",
            presentation_revision: 2,
          }),
        ],
        {},
      );
      // A no_puppet rejection is never gated on a presentation revision.
       expect(store.view.dispatch.inFlight).toBe(null);
       expect(store.dispatchAction("explore.wait", { sleep: true })).toBe("session:2");
     });

     it("releases the in-flight gate immediately when no presentation revision is declared", () => {
       openSession();
       store.dispatchAction("explore.wait", { daypart: "dusk" });
       // A result that declares no presentation revision (0) cannot be gated
       // on any future recovery, so the lock releases on result receipt.
       store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: 0 })], {});
       expect(store.view.dispatch.inFlight).toBe(null);
       // The gate is free again right away (no recovery snapshot needed).
       expect(store.dispatchAction("explore.wait", { sleep: true })).toBe("session:2");
     });

     it("marks an in-flight mutation uncertain when the puppet detaches", () => {
      openSession();
      store.dispatchAction("explore.wait", { daypart: "dusk" });
      store.receive(1, "ui_protocol_error", [fx.protocolError()], {});
      expect(store.view.phase).toBe("detached");
      expect(store.view.mutationsLocked).toBe(true);
      expect(store.view.dispatch.inFlight).toBe(null);
      // The in-flight mutation can never be confirmed after the OOC detach.
      expect(store.view.dispatch.uncertain).toBe(true);
       store.clearUncertain();
       expect(store.view.dispatch.uncertain).toBe(false);
     });

     it("recovers from a synchronous sender failure without keeping the dispatch lock", () => {
       openSession();
       const flaky = {
         actions: [],
         texts: [],
         failNext: true,
         sendAction(envelope) {
           if (flaky.failNext) {
             throw new Error("transport closed");
           }
           flaky.actions.push(envelope);
         },
         sendText(text) {
           flaky.texts.push(text);
         },
       };
       store.setSender(flaky);
       // The failing send marks the mutation uncertain and releases the
       // in-flight lock, so a later dispatch still works (duck finding:
       // a synchronous transport failure must not stick the lock).
       expect(store.dispatchAction("explore.wait", { daypart: "dusk" })).toBe("session:1");
       expect(flaky.actions.length).toBe(0);
       expect(store.view.dispatch.inFlight).toBe(null);
       expect(store.view.dispatch.uncertain).toBe(true);

       flaky.failNext = false;
       expect(store.dispatchAction("explore.wait", { daypart: "dusk" })).toBe("session:2");
       expect(flaky.actions.length).toBe(1);
       expect(flaky.actions[0].request_id).toBe("session:2");
        store.clearUncertain();
        expect(store.view.dispatch.uncertain).toBe(false);
      });

      it("marks an in-flight mutation uncertain on a plain transport loss", () => {
        openSession();
        store.dispatchAction("explore.wait", { daypart: "dusk" });
        expect(store.view.dispatch.uncertain).toBe(false);
        // A plain disconnect (no puppet-detach protocol error) while a
        // mutation is in flight and unconfirmed must mark it uncertain —
        // the offline-locking + uncertain-notice contract (shard 5).
        store.setConnected(false);
        expect(store.view.dispatch.inFlight).toBe(null);
        expect(store.view.dispatch.uncertain).toBe(true);
        store.clearUncertain();
        expect(store.view.dispatch.uncertain).toBe(false);
      });
   });

  describe("text dispatch", () => {
    it("sends ordinary text through the sender and records the command history", () => {
      openSession();
      expect(store.sendText("look")).toBe(true);
      expect(sender.sent.texts).toEqual(["look"]);
      expect(store.commandHistory).toEqual(["look"]);
      const line = store.narrative.find((l) => l.text === "look");
      expect(line.kind).toBe("in");

      store.setConnected(false);
      expect(store.sendText("北")).toBe(false);
      expect(sender.sent.texts.length).toBe(1);
    });

    it("bounds the command history", () => {
      openSession();
      for (let i = 1; i <= 55; i += 1) {
        store.sendText(`cmd-${i}`);
      }
      expect(store.commandHistory.length).toBe(50);
      expect(store.commandHistory[0]).toBe("cmd-6");
      expect(store.commandHistory[49]).toBe("cmd-55");
    });
  });

  describe("the keyboard-router focus slice", () => {
    it("loads the committed exploration frame with the G2 root keys", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      const view = store.view;
      expect(view.focus.key).toBe("move");
      expect(view.focus.label).toBe("移動");
      expect(view.focus.enabled).toBe(true);
      // The G2 root is a single-row 7-column grid; navigate horizontally.
      expect(store.focusPress("ArrowRight")).toBe(true);
      expect(store.view.focus.key).toBe("look");
      expect(store.view.focus.label).toBe("查看");
      expect(store.focusPress("ArrowRight")).toBe(true);
      expect(store.view.focus.key).toBe("interact");
      expect(store.view.focus.label).toBe("互動");
    });

    it("navigates the combat root grid with preserved action keys", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { context_actions: fx.combatActions() } })],
        {},
      );
      expect(store.view.focus.key).toBe("attack");
      expect(store.view.focus.label).toBe("攻擊");
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("forfeit");
      expect(store.view.focus.label).toBe("投降");
    });

    it("rebuilds the frame only when the committed panel content changes", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      expect(store.view.focus.key).toBe("move");
      store.focusPress("ArrowRight");
      expect(store.view.focus.key).toBe("look");

      // An identical update must not reset the focus position.
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 3, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      expect(store.view.focus.key).toBe("look");

      // A changed panel (the inventory surface disappears) resets the frame
      // focus to the first root item.
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 4,
            panels: {
              exploration: fx.explorationPanel({ inventory: { available: false } }),
              local_map: fx.localMapPanel(),
            },
          }),
        ],
        {},
      );
      expect(store.view.focus.key).toBe("move");
     });

    it("routes a confirmed action item through the single dispatch entry", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      // Navigate the G2 root to the "wait" entry (col 6): ArrowRight x6 from "move".
      for (let i = 0; i < 6; i += 1) {
        store.focusPress("ArrowRight");
      }
      expect(store.view.focus.key).toBe("wait");
      // Confirming "wait" opens the wait submenu (openSubmenu).
      expect(store.focusConfirm("keyboard")).toBe(true);
      // Within the wait submenu (2-column grid), reach "wait-dusk":
      // ArrowDown → wait-noon (row 1 col 0), ArrowRight → wait-dusk (row 1 col 1).
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.focusPress("ArrowRight")).toBe(true);
      expect(store.view.focus.key).toBe("wait-dusk");
      // Confirming the leaf dispatches the exact `explore.wait` action.
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      // `base_revision` is the committed revision at dispatch time (the
      // exploration update advanced it to 2).
      expect(sender.sent.actions[0]).toEqual({
        protocol_version: 1,
        presentation_epoch: fx.EPOCH_A,
        request_id: "session:1",
        base_revision: 2,
        action_id: "explore.wait",
        payload: { daypart: "dusk" },
      });
    });

    it("never submits a disabled or locked item", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      // Confirming the "move" root entry opens the move submenu.
      expect(store.focusConfirm("keyboard")).toBe(true);
      // Move focus to the disabled "exit-north" (row 0, col 1) and confirm:
      // a disabled item emits a `disabled` notice and never dispatches.
      expect(store.focusPress("ArrowRight")).toBe(true);
      expect(store.view.focus.key).toBe("exit-north");
      expect(store.view.focus.enabled).toBe(false);
      expect(store.focusConfirm("keyboard")).toBe(false);
      expect(sender.sent.actions.length).toBe(0);

      // Pointer activation shares the same gates (mutation-lock + enabled).
      store.focusPress("ArrowLeft"); // back to the enabled "exit-east"
      store.dispatchAction("explore.wait", { daypart: "dusk" });
      expect(store.focusConfirm("pointer")).toBe(false);
      expect(store.view.dispatch.inFlight).not.toEqual(null);
      expect(sender.sent.actions.length).toBe(1);
    });
  });

  describe("navigation and target intents", () => {
    it("records a navigation surface intent instead of inventing an OOB action", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      // Navigate the G2 root to "character" (col 3): ArrowRight x3 from "move".
      for (let i = 0; i < 3; i += 1) {
        store.focusPress("ArrowRight");
      }
      expect(store.view.focus.key).toBe("character");
      expect(store.focusConfirm("keyboard")).toBe(true);
      // The character entry re-homes the character sub-dock; no OOB action is
      // invented (the surface intent is client-local).
      expect(store.view.activeSubDock).toBe("character");
      expect(sender.sent.actions.length).toBe(0);
    });

    it("submits a SINGLE-target skill as a combat.cast action", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({
          revision: 2,
          panels: {
            context_actions: fx.combatActions({
              skills: [
                {
                  category: "innate_gift",
                  label: "天賦",
                  groups: [
                    {
                      group: null,
                      label: null,
                      skills: [
                        {
                          key: "basic_attack",
                          label: "攻擊",
                          description: "基本攻擊，對單一目標造成傷害。",
                          cost: {},
                          target_spec: "single",
                          element: null,
                          enabled: true,
                          disabled_reason: null,
                          targets: [7, 8],
                          shorthands: [],
                        },
                      ],
                    },
                  ],
                },
              ],
            }),
          },
        })],
        {},
      );
      // Confirm the focused root "attack" to open the target frame, then
      // confirm the first target (identity 7) — this submits a real
      // combat.cast ui_action envelope (never a bare identity intent).
      expect(store.focusPress("Enter")).toBe(true);
      expect(store.focusConfirm("keyboard")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      expect(sender.sent.actions[0].action_id).toBe("combat.cast");
      expect(sender.sent.actions[0].payload.skill_key).toBe("basic_attack");
      expect(sender.sent.actions[0].payload.target_ids).toEqual([7]);
    });
  });
});
