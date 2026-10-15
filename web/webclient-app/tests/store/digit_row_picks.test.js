// webclient-align-01-dock-chrome (task 2.4) + webclient-retire-exploration-
// submenus: the legend names `數字鍵 1–9` as real behaviour. A digit moves the
// dock's focus onto the Nth entry of the current frame (1-indexed, rendered
// order) and activates it through the same confirm path Enter uses. A digit
// whose entry does not exist is unclaimed and falls through to the text /
// command-history path.
//
// webclient-scene-overview-swap: the dock's root frame is the scene overview,
// so its chips in reading order are the root frame's rendered rows, and a
// person chip's verb popover is the root's one child frame.
//
// exploration-exit-compass: the exits left the root frame for the exit
// compass. exploration-presence-rail: the people and objects left it for the
// presence rail, which owns the exploration root's digits — a digit picks
// the Nth visible rail slot, a digit past the slots is claimed and does
// nothing, an empty rail claims none, and none falls through to the footer
// chips. The rail keeps the digits while the dock's waiting or suggestions
// frame is open too; a card owns them while it is open; every other family
// keeps the router's digit picks.
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

// File-local synthetic skill rows (test-data-independence): invented t_-keyed
// combat rows with invented prose; wire taxonomy values stay protocol-owned.
const SIX_SKILL_KEYS = ["t_one", "t_two", "t_three", "t_four", "t_five", "t_six"];

function sixSkillCategory() {
  return [
    {
      category: "martial_arts",
      label: "武技",
      groups: [
        {
          group: null,
          label: null,
          skills: SIX_SKILL_KEYS.map((key, index) => ({
            key,
            label: `招式${index + 1}`,
            description: `第 ${index + 1} 式的合成描述。`,
            cost: { mp: index },
            target_spec: "self",
            element: null,
            enabled: true,
            disabled_reason: null,
            targets: [],
            shorthands: [],
            hostile: false,
            beneficial: false,
          })),
        },
      ],
    },
  ];
}

// A room with two people and one object on the rail, three exits on the
// compass, and the three footer chips (查看房間 ‧ 等待／休息 ‧ 建議).
const SIX_CHIP_OVERRIDES = {
  move: [
    { exit_ref: "east", label: "東", destination: "room:43", enabled: true, disabled_reason: null },
    {
      exit_ref: "north",
      label: "北",
      destination: "room:44",
      enabled: false,
      disabled_reason: { code: "blocked", message: "門被鎖住了" },
    },
    { exit_ref: "west", label: "西", destination: "room:45", enabled: true, disabled_reason: null },
  ],
  interact: [
    {
      identity: 7,
      display_name: "店長",
      portrait_ref: null,
      affordances: [
        {
          kind: "action",
          action_id: "explore.talk_open",
          label: "交談",
          enabled: true,
          disabled_reason: null,
        },
      ],
    },
    { identity: 8, display_name: "吟遊詩人", portrait_ref: null, affordances: [] },
  ],
};

describe("dock digit row picks (1–9)", () => {
  let store;
  let sender;

  function openSession() {
    store.beginTransport(1);
    store.setConnected(true);
    expect(store.receive(1, "ui_snapshot", [fx.snapshot()], {}).accepted).toBe(true);
  }

  // The exploration root: the footer-only overview, with the room's people
  // and objects on the presence rail (exploration-presence-rail) and its
  // exits on the compass.
  function openOverview(explorationOverrides = undefined, contextActions = undefined) {
    const panels = {
      exploration: fx.explorationPanel(explorationOverrides),
      local_map: fx.localMapPanel(),
    };
    if (contextActions !== undefined) {
      panels.context_actions = contextActions;
    }
    store.receive(1, "ui_update", [fx.update({ revision: 2, panels })], {});
    expect(store.view.dockSource).toBe("exploration.root");
    expect(store.view.dockDepth).toBe(1);
  }

  const railKeys = () => store.view.presenceEntries.map((entry) => entry.key);

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  it("digit 2 picks the rail's object entry and submits its look exactly as the old chip did", () => {
    openSession();
    openOverview();
    expect(railKeys()).toEqual(["target-7", "object-3"]);
    expect(store.focusPress("2")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.look",
      payload: { target_id: 3 },
    });
    // The router's empty root never moved: the rail is outside the router.
    expect(store.view.focus.key).toBeNull();
    expect(store.view.dockDepth).toBe(1);
  });

  it("no digit addresses an exit or a room action", () => {
    openSession();
    openOverview(SIX_CHIP_OVERRIDES, fx.explorationActions());
    // The root carries no row at all (exploration-room-actions).
    expect(store.router.currentMenu().items).toEqual([]);
    for (const digit of ["1", "2", "3", "4", "5", "6"]) {
      store.focusPress(digit);
      store.closePresenceCard();
    }
    expect(sender.sent.actions.some((action) => action.action_id === "explore.move")).toBe(false);
    expect(sender.sent.actions.some((action) => action.action_id === "explore.wait")).toBe(false);
    expect(store.view.roomCard).toBeNull();
    expect(store.view.dockSource).toBe("exploration.root");
  });

  it("digit 1 opens the person's verb card: no frame, no action", () => {
    openSession();
    openOverview();
    expect(store.focusPress("1")).toBe(true);
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7, openerKey: "target-7" });
    expect(store.view.presenceVerbs.map((item) => item.key)).toEqual(["talk-open", "look-target", "back"]);
    expect(store.view.dockSource).toBe("exploration.root");
    expect(store.view.dockDepth).toBe(1);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("digits 1–3 pick the rail's entries in order: two people, then the object", () => {
    openSession();
    openOverview(SIX_CHIP_OVERRIDES, fx.explorationActions());
    expect(railKeys()).toEqual(["target-7", "target-8", "object-3"]);
    expect(store.focusPress("2")).toBe(true);
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 8 });
    expect(store.closePresenceCard()).toBe(true);
    expect(store.focusPress("3")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.look", payload: { target_id: 3 } });
  });

  it("a digit beyond the rail's slots is claimed and does nothing", () => {
    openSession();
    openOverview();
    for (const digit of ["3", "4", "9"]) {
      expect(store.focusPress(digit), digit).toBe(true);
    }
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.view.presenceCard).toBe(null);
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.focus.key).toBeNull();
  });

  it("an empty rail claims no digit and never falls through to a dock row", () => {
    openSession();
    openOverview({ interact: [], look: { entities: [], objects: [] } });
    expect(store.view.presenceEntries).toEqual([]);
    expect(store.view.railVisible).toBe(false);
    for (const digit of ["1", "2", "3"]) {
      expect(store.focusPress(digit), digit).toBe(false);
    }
    expect(store.view.dockDepth).toBe(1);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("while a card is open its rows own the digits", () => {
    openSession();
    openOverview();
    expect(store.focusPress("1")).toBe(true);
    // The verb card lists 交談 then 查看: `2` is 查看, `5` is past its rows.
    expect(store.focusPress("5")).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.focusPress("1")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.talk_open", payload: { npc_id: 7 } });
  });

  it("seven entries fold the sixth slot into ＋2, whose digit opens the overflow card", () => {
    openSession();
    const people = [1, 2, 3, 4, 5, 6].map((n) => ({
      identity: 100 + n,
      display_name: `旅人${n}`,
      portrait_ref: null,
      affordances: [],
    }));
    openOverview({ interact: people, look: { entities: [], objects: [{ identity: 3, display_name: "木箱" }] } });
    expect(railKeys()).toHaveLength(7);
    expect(store.focusPress("6")).toBe(true);
    expect(store.view.presenceCard).toMatchObject({ kind: "overflow", openerKey: "presence-more" });
    // The overflow card lists 旅人6 and 木箱: its `1` opens 旅人6's verb card.
    expect(store.focusPress("1")).toBe(true);
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 106, openerKey: "presence-more" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a drawer over the stage hides the rail and its digits", () => {
    openSession();
    openOverview();
    store.openHudDrawer("inventory");
    expect(store.view.railVisible).toBe(false);
    expect(store.focusPress("2")).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("an open room card claims the digits so none reaches the rail beneath it", () => {
    openSession();
    openOverview(undefined, fx.explorationActions({ suggestions: { status: "unavailable" } }));
    expect(store.openRoomCard("wait")).toBe(true);
    expect(store.view.railVisible).toBe(false);
    // `2` is the wait card's (its own keydown handles it), never the rail's
    // object; a stray digit that reaches the store does nothing.
    for (const digit of ["1", "2", "3", "9"]) {
      expect(store.focusPress(digit), digit).toBe(true);
    }
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.view.roomCard).toEqual({ kind: "wait" });
    expect(store.view.presenceCard).toBeNull();
    // Under a drawer the digits are not the card's.
    store.openHudDrawer("inventory");
    expect(store.focusPress("1")).toBe(false);
  });

  it("a combat skill frame's sixth row is reachable by digit 6", () => {
    openSession();
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          mode: "combat",
          panels: { context_actions: fx.combatActions({ skills: sixSkillCategory() }) },
        }),
      ],
      {},
    );
    // The skills tab opens the category frame; the single sub-group collapses
    // straight to the skill frame (design D11).
    expect(store.focusItemByKey("skills")).toBe(true);
    expect(store.focusConfirm("keyboard")).toBe(true);
    expect(store.focusItemByKey("skill-cat-0")).toBe(true);
    expect(store.focusConfirm("keyboard")).toBe(true);
    expect(store.router.currentMenu().items.map((i) => i.key)).toEqual(SIX_SKILL_KEYS);
    // Digit 6 picks the sixth skill row and opens its frame exactly as Enter
    // would — a local navigation cell, so no OOB action is dispatched.
    expect(store.focusPress("6")).toBe(true);
    expect(store.router.currentDescriptor()).toEqual({
      source: "combat.skill",
      params: { skillKey: "t_six" },
    });
    expect(sender.sent.actions).toHaveLength(0);
  });

  // webclient-dialogue-choices-overlay: the caption retarget is deleted.
  // In dialogue the keyboard router claims only `/`; the dialogue choice list
  // handles its own digits before they reach the bridge, so a digit that
  // does reach the store is unclaimed and the hidden dock never moves.
  it("a dialogue-mode digit is unclaimed and the collapsed dock never moves", () => {
    openSession();
    const choices = ["fare", "smell", "chest", "silence"].map(
      (keyword_id) => ({ keyword_id, label: `「${keyword_id}」` }),
    );
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 4,
          mode: "dialogue",
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            local_map: fx.localMapPanel(),
            dialogue: {
              schema_version: 2,
              available: true,
              kind: "dialogue",
              host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
              bond_stage: "親睦",
              line: "「渡河要五枚銅板。」",
              choices,
            },
          },
        }),
      ],
      {},
    );
    expect(store.view.mode).toBe("dialogue");
    const focusBefore = store.view.focus.key;
    expect(store.focusPress("4")).toBe(false);
    expect(store.focusPress("5")).toBe(false);
    expect(store.focusPress("1", true)).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.focus.key).toBe(focusBefore);
  });

  it("an unconsumed digit before any frame is mounted is unclaimed", () => {
    // Pre-session: no snapshot received, so the router stack is empty and a
    // digit press must stay total (false, no throw, no submit).
    expect(store.focusPress("1")).toBe(false);
    expect(store.focusPress("9")).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("held digit repeats are suppressed like held Enter, even after the lock releases", () => {
    openSession();
    openOverview();
    expect(store.focusPress("2")).toBe(true);
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
    expect(store.focusPress("2", true)).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    // The digit binding itself still works for a fresh press after the
    // suppression (the row re-submits once the lock is clear).
    expect(store.focusPress("2", false)).toBe(true);
    expect(sender.sent.actions).toHaveLength(2);
  });
});
