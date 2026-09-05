// webclient-align-11-dialogue-ux (tasks 2.4): the store side of the retired
// dock dialogue form. A committed dialogue mode keeps the dock on
// `exploration.root` (the `dialogue.root` mirror is deleted); digits retarget
// to the caption's scripted picks while the caption presents, and fall
// through to the dock otherwise; the caption's free row keeps the
// command-line borrow through `borrowDialogueCommand`; ArrowRight keeps its
// router meaning; the exit row's `dialogue-leave` dispatch rides the single
// dispatch entry; and exploration-form lifecycle guards widen to dialogue
// mode (a services/character sub-dock opened while talking closes, re-homes,
// and settles exactly as in exploration mode).

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
    panels: {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      local_map: fx.localMapPanel(),
      dialogue: DIALOGUE_PANEL,
      ...overrides,
    },
  });
}

describe("dialogue frame vocabulary", () => {
  function resolveIn(panels, source) {
    const state = { mode: "dialogue", panels: { status: fx.statusPanel(), ...panels } };
    return createFrameResolver({ getState: () => state }).resolve({
      source,
      params: {},
    });
  }

  it("dialogue.root is no longer a registered source (the mirror form is deleted)", () => {
    const menu = resolveIn({ dialogue: DIALOGUE_PANEL }, "dialogue.root");
    // An unregistered source degrades to the shared marker, like any lost
    // frame — nothing in the client references this descriptor anymore.
    expect(menu.unresolvable).toBe(true);
  });

  it("dialogue mode resolves the ordinary exploration root, not a dialogue frame", () => {
    const state = {
      mode: "dialogue",
      panels: {
        status: fx.statusPanel(),
        exploration: fx.explorationPanel(),
        dialogue: DIALOGUE_PANEL,
      },
    };
    const menu = createFrameResolver({ getState: () => state }).resolve({
      source: "exploration.root",
      params: {},
    });
    // The exploration root keeps its ordinary rows and carries NO dialogue
    // form flag: the 對話選項 mirror tab is gone.
    expect(menu.dialogueForm).toBeUndefined();
    const keys = (menu.items || []).map((i) => i.key);
    expect(keys).toContain("move");
    expect(keys).not.toContain("dlg-options");
  });
});

describe("dialogue store mode lifecycle", () => {
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
      store.receive(
        1,
        "ui_snapshot",
        [
          fx.snapshot({
            panels: {
              status: fx.statusPanel(),
              exploration: fx.explorationPanel(),
              local_map: fx.localMapPanel(),
              ...panels,
            },
          }),
        ],
        {},
      ).accepted,
    ).toBe(true);
  }

  it("a dialogue mode switch keeps the dock on exploration.root", () => {
    openSession();
    // Open one exploration submenu so the switch has frames to replace.
    expect(store.focusConfirm("keyboard")).toBe(true); // root row -> move frame
    expect(store.view.dockDepth).toBe(2);
    expect(store.receive(1, "ui_snapshot", [dialogueSnapshot()], {}).accepted).toBe(true);
    expect(store.view.mode).toBe("dialogue");
    expect(store.view.dockDepth).toBe(1);
    // The root frame is the ORDINARY exploration root: no dialogue form,
    // no 對話選項 tab, ordinary rows still activatable.
    expect(store.view.rootMenu && store.view.rootMenu.dialogueForm).toBeUndefined();
    expect(store.view.rootMenu.items.map((i) => i.key)).toContain("move");
  });

  it("digits 1–4 dispatch the caption's scripted picks while the caption presents", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    expect(store.focusPress("2")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.talk_scripted",
      payload: { npc_id: 41, keyword_id: "smell" },
    });
    // The dock's own rows are NOT digit-claimed while the caption presents:
    // no navigation frame opened.
    expect(store.view.dockDepth).toBe(1);
  });

  it("digits beyond the rendered picks fall through unclaimed", () => {
    openSession();
    store.receive(
      1,
      "ui_snapshot",
      [
        dialogueSnapshot({
          dialogue: { ...DIALOGUE_PANEL, choices: [{ keyword_id: "one", label: "一句" }] },
        }),
      ],
      {},
    );
    // Digits address ONLY the rendered caption picks (max four). The free and
    // exit rows take no digit slot, and digit 2 has no pick: the press is
    // unclaimed (the caption branch owns the press and declines).
    expect(store.focusPress("2")).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("an unavailable panel releases the digits back to the dock", () => {
    openSession();
    store.receive(
      1,
      "ui_snapshot",
      [dialogueSnapshot({ dialogue: UNAVAILABLE_PANEL })],
      {},
    );
    expect(store.view.mode).toBe("dialogue");
    // No caption: digit 1 addresses the exploration root grid (focus +
    // confirm opens the Move submenu) — the ordinary dock semantics.
    expect(store.focusPress("1")).toBe(true);
    expect(store.view.dockDepth).toBe(2);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a zero-choice panel releases the digits back to the dock", () => {
    openSession();
    store.receive(
      1,
      "ui_snapshot",
      [dialogueSnapshot({ dialogue: { ...DIALOGUE_PANEL, choices: [] } })],
      {},
    );
    expect(store.focusPress("1")).toBe(true);
    expect(store.view.dockDepth).toBe(2);
  });

  it("the caption free row keeps the command-line borrow", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    const before = store.view.drawerRequest;
    // AppClient maps the feed's dialogue-freeform emit onto this seam.
    expect(store.borrowDialogueCommand()).toBe(true);
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

  it("the borrow declines without a live caption", () => {
    openSession();
    const before = store.view.drawerRequest;
    expect(store.borrowDialogueCommand()).toBe(false);
    expect(store.view.drawerRequest).toBe(before);
  });

  it("the exit dispatch rides the single dispatch entry", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    // AppClient maps the feed's dialogue-leave emit onto the same entry.
    store.dispatchAction("explore.dialogue_leave", { npc_id: 41 }, null);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.dialogue_leave",
      payload: { npc_id: 41 },
    });
  });

  it("ArrowRight keeps its router meaning in dialogue mode (no form borrow)", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    const before = store.view.drawerRequest;
    // The dock's root grid walks focus columns through the ROUTER.
    expect(store.focusPress("ArrowRight")).toBe(true);
    expect(store.view.focus.key).toBe("look");
    expect(store.view.drawerRequest).toBe(before);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("leaving dialogue re-homes nothing further (the dock never left)", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    expect(
      store.receive(
        1,
        "ui_snapshot",
        [
          fx.snapshot({
            revision: 9,
            panels: {
              status: fx.statusPanel(),
              exploration: fx.explorationPanel(),
              local_map: fx.localMapPanel(),
            },
          }),
        ],
        {},
      ).accepted,
    ).toBe(true);
    expect(store.view.mode).toBe("exploration");
    expect(store.view.dockDepth).toBe(1);
    // Digits address the dock again: no scripted keyword can dispatch.
    store.focusPress("1");
    expect(sender.sent.actions.every((a) => a.action_id !== "explore.talk_scripted")).toBe(true);
  });

  it("a character sub-dock opened while talking closes and re-homes on Escape", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    // The services sub-dock mid-conversation (the widened lifecycle guards):
    // Escape pops the frame and the widened menu-close cleanup clears the
    // sub-dock, exactly as in exploration mode.
    store.setActiveSubDock("services");
    store.router.pushFrame({ source: "exploration.move", params: {} }, "services");
    expect(store.view.dockDepth).toBe(2);
    expect(store.view.activeSubDock).toBe("services");
    expect(store.focusEscape()).toBe(true);
    expect(store.view.activeSubDock).toBe(null);
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.focus.key).toBe("move");
  });

  it("an exploration-served drawer close while talking clears the sub-dock and re-homes", () => {
    openSession();
    store.receive(1, "ui_snapshot", [dialogueSnapshot()], {});
    // The 狀態 drawer owns the character sub-dock (the frameless-drawer
    // precedent): closing it while talking must clear the sub-dock and
    // re-home the exploration root — the widened close guard (align-11 D8).
    store.setActiveSubDock("character");
    expect(store.openHudDrawer("status")).toBe(true);
    expect(store.closeHudDrawer({ popFrame: true })).toBe(true);
    // The widened non-hosted close guard (align-11 D8): the sub-dock dies
    // with the drawer and the root frame re-homes, exactly as in exploration.
    expect(store.view.activeSubDock).toBe(null);
    expect(store.router.currentMenu().title).toBe("探索");
  });
});
