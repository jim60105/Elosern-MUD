// exploration-presence-rail (tasks 3.1/3.2, design D2): the store's presence
// slice. The rail's entries, the client-local verb and overflow cards (no
// router frame, no request to open), the one gated activation every row
// outside the router shares, payloads byte-identical to the retired popover
// rows, and the commit-time settle: a departed person closes the card with
// a flash, a move or a mode change closes it quietly, and an unavailable
// panel or a pending submission never reads as a departure.
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import ExplorationMenu from "../../lib/exploration_menu.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

function action(action_id, label, extra = {}) {
  return { kind: "action", action_id, label, enabled: true, disabled_reason: null, ...extra };
}

// A clerk carrying every affordance kind the retired popover mapped.
const CLERK = {
  identity: 7,
  display_name: "店長",
  portrait_ref: null,
  services: { state: "ready", entries: [
    { key: "shop", label: "交易", enabled: true, disabled_reason: null, route: { kind: "services", npc_id: 7, section: "shop" } },
    { key: "guild", label: "公會服務", enabled: true, disabled_reason: null, route: { kind: "services", npc_id: 7, section: "board" } },
  ] },
  affordances: [
    action("explore.talk_open", "交談"),
    action("explore.engage", "戰鬥"),
    action("explore.party_invite", "邀請"),
    action("explore.deliver", "交付 藥草 給 店長", { params: { npc_id: 7, item_key: "herb" } }),
  ],
};

const LOCKED_TALK = {
  identity: 9,
  display_name: "守衛",
  portrait_ref: null,
  affordances: [
    {
      kind: "action",
      action_id: "explore.talk_open",
      label: "交談",
      enabled: false,
      disabled_reason: { code: "busy", message: "守衛正在值勤。" },
    },
  ],
};

function panelWith(interact, extra = {}) {
  return fx.explorationPanel({ interact, ...extra });
}

describe("the presence slice (exploration-presence-rail)", () => {
  let store;
  let sender;
  let revision;

  function open(interact = [CLERK]) {
    store.beginTransport(1);
    store.setConnected(true);
    revision = 1;
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          panels: {
            status: fx.statusPanel(),
            exploration: panelWith(interact),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  function commit(exploration, extra = {}) {
    const { panels: extraPanels, ...rest } = extra;
    revision += 1;
    return store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision,
          panels: { exploration, local_map: fx.localMapPanel(), ...(extraPanels || {}) },
          ...rest,
        }),
      ],
      {},
    );
  }

  // Release the in-flight gate exactly like a committed result does.
  function settleResult() {
    store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: revision + 1 })], {});
    commit(panelWith([]));
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  it("opening a verb card is local: no request, no router frame", () => {
    open();
    expect(store.activatePresence("target-7")).toMatchObject({ sent: false, handled: true });
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7, name: "店長", openerKey: "target-7" });
    expect(store.view.railVisible).toBe(false);
    expect(store.router.depth()).toBe(1);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.closePresenceCard()).toBe(true);
    expect(store.view.presenceCard).toBe(null);
    expect(store.view.railVisible).toBe(true);
  });

  it("keeps a service read bound to the selected host among same-class hosts", () => {
    const other = { ...CLERK, identity: 8, services: { state: "none", entries: [] } };
    open([CLERK, other]);
    store.activatePresence("target-7");
    store.activatePresenceVerb("service-shop");
    expect(store.view.serviceReadRequest).toMatchObject({ slot: "shop", npcId: 7, section: "shop" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("routes enrollment to input only and clears it across transport replacement", () => {
    const host = { ...CLERK, services: { state: "ready", entries: [{
      key: "church.enroll", label: "入教", enabled: true, disabled_reason: null,
      route: { kind: "command", npc_id: 7, command: "church join" },
    }] } };
    open([host]);
    store.activatePresence("target-7");
    store.activatePresenceVerb("service-church.enroll");
    expect(store.view.commandPrefill.text).toBe("church join #7");
    expect(sender.sent.actions).toHaveLength(0);
    store.beginTransport(2);
    expect(store.view.commandPrefill).toBeNull();
  });

  it("opens the exact dialogue host and retains only a local topic focus", () => {
    const host = { ...CLERK, services: { state: "ready", entries: [{
      key: "dialogue.offer", label: "委託", enabled: true, disabled_reason: null,
      route: { kind: "dialogue", npc_id: 7, topic_id: "t_offer" },
    }] } };
    open([host]);
    store.activatePresence("target-7");
    store.activatePresenceVerb("service-dialogue.offer");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.talk_open", payload: { npc_id: 7 } });
    expect(store.view.dialogueFocusTopic).toMatchObject({ npcId: 7, topicId: "t_offer" });
    store.beginTransport(2);
    expect(store.view.dialogueFocusTopic).toBeNull();
  });

  it("the card groups the fixed common slots, the conditional rows and the services", () => {
    open();
    store.activatePresence("target-7");
    expect(store.view.presenceVerbs.map((item) => item.key)).toEqual([
      "talk-open",
      "look-target",
      "party-invite",
      "deliver",
      "engage",
      "service-shop",
      "service-guild",
      "back",
    ]);
    expect(store.view.presenceVerbs.map((item) => item.group)).toEqual([
      "common",
      "common",
      "conditional",
      "conditional",
      "conditional",
      "services",
      "services",
      undefined,
    ]);
    // The trailing row is the unnumbered return.
    expect(store.view.presenceVerbs.at(-1).goBack).toBe(true);
  });

  describe("payloads byte-identical to the retired popover rows", () => {
    const SUBMITTING = ["talk-open", "engage", "party-invite", "deliver", "look-target"];
    for (const key of SUBMITTING) {
      it(`${key} submits the builder row's action and payload once`, () => {
        open();
        const model = ExplorationMenu.buildMenus(panelWith([CLERK]), {});
        const row = ExplorationMenu.verbMenuFor(model, ExplorationMenu.targetById(model, 7)).items.find(
          (item) => item.key === key,
        );
        store.activatePresence("target-7");
        expect(store.activatePresenceVerb(key).sent).toBe(true);
        expect(sender.sent.actions).toHaveLength(1);
        expect(sender.sent.actions[0].action_id).toBe(row.actionId);
        expect(JSON.stringify(sender.sent.actions[0].payload)).toBe(JSON.stringify(row.payload));
      });
    }

    it("查看 closes the card once it is sent", () => {
      open();
      store.activatePresence("target-7");
      store.activatePresenceVerb("look-target");
      expect(store.view.presenceCard).toBe(null);
    });

    it("a navigate row opens its drawer without a frame or a request and keeps the card", () => {
      open();
      store.activatePresence("target-7");
      expect(store.activatePresenceVerb("service-guild")).toMatchObject({ sent: false, handled: true });
      expect(store.view.hudDrawer).toBe("quest");
      expect(store.router.depth()).toBe(1);
      expect(sender.sent.actions).toHaveLength(0);
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
      store.closeHudDrawer();
      expect(store.activatePresenceVerb("service-shop").handled).toBe(true);
      expect(store.view.hudDrawer).toBe("shop");
    });

    it("the rail's bystander and object entries submit the old look chips' payloads", () => {
      open([]);
      expect(store.activatePresence("entity-7").sent).toBe(true);
      settleResult();
      expect(store.activatePresence("object-3").sent).toBe(true);
      const look = ExplorationMenu.lookItems(fx.explorationPanel());
      expect(sender.sent.actions.map((a) => JSON.stringify(a.payload))).toEqual([
        JSON.stringify(look.find((item) => item.key === "entity-7").payload),
        JSON.stringify(look.find((item) => item.key === "object-3").payload),
      ]);
    });
  });

  it("a disabled row explains itself and submits nothing", () => {
    open([LOCKED_TALK]);
    store.activatePresence("target-9");
    const row = store.view.presenceVerbs.find((item) => item.key === "talk-open");
    expect(row.enabled).toBe(false);
    expect(row.disabledReason.message).toBe("守衛正在值勤。");
    expect(store.activatePresenceVerb("talk-open")).toMatchObject({ sent: false, reason: "disabled" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a vanished verb row does nothing", () => {
    open();
    store.activatePresence("target-7");
    expect(store.activatePresenceVerb("no-such-row")).toMatchObject({ sent: false, reason: "missing" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  // slice U: the fixed common slots stay in place for a target whose
  // descriptor carries no talk row of its own, and the fallback is never
  // callable.
  it("a target with no talk row keeps a disabled 交談 at slot 1 and 查看 at 2", () => {
    const goblin = {
      identity: 11,
      display_name: "哥布林",
      portrait_ref: null,
      services: { state: "none", entries: [] },
      affordances: [action("explore.engage", "戰鬥")],
    };
    open([goblin]);
    store.activatePresence("target-11");
    expect(store.view.presenceVerbs.map((item) => item.key)).toEqual([
      "talk-open",
      "look-target",
      "engage",
      "back",
    ]);
    expect(store.view.presenceVerbs[0]).toMatchObject({ enabled: false, actionId: null });
    expect(store.view.presenceVerbs[0].disabledReason.code).toBe("not_conversable");
    expect(store.activatePresenceVerb("talk-open")).toMatchObject({ sent: false, reason: "disabled" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  describe("the rendered mapping", () => {
    it("an equal-content re-publication keeps the card and its mapping", () => {
      open();
      store.activatePresence("target-7");
      const token = store.view.presenceMapping.token;
      commit(panelWith([CLERK]));
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
      expect(store.view.presenceMapping.token).toBe(token);
    });

    it("a changed entry set consumes an activation made against the previous mapping", () => {
      open();
      store.activatePresence("target-7");
      const rendered = store.view.presenceMapping.token;
      const paused = {
        ...CLERK,
        services: {
          state: "ready",
          entries: [
            {
              key: "guild",
              label: "公會服務",
              enabled: false,
              disabled_reason: { code: "paused", message: "公會服務暫時停止。" },
              route: { kind: "services", npc_id: 7, section: "board" },
            },
          ],
        },
      };
      commit(panelWith([paused]));
      // The queued activation still names the rows the player saw: it is
      // consumed without sending, and never reaches the row that now sits
      // at that key.
      expect(store.activatePresenceVerb("service-guild", rendered)).toMatchObject({
        sent: false,
        handled: true,
        reason: "stale",
      });
      expect(sender.sent.actions).toHaveLength(0);
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
      // A fresh selection against the current mapping acts on this row.
      expect(store.activatePresenceVerb("service-guild", store.view.presenceMapping.token)).toMatchObject({
        sent: false,
        reason: "disabled",
      });
    });

    it("a digit press against an obsolete mapping is consumed without acting", () => {
      open();
      store.activatePresence("target-7");
      store.acknowledgePresenceMapping(store.view.presenceMapping.token);
      const paused = {
        ...CLERK,
        services: {
          state: "ready",
          entries: [
            {
              key: "guild",
              label: "公會服務",
              enabled: true,
              disabled_reason: null,
              route: { kind: "services", npc_id: 7, section: "board" },
            },
          ],
        },
      };
      commit(panelWith([paused]));
      // Slot 6 named 交易 before the commit; without a fresh render the press
      // must not open the row that took the position.
      expect(store.focusPress("6")).toBe(true);
      expect(store.view.hudDrawer).toBe(null);
      expect(sender.sent.actions).toHaveLength(0);
      // Once the card has drawn its current mapping, the digit acts again.
      store.acknowledgePresenceMapping(store.view.presenceMapping.token);
      expect(store.focusPress("6")).toBe(true);
      expect(store.view.hudDrawer).toBe("quest");
    });
  });

  describe("the service origin", () => {
    it("records the entry that opened the flow and yields it once", () => {
      open();
      store.activatePresence("target-7");
      expect(store.activatePresenceVerb("service-shop").handled).toBe(true);
      expect(store.view.presenceCard.serviceOrigin).toBe("service-shop");
      expect(store.view.presenceCard.serviceDrawer).toBe("shop");
      expect(store.claimPresenceServiceOrigin()).toBe("service-shop");
      expect(store.claimPresenceServiceOrigin()).toBe(null);
    });

    it("a departed provider closes its drawer with the card", () => {
      open();
      store.activatePresence("target-7");
      store.activatePresenceVerb("service-guild");
      expect(store.view.hudDrawer).toBe("quest");
      commit(panelWith([], { look: { entities: [] } }));
      expect(store.view.presenceCard).toBe(null);
      expect(store.view.hudDrawer).toBe(null);
      expect(store.view.presenceNotice).toMatchObject({ name: "店長" });
    });
  });

  it("a possession swap keeps the card and makes a pre-swap selection stale", () => {
    open();
    store.activatePresence("target-7");
    const rendered = store.view.presenceMapping.token;
    commit(panelWith([CLERK]), {
      panels: {
        status: fx.statusPanel({
          actor: { name: "影行者", identity: "77", location: { label: "測試起點", identity: "17" } },
        }),
      },
    });
    // The same player keeps the card across a control swap; nobody left the
    // room, so there is no departure message.
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
    expect(store.view.presenceNotice).toBe(null);
    // The acting body is part of the mapping: the selection made for the old
    // body is consumed and a fresh one acts.
    expect(store.view.presenceMapping.token).not.toBe(rendered);
    expect(store.activatePresenceVerb("service-shop", rendered)).toMatchObject({
      sent: false,
      handled: true,
      reason: "stale",
    });
    expect(store.activatePresenceVerb("service-shop", store.view.presenceMapping.token)).toMatchObject({
      sent: false,
      handled: true,
    });
    expect(store.view.hudDrawer).toBe("shop");
  });

  it("every consumer is suppressed while a submission is in flight or awaiting its revision", () => {
    open([CLERK]);
    store.activatePresence("target-7");
    expect(store.activatePresenceVerb("engage").sent).toBe(true);
    // In flight: the verb card, the rail, and the compass all refuse.
    expect(store.activatePresenceVerb("talk-open")).toMatchObject({ sent: false, reason: "locked" });
    store.closePresenceCard();
    expect(store.activatePresence("object-3")).toMatchObject({ sent: false, reason: "locked" });
    expect(store.activateExit("east")).toMatchObject({ sent: false, reason: "locked" });
    // Awaiting the declared revision: still refused.
    store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: revision + 5 })], {});
    expect(store.view.dispatch.inFlight).not.toBe(null);
    expect(store.activatePresence("object-3")).toMatchObject({ sent: false, reason: "locked" });
    expect(sender.sent.actions).toHaveLength(1);
  });

  describe("the commit-time settle", () => {
    it("a departed person closes the card in that commit and flashes a notice", () => {
      open();
      store.activatePresence("target-7");
      commit(panelWith([], { look: { entities: [] } }));
      expect(store.view.presenceCard).toBe(null);
      expect(store.view.presenceNotice).toMatchObject({ name: "店長" });
      const seq = store.view.presenceNotice.seq;
      // A second departure raises a fresh notice.
      commit(panelWith([CLERK]));
      store.activatePresence("target-7");
      commit(panelWith([], { look: { entities: [] } }));
      expect(store.view.presenceNotice.seq).toBe(seq + 1);
    });

    it("a committed move closes the card without a notice", () => {
      open();
      store.activatePresence("target-7");
      commit(panelWith([], { look: { room: { identity: 99, display_name: "別處", room: true }, entities: [] } }));
      expect(store.view.presenceCard).toBe(null);
      expect(store.view.presenceNotice).toBe(null);
    });

    it("the local map flapping in the same room is not a move", () => {
      open();
      store.activatePresence("target-7");
      const unavailableMap = {
        schema_version: 1,
        available: false,
        reason: { code: "map_unavailable", message: "區域地圖目前無法顯示" },
      };
      revision += 1;
      store.receive(1, "ui_update", [fx.update({ revision, panels: { exploration: panelWith([CLERK]), local_map: unavailableMap } })], {});
      expect(store.view.explorationCurrentNode).toBe(null);
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
      commit(panelWith([CLERK]));
      expect(store.view.explorationCurrentNode).not.toBe(null);
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
    });

    it("a departure while an unrelated submission is pending closes the card in that commit", () => {
      open();
      store.activatePresence("object-3");
      store.activatePresence("target-7");
      // The look is in flight, but the committed availability loss is the
      // first and final word: the card retires at once, correlation and
      // emphasis with it, and the departure is flashed exactly once.
      commit(panelWith([], { look: { entities: [] } }));
      expect(store.view.presenceCard).toBe(null);
      expect(store.view.presenceNotice).toMatchObject({ name: "店長" });
      const seq = store.view.presenceNotice.seq;
      // Later settlement does not flash a duplicate.
      store.receive(1, "ui_action_result", [fx.actionResult({ outcome: "rejected", code: "invalid", message: "不行。" })], {});
      expect(store.view.dispatch.inFlight).toBe(null);
      expect(store.view.presenceCard).toBe(null);
      expect(store.view.presenceNotice.seq).toBe(seq);
    });

    it("an unavailable panel never reads as a departure", () => {
      open();
      store.activatePresence("target-7");
      const result = commit({ schema_version: 5, available: false, reason: { code: "scene_lost", message: "暫時不可用。" } });
      expect(result.accepted).toBe(true);
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
      expect(store.view.presenceNotice).toBe(null);
      commit(panelWith([CLERK]));
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
    });

    it("交談's intermediate commit without the host waits for the dialogue commit", () => {
      open();
      store.activatePresence("target-7");
      expect(store.activatePresenceVerb("talk-open").sent).toBe(true);
      // An exploration commit that already lacks the host, while 交談 is in
      // flight: no close and no flash.
      commit(panelWith([], { look: { entities: [] } }));
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
      expect(store.view.presenceNotice).toBe(null);
      // The dialogue commit closes it quietly.
      revision += 1;
      store.receive(
        1,
        "ui_snapshot",
        [
          fx.snapshot({
            revision,
            mode: "dialogue",
            panels: {
              status: fx.statusPanel(),
              exploration: panelWith([CLERK]),
              local_map: fx.localMapPanel(),
              dialogue: {
                schema_version: 3,
                available: true,
                kind: "dialogue",
                host: { identity: 7, display_name: "店長", portrait_ref: null },
                actor: { identity: 1, display_name: "測試者", portrait_ref: null },
                bond_stage: "親睦",
                context_id: "ctx-1",
                delivery: null,
                choices: [],
                pure_chain: [],
                reading_revision: 0,
                completed_topic_ids: [],
                unlock_batch: null,
              },
            },
          }),
        ],
        {},
      );
      expect(store.view.mode).toBe("dialogue");
      expect(store.view.presenceCard).toBe(null);
      expect(store.view.presenceNotice).toBe(null);
    });

    it("a mode change to combat closes the card", () => {
      open();
      store.activatePresence("target-7");
      revision += 1;
      store.receive(1, "ui_update", [fx.update({ revision, mode: "combat", panels: { context_actions: fx.combatActions() } })], {});
      expect(store.view.mode).toBe("combat");
      expect(store.view.presenceCard).toBe(null);
    });

    it("a root reset closes the card", () => {
      open();
      store.activatePresence("target-7");
      store.resetFramesToRoot();
      expect(store.view.presenceCard).toBe(null);
    });

    it("a new transport generation leaves no card open", () => {
      open();
      store.activatePresence("target-7");
      store.beginTransport(2);
      expect(store.view.presenceCard).toBe(null);
    });
  });

  describe("digits while a card is open", () => {
    it("a held repeat and a digit past the rows are claimed and do nothing", () => {
      open();
      store.activatePresence("target-7");
      expect(store.focusPress("1", true)).toBe(true);
      expect(store.focusPress("9")).toBe(true);
      expect(sender.sent.actions).toHaveLength(0);
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
    });

    it("a drawer over the card takes its digits away", () => {
      open();
      store.activatePresence("target-7");
      expect(store.activatePresenceVerb("service-guild").handled).toBe(true);
      expect(store.view.hudDrawer).toBe("quest");
      expect(store.focusPress("1")).toBe(false);
      expect(sender.sent.actions).toHaveLength(0);
      store.closeHudDrawer();
      expect(store.focusPress("1")).toBe(true);
      expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.talk_open" });
    });

    it("the card owns the digits whatever dock frame is open beneath it, and replaces an open room card", () => {
      open();
      store.router.pushFrame({ source: "exploration.navigation", params: {} }, { openerKey: null });
      store.refreshView();
      expect(store.view.dockDepth).toBe(2);
      expect(store.openRoomCard("wait")).toBe(true);
      store.activatePresence("target-7");
      // One centred card at a time: the person's card replaced the room card.
      expect(store.view.roomCard).toBeNull();
      // The card lists 交談 … 查看; its digit picks never reach the frame beneath.
      const lookSlot = String(store.view.presenceVerbs.findIndex((item) => item.key === "look-target") + 1);
      expect(store.focusPress(lookSlot)).toBe(true);
      expect(sender.sent.actions).toHaveLength(1);
      expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.look", payload: { target_id: 7 } });
    });
  });

  describe("the overflow card", () => {
    const crowd = (count) =>
      Array.from({ length: count }, (_, n) => ({
        identity: 100 + n,
        display_name: `旅人${n + 1}`,
        portrait_ref: null,
        affordances: [],
      }));

    it("＋N opens it, a person picked there opens that person's card, and back points at ＋N", () => {
      open(crowd(7));
      expect(store.activatePresence("presence-more")).toMatchObject({ handled: true });
      expect(store.view.presenceCard).toMatchObject({ kind: "overflow", openerKey: "presence-more" });
      store.activatePresence("target-105");
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 105, openerKey: "presence-more" });
    });

    it("a look picked there submits and closes it", () => {
      // Five people, the 店長 bystander, and the 木箱: seven entries.
      open(crowd(5));
      expect(store.view.presenceEntries).toHaveLength(7);
      store.activatePresence("presence-more");
      expect(store.activatePresence("object-3").sent).toBe(true);
      expect(store.view.presenceCard).toBe(null);
    });

    it("a verb card opened from ＋N survives the fold disappearing", () => {
      open(crowd(7));
      store.activatePresence("presence-more");
      store.activatePresence("target-105");
      commit(panelWith([...crowd(7)].slice(4)));
      expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 105, openerKey: "presence-more" });
    });

    it("closes quietly when nothing is folded any more, and ＋N does nothing without overflow", () => {
      open(crowd(7));
      store.activatePresence("presence-more");
      commit(panelWith(crowd(2)));
      expect(store.view.presenceCard).toBe(null);
      expect(store.view.presenceNotice).toBe(null);
      expect(store.activatePresence("presence-more")).toMatchObject({ handled: false });
    });
  });
});
