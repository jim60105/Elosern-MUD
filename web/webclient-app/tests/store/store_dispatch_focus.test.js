// C1 (webclient-vue-07-wire-store) dispatch + focus tests: the single
// dispatch entry (dispatch-only, one mutation in flight) with the tested
// lock semantics, and the keyboard-router focus slice driven by the
// committed `context_actions` panel (the preserved `action-`/`target-` item
// keys as the single key contract).

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";
import CombatMenu from "../../lib/combat_menu.js";
import { SYNTH_SKILL } from "../support/synthetic-data.mjs";

// File-local synthetic rows (test-data-independence): the attack key is wire
// vocabulary owned by the combat model (BASIC_ATTACK_KEY — the root attack
// opener resolves it); the AREA row is the kit skill with invented prose.
const T_ATTACK_KEY = CombatMenu.BASIC_ATTACK_KEY;
// The attack key the beat-queue lock case dispatches (the same model constant):
// wire vocabulary is never spelled out in the suite (test-data-independence).
const ATTACK_KEY = CombatMenu.BASIC_ATTACK_KEY;

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

    it("refuses a dispatch while a combat round plays, and accepts one that ends it", () => {
      // webclient-combat-beat-queue D5 / webclient-combat-menu "A combat round
      // plays beat by beat": the command panel stays locked in addition to
      // the declared-revision lock, and unlocks when both have cleared.
      openSession();
      const requestId = store.dispatchAction("combat.command", ATTACK_KEY);
      store.appendText("out", "你擲出了骰子。");
      store.appendText("out", "你擊中了灰袍盜賊。");
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 2,
            mode: "combat",
            panels: {
              context_actions: fx.combatActions(),
              combat_beats: {
                schema_version: 1,
                available: true,
                round: "s-1/1",
                beats: [
                  {
                    seq: 0,
                    action: 0,
                    kind: "roll",
                    actor: "42",
                    target: "7",
                    amount: null,
                    hp_after: null,
                    text: "你擲出了骰子。",
                  },
                  {
                    seq: 1,
                    action: 1,
                    kind: "damage",
                    actor: "42",
                    target: "7",
                    amount: 12,
                    hp_after: 68,
                    text: "你擊中了灰袍盜賊。",
                  },
                ],
              },
            },
          }),
        ],
        {},
      );
      store.receive(
        1,
        "ui_action_result",
        [fx.actionResult({ request_id: requestId, presentation_revision: 2 })],
        {},
      );
      // The revision is accepted, so only the playback lock holds.
      expect(store.view.dispatch.inFlight).toBe(null);
      expect(store.view.dispatch.beatLocked).toBe(true);
      expect(store.dispatchAction("combat.command", ATTACK_KEY)).toBe(null);
      expect(sender.sent.actions.length).toBe(1);

      store.skipBeats();
      expect(store.view.dispatch.beatLocked).toBe(false);
      expect(store.dispatchAction("combat.command", ATTACK_KEY)).toBe("session:2");
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
    it("loads the empty exploration root with every row outside the router", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      const view = store.view;
      // The exits are the exit compass's (exploration-exit-compass), the
      // people and objects the presence rail's (exploration-presence-rail),
      // and the room actions the place card's and the 建議 pill's
      // (exploration-room-actions), so the root carries no item and nothing
      // is focused on it.
      expect(view.focus.key).toBeNull();
      expect(store.router.rootMenu().items).toEqual([]);
      expect(view.degradedRoot).toBeNull();
      expect(view.dockSource).toBe("exploration.root");
      expect(view.presenceEntries.map((entry) => entry.key)).toEqual(["target-7", "object-3"]);
      expect(view.roomLook.payload).toEqual({ room: true });
      expect(view.waitRows.map((row) => row.key)).toEqual(["wait-dawn", "wait-sleep", "wait-rest"]);
      // No arrow, Enter, or digit is claimed by a root row; Escape and Space
      // keep their frame-independent meaning, with no error and no frame change.
      for (const key of ["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Enter"]) {
        expect(store.focusPress(key)).toBe(false);
      }
      expect(store.focusPress("Escape")).toBe(true);
      expect(store.focusPress(" ")).toBe(true);
      expect(store.view.dockDepth).toBe(1);
      expect(store.view.dockSource).toBe("exploration.root");
      expect(sender.sent.actions.length).toBe(0);
    });

    it("navigates the combat root grid with preserved action keys", () => {
      openSession();
      const panels = { context_actions: fx.combatActions() };
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels })],
        {},
      );
      expect(store.view.focus.key).toBe("attack");
      expect(store.view.focus.label).toBe("攻擊");
      // The combat root is one vertical command list
      // (webclient-combat-command-window): a horizontal press is a no-op,
      // ArrowDown walks the rendered order — the client-local 背包 row
      // included — and wraps from the last row to the first.
      expect(store.focusPress("ArrowRight")).toBe(false);
      expect(store.focusPress("ArrowLeft")).toBe(false);
      expect(store.view.focus.key).toBe("attack");
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("skills");
      expect(store.view.focus.label).toBe("技能");
      for (const key of ["items", "bag", "defend", "flee", "forfeit"]) {
        expect(store.focusPress("ArrowDown")).toBe(true);
        expect(store.view.focus.key).toBe(key);
      }
      expect(store.view.focus.label).toBe("投降");
      expect(store.focusPress("ArrowDown")).toBe(true);
      expect(store.view.focus.key).toBe("attack");
      expect(store.focusPress("ArrowUp")).toBe(true);
      expect(store.view.focus.key).toBe("forfeit");
    });

    it("the combat top-navigation 背包 entry opens inventory without any dispatch", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { context_actions: fx.combatActions() } })],
        {},
      );
      store.tabToRootAndConfirm("bag", "pointer");
      expect(store.view.hudDrawer).toBe("inventory");
      // No OOB packet, no router frame pushed (the frame stays the root).
      expect(sender.sent.actions.length).toBe(0);
      expect(store.view.dockDepth).toBe(1);
    });

    it("a committed update re-resolves the empty root in place", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision: 3,
            panels: {
              exploration: fx.explorationPanel({ inventory: { available: false } }),
              local_map: fx.localMapPanel(),
            },
          }),
        ],
        {},
      );
      expect(store.view.dockDepth).toBe(1);
      expect(store.view.dockSource).toBe("exploration.root");
      expect(store.view.degradedRoot).toBeNull();
      expect(store.view.navigationItems.map((item) => item.key)).not.toContain("inventory");
    });

    it("routes a wait card row through the single dispatch entry", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      // The place card's 等待 opens the client-local wait card (no request),
      // and its sleep row dispatches the exact `explore.wait` action.
      expect(store.openRoomCard("wait")).toBe(true);
      expect(sender.sent.actions.length).toBe(0);
      expect(store.activateWaitRow("wait-sleep")).toMatchObject({ sent: true });
      expect(sender.sent.actions.length).toBe(1);
      // `base_revision` is the committed revision at dispatch time (the
      // exploration update advanced it to 2).
      expect(sender.sent.actions[0]).toEqual({
        protocol_version: 1,
        presentation_epoch: fx.EPOCH_A,
        request_id: "session:1",
        base_revision: 2,
        action_id: "explore.wait",
        payload: { sleep: true },
      });
      expect(store.view.roomCard).toBeNull();
    });

    it("never submits a disabled or locked item", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      );
      // The disabled exit is the compass's: its gated activation submits
      // nothing.
      expect(store.activateExit("north")).toMatchObject({ sent: false, reason: "disabled" });
      expect(sender.sent.actions.length).toBe(0);

      // The place card's 查看房間 shares the same gates (mutation-lock).
       store.dispatchAction("explore.wait", { daypart: "dusk" });
       expect(store.activateRoomLook()).toMatchObject({ sent: false, reason: "locked" });
       // The rail's look entry runs the same gate (exploration-presence-rail).
       expect(store.activatePresence("object-3")).toMatchObject({ sent: false, reason: "locked" });
       expect(store.view.dispatch.inFlight).not.toEqual(null);
       expect(sender.sent.actions.length).toBe(1);
     });

     // H3 (task 3.3): the breadcrumb trail is the router's frame stack, so its
     // length must equal the router depth after every push, pop, replacement,
     // and mode change — the crumb can never lag the frame (design D1).
     it("keeps view.dockTrail.length equal to view.dockDepth across push / pop / replace / mode change", () => {
       openSession();
       const invariant = () => {
         expect(store.view.dockTrail.length).toBe(store.view.dockDepth);
       };
       // Root frame: depth 1, one trail entry (the root title).
       expect(store.view.dockDepth).toBe(1);
       invariant();

       // Push: a resolvable exploration child frame (the exploration family
       // pushes none of its own since exploration-room-actions) — the frame
       // stack grows to depth 2, the trail gains a level.
       const panels2 = { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() };
       store.receive(1, "ui_update", [fx.update({ revision: 2, panels: panels2 })], {});
       store.router.pushFrame({ source: "exploration.navigation", params: {} }, { openerKey: null });
       store.refreshView();
       expect(store.view.dockDepth).toBe(2);
       invariant();

       // Pop: Escape returns to the root frame — depth back to 1.
       expect(store.focusEscape()).toBe(true);
       expect(store.view.dockDepth).toBe(1);
       invariant();

       // Replace: a panel replacement rebuilds the root frame (depth stays 1).
       const panels3 = { exploration: fx.explorationPanel({ inventory: { available: false } }), local_map: fx.localMapPanel() };
       store.receive(1, "ui_update", [fx.update({ revision: 3, panels: panels3 })], {});
       expect(store.view.dockDepth).toBe(1);
       invariant();

       // Mode change: switching to combat resets the router to the combat root
       // frame (depth 1, the combat root title in the trail).
       const panels4 = { context_actions: fx.combatActions(), local_map: fx.localMapPanel() };
       store.receive(1, "ui_update", [fx.update({ revision: 4, mode: "combat", panels: panels4 })], {});
       expect(store.view.dockDepth).toBe(1);
       invariant();
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
      store.tabToRootAndConfirm("character", "pointer");
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
                          targets: [7, 8],
                          shorthands: [],
                          hostile: false,
                          beneficial: false,
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
      expect(sender.sent.actions[0].action_id).toBe("combat.command");
      expect(sender.sent.actions[0].payload.skill_key).toBe(T_ATTACK_KEY);
      expect(sender.sent.actions[0].payload.target_ids).toEqual([7]);
    });

    it("a pointer confirm on a SINGLE target row submits the identical cast", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({
          revision: 2,
          mode: "combat",
          panels: {
            context_actions: fx.combatActions({
              skills: [
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
                          targets: [7, 8],
                          shorthands: [],
                          hostile: false,
                          beneficial: false,
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
      // Open the basic-attack target frame from the root "attack" entry.
      expect(store.focusPress("Enter")).toBe(true);
      // Pointer parity (webclient-pointer-activation): focusing the row and
      // confirming with source "pointer" — exactly what a row click drives —
      // emits the same single combat.cast that Enter emits.
      expect(store.focusItemByKey("target-7")).toBe(true);
      expect(store.focusConfirm("pointer")).toBe(true);
      expect(sender.sent.actions.length).toBe(1);
      expect(sender.sent.actions[0].action_id).toBe("combat.command");
      expect(sender.sent.actions[0].payload.command.payload.skill_key).toBe(T_ATTACK_KEY);
      expect(sender.sent.actions[0].payload.command.payload.target_ids).toEqual([7]);
      expect(store.view.lastTarget).toBe("7");
    });

    it("activating an AREA candidate toggles locally and dispatches nothing", () => {
      openSession();
      store.receive(
        1,
        "ui_update",
        [fx.update({
          revision: 2,
          mode: "combat",
          panels: {
            context_actions: fx.combatActions({
              skills: [
                {
                  category: "martial_arts",
                  label: "武技",
                  groups: [
                    {
                      group: null,
                      label: null,
                      skills: [
                        {
                          key: SYNTH_SKILL.id,
                          label: SYNTH_SKILL.label,
                          description: "範圍火焰傷害。",
                          cost: { mp: 5 },
                          target_spec: "area",
                          element: "fire",
                          enabled: true,
                          disabled_reason: null,
                          targets: [7, 8],
                          shorthands: [],
                          hostile: false,
                          beneficial: false,
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
      // skills tab -> category frame -> group frame -> skill -> AREA targets.
      expect(store.focusItemByKey("skills")).toBe(true);
      store.focusConfirm("keyboard");
      expect(store.focusItemByKey("skill-cat-0")).toBe(true);
      store.focusConfirm("keyboard");
      expect(store.focusItemByKey(SYNTH_SKILL.id)).toBe(true);
      store.focusConfirm("keyboard");
      // The AREA candidate row: deliberate activation (pointer or Enter)
      // toggles the client-local selection; no OOB action is ever invented.
      expect(store.focusItemByKey("area-7")).toBe(true);
      expect(store.focusConfirm("pointer")).toBe(true);
      expect(sender.sent.actions.length).toBe(0);
      expect(store.view.combatSelected).toEqual([7]);
    });
  });
});
