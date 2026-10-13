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
  affordances: [
    action("explore.talk_open", "交談"),
    { kind: "navigate", surface: "shop", label: "交易", enabled: true, disabled_reason: null },
    { kind: "navigate", surface: "guild", label: "公會服務", enabled: true, disabled_reason: null },
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
    revision += 1;
    return store.receive(
      1,
      "ui_update",
      [fx.update({ revision, panels: { exploration, local_map: fx.localMapPanel() }, ...extra })],
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

  it("verb rows are verbMenuFor's rows in payload order, ending in 查看 and the back row", () => {
    open();
    store.activatePresence("target-7");
    expect(store.view.presenceVerbs.map((item) => item.key)).toEqual([
      "talk-open",
      "service-shop",
      "service-guild",
      "engage",
      "party-invite",
      "deliver",
      "look-target",
      "back",
    ]);
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

    it("an unavailable panel never reads as a departure", () => {
      open();
      store.activatePresence("target-7");
      commit({ schema_version: 3, available: false, reason: { code: "scene_lost", message: "暫時不可用。" } });
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
                schema_version: 2,
                available: true,
                kind: "dialogue",
                host: { identity: 7, display_name: "店長", portrait_ref: null },
                bond_stage: "親睦",
                line: "「歡迎。」",
                choices: [],
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
      store.refreshView();
      expect(store.view.presenceCard).toBe(null);
    });

    it("a new transport generation leaves no card open", () => {
      open();
      store.activatePresence("target-7");
      store.beginTransport(2);
      expect(store.view.presenceCard).toBe(null);
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
