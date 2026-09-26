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
          })),
        },
      ],
    },
  ];
}

// The nine-chip overview: three exits, two person chips, one object chip, and
// the three footer chips (查看房間 · 等待／休息 · 建議), in reading order.
const NINE_CHIP_OVERRIDES = {
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

const NINE_CHIP_KEYS = [
  "exit-east",
  "exit-north",
  "exit-west",
  "target-7",
  "target-8",
  "object-3",
  "look-room",
  "wait",
  "suggestions",
];

const SIX_CHIP_KEYS = [
  "exit-east",
  "exit-north",
  "target-7",
  "object-3",
  "look-room",
  "wait",
];

describe("dock digit row picks (1–9)", () => {
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
    // The popover renders exactly two rows (查看 and 返回上一層), so `3`–`9`
    // are unclaimed.
    for (const digit of ["3", "4", "5", "6", "7", "8", "9"]) {
      expect(store.focusPress(digit), digit).toBe(false);
    }
    // An untouched digit does not consume the key: focus stays where it was.
    expect(store.view.focus.key).toBe("look-target");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("the digit slots follow the rendered rows: the popover's back row takes a slot", () => {
    openSession();
    openLookOnlyPopover();
    // The popover's `back` row is a rendered row of its listbox, so `2`
    // addresses it and pops exactly one level with no dispatch.
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

  it("digits 5–9 pick the overview's later chips in reading order", () => {
    openSession();
    // The default envelope is `generating`, so the footer carries the 建議
    // chip and the overview holds exactly nine chips.
    openOverview(NINE_CHIP_OVERRIDES, fx.explorationActions());
    expect(store.router.currentMenu().items.map((i) => i.key)).toEqual(NINE_CHIP_KEYS);

    // 5 -> the second person chip: its verb popover opens, nothing submits.
    expect(store.focusPress("5")).toBe(true);
    expect(store.view.dockSource).toBe("exploration.target");
    expect(store.view.dockDepth).toBe(2);
    // The popover is scoped to the chip's own target.
    expect(store.view.combatMenu.target.identity).toBe(8);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.focusEscape()).toBe(true);
    expect(store.view.dockDepth).toBe(1);

    // 9 -> the ninth chip is the footer's 建議 chip: it pushes the suggestions
    // frame through the ordinary confirmation path.
    expect(store.focusPress("9")).toBe(true);
    expect(store.view.dockSource).toBe("exploration.suggestions");
    expect(store.view.dockDepth).toBe(2);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.focusEscape()).toBe(true);

    // 6 -> the object chip submits its explore.look once.
    expect(store.focusPress("6")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.look",
      payload: { target_id: 3 },
    });
  });

  it("digit 9 on a six-chip overview is unclaimed", () => {
    openSession();
    openOverview(undefined, fx.explorationActions({ suggestions: { status: "unavailable" } }));
    expect(store.router.currentMenu().items.map((i) => i.key)).toEqual(SIX_CHIP_KEYS);
    // No ninth chip: the press is unclaimed and nothing submits.
    expect(store.focusPress("9")).toBe(false);
    expect(store.view.dockDepth).toBe(1);
    expect(sender.sent.actions).toHaveLength(0);
    // The sixth chip is real: 等待／休息 pushes the waiting frame.
    expect(store.focusPress("6")).toBe(true);
    expect(store.view.dockSource).toBe("exploration.wait");
    expect(sender.sent.actions).toHaveLength(0);
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

  it("the caption's picks claim the slots while the dialogue variant presents", () => {
    openSession();
    // The caption panel's own bound is four picks (`DIALOGUE_MAX_CHOICES`,
    // webclient-align-11), so the caption range is 1–4.
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
              schema_version: 1,
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
    expect(store.focusPress("4")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.talk_scripted",
      payload: { npc_id: 41, keyword_id: "silence" },
    });
    // A digit past the rendered picks has no pick: the caption branch owns the
    // press and declines, so it falls through.
    expect(store.focusPress("5")).toBe(false);
    // The dock's own chips claim no digit while the caption presents.
    expect(store.view.dockDepth).toBe(1);
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
