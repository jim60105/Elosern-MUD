// webclient-align-08-dialogue-surface (tasks 3.1/3.2/4.2): the store-side
// dialogue form. A committed dialogue mode tears the frame stack down to
// exactly `dialogue.root`; the resolver rows carry the committed keyword ids
// and labels verbatim with payloads naming the committed host; digits pick
// the rendered picks through the same confirm entry; `→` borrows the command
// line while the form presents (never from the input field — the bridge owns
// that gate, asserted at bridge level — and never while degraded); an
// unavailable panel degrades to the shared marker with the server-authored
// reason.

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../stores/elosern.js";
import { createFrameResolver } from "../stores/frame-resolvers.js";
import * as fx from "./store/protocol_fixtures.js";

const DIALOGUE_PANEL = {
  schema_version: 1,
  available: true,
  kind: "dialogue",
  host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
  bond_stage: "親睦",
  line: "「渡河要五枚銅板。」",
  choices: [
    { keyword_id: "fare", label: "「就五枚，走嗎？」" },
    { keyword_id: "smell", label: "含糊帶過氣味" },
    { keyword_id: "chest", label: "直接問箱櫃下落" },
    { keyword_id: "silence", label: "保持沉默" },
  ],
};

const UNAVAILABLE_PANEL = {
  schema_version: 1,
  available: false,
  reason: { code: "dialogue_unavailable", message: "對話目前無法顯示" },
};

function dialogueSnapshot(overrides = {}) {
  return fx.snapshot({
    revision: 4,
    mode: "dialogue",
    panels: { status: fx.statusPanel(), dialogue: DIALOGUE_PANEL, ...overrides },
  });
}

describe("dialogue frame resolver", () => {
  function resolveIn(panels) {
    const state = { mode: "dialogue", panels: { status: fx.statusPanel(), ...panels } };
    return createFrameResolver({ getState: () => state }).resolve({
      source: "dialogue.root",
      params: {},
    });
  }

  it("resolves the committed picks verbatim with payloads naming the committed host", () => {
    const menu = resolveIn({ dialogue: DIALOGUE_PANEL });
    expect(menu.dialogueForm).toBe(true);
    expect(menu.items).toHaveLength(5);
    const [first, , , , free] = menu.items;
    expect(first).toMatchObject({
      key: "dlg-kw-fare",
      label: "「就五枚，走嗎？」",
      actionId: "explore.talk_scripted",
      payload: { npc_id: 41, keyword_id: "fare" },
    });
    expect(free).toMatchObject({ key: "dlg-free", freeform: true, npcId: 41 });
    expect(menu.focusKey).toBe("dlg-kw-fare");
  });

  it("keeps the free row reachable when the panel carries zero choices", () => {
    const menu = resolveIn({ dialogue: { ...DIALOGUE_PANEL, choices: [] } });
    expect(menu.items).toHaveLength(1);
    expect(menu.items[0].key).toBe("dlg-free");
    expect(menu.focusKey).toBe("dlg-free");
  });

  it("degrades an unavailable panel to the marker with the server-authored reason", () => {
    const menu = resolveIn({ dialogue: UNAVAILABLE_PANEL });
    expect(menu.unresolvable).toBe(true);
    expect(menu.reason).toBe("對話目前無法顯示");
  });
});

describe("dialogue store teardown + keys", () => {
  let store;
  let sender;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  function openSession(panels) {
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    expect(
      store.receive(1, "ui_snapshot", [fx.snapshot({ panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), local_map: fx.localMapPanel(), ...panels } })], {}).accepted,
    ).toBe(true);
  }

  it("a dialogue mode switch tears the stack down to exactly dialogue.root", () => {
    openSession();
    // Open one exploration submenu so the teardown has frames to replace.
    expect(store.focusConfirm("keyboard")).toBe(true); // root row -> move frame
    expect(store.view.dockDepth).toBe(2);
    expect(
      store.receive(1, "ui_snapshot", [dialogueSnapshot()], {}).accepted,
    ).toBe(true);
    expect(store.view.mode).toBe("dialogue");
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.rootMenu && store.view.rootMenu.dialogueForm).toBe(true);
    expect(store.view.combatMenu.items.map((i) => i.key)).toEqual([
      "dlg-kw-fare",
      "dlg-kw-smell",
      "dlg-kw-chest",
      "dlg-kw-silence",
      "dlg-free",
    ]);
    // No exploration row remains activatable: the stack holds exactly the
    // dialogue root (depth 1 + the root's own rows, no submenu frame).
    expect(store.view.dockTrail.filter((t) => t === "移動")).toHaveLength(0);
  });

  it("digits 1–4 activate the rendered picks through the shared dispatch entry", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    expect(store.focusPress("2")).toBe(true);
    expect(store.view.focus.key).toBe("dlg-kw-smell");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.talk_scripted",
      payload: { npc_id: 41, keyword_id: "smell" },
    });
  });

  it("a digit beyond the rendered picks falls through unclaimed", () => {
    openSession();
    store.receive(
      1,
      "ui_snapshot",
      [dialogueSnapshot({ dialogue: { ...DIALOGUE_PANEL, choices: [{ keyword_id: "one", label: "一句" }] } })],
      {},
    );
    // 2 rows render (one pick + free row): digit 3 has no row.
    expect(store.focusPress("3")).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("→ borrows the command line for the committed host and dispatches nothing", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    const before = store.view.drawerRequest;
    expect(store.focusPress("ArrowRight")).toBe(true);
    expect(store.view.drawerRequest).toBe(before + 1);
    expect(sender.sent.actions).toHaveLength(0);
    expect(sender.sent.texts).toHaveLength(0);
    // The borrow set the guarded freeform target: an ordinary send goes out
    // as explore.talk_freeform for the host (the existing seam).
    expect(store.sendText("五枚就五枚。")).toBe(true);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.talk_freeform",
      payload: { npc_id: 41, speech: "五枚就五枚。" },
    });
  });

  it("→ is not claimed while the dialogue frame is degraded", () => {
    openSession();
    store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ revision: 4, mode: "dialogue", panels: { status: fx.statusPanel(), dialogue: UNAVAILABLE_PANEL } })],
      {},
    );
    expect(store.view.mode).toBe("dialogue");
    // The root frame degrades: the pane presents the marker row, and the
    // dialogue form is NOT presented.
    expect(store.view.degradedRoot && store.view.degradedRoot.reason).toBe("對話目前無法顯示");
    const before = store.view.drawerRequest;
    store.focusPress("ArrowRight");
    // No borrow: no focus request, no target capture, nothing dispatched —
    // the press falls through to the router's degraded-menu no-op.
    expect(store.view.drawerRequest).toBe(before);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("ArrowRight keeps its router meaning outside dialogue mode", () => {
    openSession();
    const before = store.view.drawerRequest;
    // The G2 root single-row grid: ArrowRight walks the focus columns
    // through the ROUTER (not the borrow path).
    expect(store.focusPress("ArrowRight")).toBe(true);
    expect(store.view.focus.key).toBe("look");
    expect(store.view.drawerRequest).toBe(before);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("leaving dialogue re-homes the stack through the mode-root decision point", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    expect(store.view.rootMenu.dialogueForm).toBe(true);
    expect(
      store.receive(
        1,
        "ui_snapshot",
        [fx.snapshot({ revision: 9, panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), local_map: fx.localMapPanel() } })],
        {},
      ).accepted,
    ).toBe(true);
    expect(store.view.mode).toBe("exploration");
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.rootMenu && store.view.rootMenu.dialogueForm).toBeUndefined();
    // No dialogue row remains activatable: digit picks now address the
    // exploration root grid, and no scripted keyword can dispatch.
    store.focusPress("1");
    expect(sender.sent.actions.every((a) => a.action_id !== "explore.talk_scripted")).toBe(true);
  });
});
