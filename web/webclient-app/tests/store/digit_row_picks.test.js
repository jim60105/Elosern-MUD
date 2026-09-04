// webclient-align-01-dock-chrome (task 2.4): the legend names `數字鍵 1–4`
// as real behaviour. A digit moves the dock's focus onto the Nth row of the
// current frame (1-indexed, rendered order) and activates it through the
// same confirm path Enter uses. A digit whose row does not exist is
// unclaimed and falls through to the text / command-history path.

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

describe("dock digit row picks (1–4)", () => {
  let store;
  let sender;

  function openSession() {
    store.beginTransport(1);
    store.setConnected(true);
    expect(store.receive(1, "ui_snapshot", [fx.snapshot()], {}).accepted).toBe(true);
  }

  function openMoveFrame() {
    // The exploration panel provides the move submenu; open it so the
    // current frame has known rows: exit-east (enabled), exit-north (disabled).
    store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
      {},
    );
    expect(store.focusConfirm("keyboard")).toBe(true); // root entry -> move frame
    expect(store.view.dockDepth).toBe(2);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  it("digit 1 picks the first row and submits it exactly as Enter would", () => {
    openSession();
    openMoveFrame();
    expect(store.focusPress("1")).toBe(true);
    expect(store.view.focus.key).toBe("exit-east");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.move",
      payload: { exit_ref: "east" },
    });
  });

  it("digit 2 moves focus onto a disabled row, shows its explanation, and submits nothing", () => {
    openSession();
    openMoveFrame();
    expect(store.focusPress("2")).toBe(true);
    expect(store.view.focus.key).toBe("exit-north");
    expect(store.view.focus.enabled).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a digit beyond the frame's row count is unclaimed and submits nothing", () => {
    openSession();
    openMoveFrame();
    // The move frame has three rows (two exits plus the breadcrumb row):
    // `4` is unclaimed.
    expect(store.focusPress("4")).toBe(false);
    // An untouched digit does not consume the key: focus stays where it was.
    expect(store.view.focus.key).toBe("exit-east");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("an unconsumed digit before any frame is mounted is unclaimed", () => {
    // Pre-session: no snapshot received, so the router stack is empty and a
    // digit press must stay total (false, no throw, no submit).
    expect(store.focusPress("1")).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("the bounded quantity form captures digits before the row pick", () => {
    openSession();
    // The quantity form is a local UI exception whose open state the store
    // publishes (services rows open it through the row-activation path);
    // while open, a digit edits the quantity and is consumed before the
    // dock row pick ever sees it.
    store.quantityForm = {
      itemKey: "item-1",
      actionId: "shop.buy",
      itemLabel: "麵包",
      state: { min: 1, max: 9, raw: "", value: null },
      open: true,
    };
    expect(store.focusPress("1")).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
    // The digit edited the quantity, not the dock.
    store.focusPress("Enter");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "shop.buy",
      payload: { item_key: "item-1", quantity: 1 },
    });
  });

  it("repeat-suppression matches the Enter contract: an immediate second digit-1 is suppressed", () => {
    openSession();
    openMoveFrame();
    expect(store.focusPress("1")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    // The first submit put a mutation in flight; the router's held-repeat
    // guard (source !== pointer) plus the mutation lock mean a second
    // immediate activation cannot double-submit.
    expect(store.focusPress("1")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
  });
});
