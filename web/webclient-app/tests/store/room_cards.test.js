// exploration-room-actions (design D1/D3/D5): the store's client-local room
// card slice — the wait card — beside the presence card. Opening is local
// (no request, no frame); the commit-time settle closes the card on a mode
// change, a move, or an unavailable panel; and the presence card's consumers
// never see a room card.
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

describe("the room card slice (exploration-room-actions)", () => {
  let store;
  let sender;
  let revision;

  function open() {
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
            context_actions: fx.explorationActions(),
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

  it("a presence card and a room card replace one another", () => {
    open();
    expect(store.openRoomCard("wait")).toBe(true);
    store.activatePresence("target-7");
    expect(store.view.roomCard).toBeNull();
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
    expect(store.openRoomCard("wait")).toBe(true);
    expect(store.view.presenceCard).toBeNull();
  });

  it("the rest entry opens only while the exploration panel is available", () => {
    // redesign-rest-entry design D2: the gate reads the committed panel
    // directly (no builder rows); the view publishes no wait-row list.
    open();
    expect(store.view.waitRows).toBeUndefined();
    commit({ exploration: { schema_version: 7, available: false, reason: { code: "scene_lost", message: "暫時不可用。" } } });
    expect(store.openRoomCard("wait")).toBe(false);
    expect(store.view.roomCard).toBeNull();
    commit({ exploration: fx.explorationPanel() });
    expect(store.openRoomCard("wait")).toBe(true);
    expect(store.view.roomCard).toEqual({ kind: "wait" });
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.activateWaitRow).toBeUndefined();
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
    commit({ exploration: { schema_version: 7, available: false, reason: { code: "scene_lost", message: "暫時不可用。" } } });
    expect(store.view.roomCard).toBeNull();
  });

  it("a root reset leaves no room card open", () => {
    open();
    store.openRoomCard("wait");
    store.resetFramesToRoot();
    expect(store.view.roomCard).toBeNull();
  });
});
