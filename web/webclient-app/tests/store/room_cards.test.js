// exploration-room-actions (design D1/D3/D4/D5): the store's client-local
// room card slice — the wait card and the suggestions card — beside the
// presence card. Opening is local (no request, no frame); rows re-resolve
// from the committed panels at activation and run the one exploration gate;
// the commit-time settle closes the card on a mode change, a move, an
// unavailable panel, or (the suggestions card) an envelope that presents
// nothing; and the presence card's consumers never see a room card.
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

const READY = {
  status: "ready",
  cards: [
    { kind: "known_action", action_code: "explore.look", label: "看看木箱", params: { target_id: 3 }, hint: null },
    { kind: "freeform", action_code: "explore.talk_freeform", label: "我們聊聊好嗎？", params: { npc_id: 7 }, hint: null },
    { kind: "known_action", action_code: "explore.look", label: "環顧四周", params: { room: true }, hint: null },
  ],
};

describe("the room card slice (exploration-room-actions)", () => {
  let store;
  let sender;
  let revision;

  function open(suggestions) {
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
            exploration: fx.explorationPanel(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(suggestions ? { suggestions } : undefined),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  function commit(panels, extra = {}) {
    revision += 1;
    expect(store.receive(1, "ui_update", [fx.update({ revision, panels, ...extra })], {}).accepted).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  it("opens locally: no request, no frame, the rail off the stage", () => {
    open();
    expect(store.view.railVisible).toBe(true);
    expect(store.openRoomCard("wait")).toBe(true);
    expect(store.view.roomCard).toEqual({ kind: "wait" });
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.dockSource).toBe("exploration.root");
    expect(store.view.railVisible).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
    // The presence card's consumers see no presence card.
    expect(store.view.presenceCard).toBeNull();
    expect(store.view.presenceVerbs).toBeNull();
    expect(store.openRoomCard("bogus")).toBe(false);
  });

  it("the suggestions card opens only while the envelope presents one", () => {
    open({ status: "unavailable" });
    expect(store.view.suggestionsCard).toBeNull();
    expect(store.openRoomCard("suggestions")).toBe(false);
    expect(store.view.roomCard).toBeNull();
    commit({ context_actions: fx.explorationActions({ suggestions: READY }) });
    expect(store.openRoomCard("suggestions")).toBe(true);
    expect(store.view.suggestionsCard.items.map((item) => item.key)).toEqual([
      "action-explore.look",
      "action-explore.talk_freeform",
      "action-explore.look-2",
      "action-options.dismiss",
    ]);
  });

  it("a presence card and a room card replace one another", () => {
    open();
    expect(store.openRoomCard("wait")).toBe(true);
    store.activatePresence("target-7");
    expect(store.view.roomCard).toBeNull();
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
    expect(store.openRoomCard("wait")).toBe(true);
    expect(store.view.presenceCard).toBeNull();
  });

  it("wait rows submit the builder payloads through the gate and close the card", () => {
    open();
    store.openRoomCard("wait");
    expect(store.activateWaitRow("wait-rest")).toMatchObject({ sent: false, reason: "missing" });
    expect(store.activateWaitRow("wait-dawn")).toMatchObject({ sent: true });
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.wait", payload: { daypart: "dawn" } });
    expect(store.view.roomCard).toBeNull();
    // The card is gone: a second row resolves nothing.
    expect(store.activateWaitRow("wait-sleep")).toMatchObject({ sent: false, reason: "missing" });
    expect(sender.sent.actions).toHaveLength(1);
  });

  it("a locked submission keeps the card open and sends nothing", () => {
    open();
    store.openRoomCard("wait");
    store.dispatchAction("explore.look", { room: true });
    expect(store.activateWaitRow("wait-sleep", { dream: true })).toMatchObject({ sent: false, reason: "locked" });
    expect(store.view.roomCard).toEqual({ kind: "wait" });
    expect(sender.sent.actions).toHaveLength(1);
  });

  it("the dream flag rides only the sleep row", () => {
    open();
    store.openRoomCard("wait");
    expect(store.activateWaitRow("wait-sleep", { dream: true })).toMatchObject({ sent: true });
    expect(sender.sent.actions[0].payload).toEqual({ sleep: true, dream: true });
  });

  it("suggestion rows submit their builder envelopes, dismiss included", () => {
    open(READY);
    store.openRoomCard("suggestions");
    expect(store.activateSuggestion("action-explore.talk_freeform")).toMatchObject({ sent: true });
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.talk_freeform",
      payload: { npc_id: 7, speech: "我們聊聊好嗎？" },
    });
    expect(store.view.roomCard).toBeNull();
  });

  it("closes on a mode change, a move, and an unavailable panel, in that commit", () => {
    open();
    store.openRoomCard("wait");
    commit({ context_actions: fx.combatActions(), local_map: fx.localMapPanel() }, { mode: "combat" });
    expect(store.view.roomCard).toBeNull();

    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(sender);
    open();
    store.openRoomCard("wait");
    commit({ exploration: fx.explorationPanel() });
    expect(store.view.roomCard).toEqual({ kind: "wait" });
    commit({ exploration: fx.explorationPanel({ look: { room: { identity: 77, display_name: "渡口", room: true } } }) });
    expect(store.view.roomCard).toBeNull();

    store.openRoomCard("wait");
    commit({ exploration: { schema_version: 3, available: false, reason: { code: "scene_lost", message: "暫時不可用。" } } });
    expect(store.view.roomCard).toBeNull();
  });

  it("the suggestions card closes when the envelope turns unavailable, and on a transport reset", () => {
    open(READY);
    store.openRoomCard("suggestions");
    commit({ context_actions: fx.explorationActions({ suggestions: { status: "generating" } }) });
    expect(store.view.roomCard).toEqual({ kind: "suggestions" });
    commit({ context_actions: fx.explorationActions({ suggestions: { status: "unavailable" } }) });
    expect(store.view.roomCard).toBeNull();

    commit({ context_actions: fx.explorationActions({ suggestions: READY }) });
    store.openRoomCard("suggestions");
    store.beginTransport(2);
    expect(store.view.roomCard).toBeNull();
    expect(store.activateSuggestion("action-explore.look")).toMatchObject({ sent: false });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("the suggestions card yields to a re-homed sub-dock", () => {
    open(READY);
    store.openRoomCard("suggestions");
    store.setActiveSubDock("character");
    expect(store.view.roomCard).toBeNull();
    expect(store.openRoomCard("suggestions")).toBe(false);
    store.setActiveSubDock(null);
    expect(store.openRoomCard("suggestions")).toBe(true);
  });

  it("a root reset leaves no room card open", () => {
    open();
    store.openRoomCard("wait");
    store.resetFramesToRoot();
    expect(store.view.roomCard).toBeNull();
  });
});
