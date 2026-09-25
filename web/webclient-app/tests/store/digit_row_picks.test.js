// webclient-align-01-dock-chrome (task 2.4): the legend names `數字鍵 1–4`
// as real behaviour. A digit moves the dock's focus onto the Nth row of the
// current frame (1-indexed, rendered order) and activates it through the
// same confirm path Enter uses. A digit whose row does not exist is
// unclaimed and falls through to the text / command-history path.
//
// webclient-scene-overview-swap: the dock's root frame is the scene overview,
// so its chips in reading order are the root frame's rendered rows, and a
// person chip's verb popover is the root's one child frame.
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

  // The exploration root: the scene overview, whose chips are the root
  // frame's rendered rows — exit-east (enabled), exit-north (disabled),
  // target-7, object-3, look-room, wait, suggestions.
  function openOverview(explorationOverrides = undefined) {
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          panels: {
            exploration: fx.explorationPanel(explorationOverrides),
            local_map: fx.localMapPanel(),
          },
        }),
      ],
      {},
    );
    expect(store.view.dockSource).toBe("exploration.root");
    expect(store.view.dockDepth).toBe(1);
  }

  // A person chip whose target maps to no affordance: the popover then holds
  // exactly [查看, 返回上一層].
  function openLookOnlyPopover() {
    openOverview({
      interact: [
        { identity: 9001, display_name: "石像", portrait_ref: null, affordances: [] },
      ],
    });
    expect(store.focusItemByKey("target-9001")).toBe(true);
    expect(store.focusConfirm("keyboard")).toBe(true);
    expect(store.view.dockDepth).toBe(2);
    expect(store.view.dockSource).toBe("exploration.target");
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  it("digit 1 picks the first chip and submits it exactly as Enter would", () => {
    openSession();
    openOverview();
    expect(store.focusPress("1")).toBe(true);
    expect(store.view.focus.key).toBe("exit-east");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.move",
      payload: { exit_ref: "east" },
    });
  });

  it("digit 2 moves focus onto a disabled chip, shows its explanation, and submits nothing", () => {
    openSession();
    openOverview();
    expect(store.focusPress("2")).toBe(true);
    expect(store.view.focus.key).toBe("exit-north");
    expect(store.view.focus.enabled).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a digit beyond the frame's row count is unclaimed and submits nothing", () => {
    openSession();
    openLookOnlyPopover();
    // The popover renders exactly two rows (查看 and 返回上一層), so `3` and
    // `4` are unclaimed.
    expect(store.focusPress("3")).toBe(false);
    expect(store.focusPress("4")).toBe(false);
    // An untouched digit does not consume the key: focus stays where it was.
    expect(store.view.focus.key).toBe("look-target");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("the digit slots follow the rendered rows: the popover's back row takes a slot", () => {
    openSession();
    openLookOnlyPopover();
    // The popover's `back` row is a rendered row of its listbox (the exit
    // outlet's non-rendered cell is gone with the outlet), so `2` addresses
    // it and pops exactly one level with no dispatch.
    expect(store.focusPress("2")).toBe(true);
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.dockSource).toBe("exploration.root");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("the overview's chips follow reading order: digit 3 opens the person's verb popover", () => {
    openSession();
    openOverview();
    // The overview renders exits, then people, then objects, then the
    // footer, so slot 3 is the person chip.
    expect(store.router.currentMenu().items[2].key).toBe("target-7");
    expect(store.focusPress("3")).toBe(true);
    expect(store.view.dockSource).toBe("exploration.target");
    expect(store.view.dockDepth).toBe(2);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("an unconsumed digit before any frame is mounted is unclaimed", () => {
    // Pre-session: no snapshot received, so the router stack is empty and a
    // digit press must stay total (false, no throw, no submit).
    expect(store.focusPress("1")).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("held digit repeats are suppressed like held Enter, even after the lock releases", () => {
    openSession();
    openOverview();
    expect(store.focusPress("1")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    // Release the mutation lock exactly like a committed result does
    // (result declares the revision, the update reaches it). A held-key
    // repeat arriving after that point must still be suppressed — the
    // router's Enter-repeat branch is the reference behaviour.
    store.receive(1, "ui_action_result", [fx.actionResult()], {});
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          panels: { exploration: fx.explorationPanel(), local_map: fx.localMapPanel() },
        }),
      ],
      {},
    );
    expect(store.view.dispatch.inFlight).toBe(null);
    expect(store.focusPress("1", true)).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    // The digit binding itself still works for a fresh press after the
    // suppression (the row re-submits once the lock is clear).
    expect(store.focusPress("1", false)).toBe(true);
    expect(sender.sent.actions).toHaveLength(2);
  });
});
