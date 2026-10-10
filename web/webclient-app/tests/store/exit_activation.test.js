// exploration-exit-compass (task 3.1): the exit compass submits through the
// store's exit gate (`store.activateExit`). The row is re-resolved from the
// committed panels at activation time and handed to the one exploration
// submit handler, so the envelope and the command echo are byte-identical to
// what the retired exit chip produced; a disabled exit, a mutation in flight,
// and an awaited presentation revision all submit nothing.
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import ExplorationMenu from "../../lib/exploration_menu.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

function openExploration(store) {
  store.beginTransport(1);
  store.setConnected(true);
  expect(store.receive(1, "ui_snapshot", [fx.snapshot()], {}).accepted).toBe(true);
  store.receive(
    1,
    "ui_update",
    [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
    {},
  );
}

function freshStore() {
  setActivePinia(createPinia());
  const store = useElosernStore();
  const sender = fx.createFakeSender();
  store.setSender(sender);
  return { store, sender };
}

describe("store.activateExit (the exit compass's gate)", () => {
  let store;
  let sender;

  beforeEach(() => {
    ({ store, sender } = freshStore());
  });

  it("exposes the committed exit rows outside the router root", () => {
    openExploration(store);
    const rows = store.view.explorationExits;
    expect(rows).toEqual(ExplorationMenu.moveItems(fx.explorationPanel(), "room:42"));
    expect(store.view.explorationCurrentNode).toBe("room:42");
    expect(store.view.rootMenu.items.some((item) => item.key.startsWith("exit-"))).toBe(false);
  });

  it("submits an envelope and echo byte-identical to the old exit chip's", () => {
    openExploration(store);
    const result = store.activateExit("east");
    expect(result).toEqual({ sent: true, requestId: "session:1" });

    // The old chip path: the router's submit handed the committed move row to
    // the exploration handler, which called the single dispatch entry with
    // the row's payload and command-display descriptor.
    const reference = freshStore();
    openExploration(reference.store);
    const row = ExplorationMenu.moveItems(fx.explorationPanel(), "room:42").find((r) => r.key === "exit-east");
    reference.store.dispatchAction(row.actionId, row.payload, row.commandDisplay);

    expect(sender.sent.actions).toHaveLength(1);
    expect(JSON.stringify(sender.sent.actions[0])).toBe(JSON.stringify(reference.sender.sent.actions[0]));
    expect(sender.sent.actions[0].payload).toEqual({ exit_ref: "east", current_node: "room:42" });
    const lines = (s) => {
      const narrative = s.narrative && "value" in s.narrative ? s.narrative.value : s.narrative;
      return JSON.stringify(Array.from(narrative || [], (line) => ({ ...line, id: undefined, seq: undefined })));
    };
    expect(lines(store)).toBe(lines(reference.store));
    expect(lines(store)).toContain("西風酒館");
  });

  it("a disabled exit submits nothing", () => {
    openExploration(store);
    expect(store.activateExit("north")).toMatchObject({ sent: false, reason: "disabled" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("an exit the committed panel no longer lists submits nothing", () => {
    openExploration(store);
    expect(store.activateExit("gone")).toEqual({ sent: false, reason: "missing" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a mutation in flight suppresses the activation", () => {
    openExploration(store);
    expect(store.activateExit("east").sent).toBe(true);
    expect(store.view.submitLocked).toBe(true);
    expect(store.activateExit("east")).toEqual({ sent: false, reason: "locked" });
    expect(sender.sent.actions).toHaveLength(1);
  });

  it("an awaited presentation revision suppresses the activation until it commits", () => {
    openExploration(store);
    expect(store.activateExit("east").sent).toBe(true);
    // The result declares revision 3; the gate holds until it commits.
    store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: 3 })], {});
    expect(store.view.submitLocked).toBe(true);
    expect(store.activateExit("east")).toEqual({ sent: false, reason: "locked" });
    expect(sender.sent.actions).toHaveLength(1);
    store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 3, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
      {},
    );
    expect(store.view.submitLocked).toBe(false);
    expect(store.activateExit("east").sent).toBe(true);
    expect(sender.sent.actions).toHaveLength(2);
  });

  it("refuses outside the exploration form", () => {
    openExploration(store);
    store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 3, mode: "combat", panels: { context_actions: fx.combatActions() } })],
      {},
    );
    expect(store.activateExit("east")).toEqual({ sent: false, reason: "mode" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("re-resolves the row at activation time: a newer room's exit is the one sent", () => {
    openExploration(store);
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 3,
          panels: {
            exploration: fx.explorationPanel({
              move: [{ exit_ref: "south", label: "南", destination: "room:50", enabled: true, disabled_reason: null }],
            }),
            local_map: fx.localMapPanel(),
          },
        }),
      ],
      {},
    );
    expect(store.activateExit("east")).toEqual({ sent: false, reason: "missing" });
    expect(store.activateExit("south").sent).toBe(true);
    expect(sender.sent.actions[0].payload).toEqual({ exit_ref: "south", current_node: "room:42" });
  });
});
