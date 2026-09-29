// webclient-combat-command-window: the store side of the vertical combat
// command window — basic attack's initial focus on an eligible foe (focus
// only, never a submission) and the focused-skill detail following the
// CURRENT frame, so a backed-out category never shows a stale skill.

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";
import CombatMenu from "../../lib/combat_menu.js";

const ATTACK = CombatMenu.BASIC_ATTACK_KEY;
const FOE = 7;
const ALLY = 8;

// One category with a single sub-group (the skill frame opens directly):
// basic attack plus a second single-target skill.
function skills(attackTargets) {
  const skill = (key, label, targets) => ({
    key,
    label,
    description: `${label}的合成描述。`,
    cost: key === ATTACK ? {} : { mp: 6 },
    target_spec: "single",
    element: null,
    enabled: true,
    disabled_reason: null,
    targets,
    shorthands: [],
  });
  return [
    {
      category: "martial_arts",
      label: "武技",
      groups: [
        {
          group: null,
          label: null,
          skills: [skill(ATTACK, "普通攻擊", attackTargets), skill("heavy_slash", "重斬", [FOE])],
        },
      ],
    },
  ];
}

describe("combat command window (store)", () => {
  let store;
  let sender;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  // The presenter order lists the ally first, so an opposing candidate is
  // never simply the first row.
  const PARTICIPANTS = [
    { identity: ALLY, token: "a1", display_name: "同行劍士", team: "party", state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null },
    { identity: FOE, token: "e1", display_name: "灰袍盜賊", team: "foes", state: "active", hp_current: 80, hp_maximum: 100, portrait_ref: null },
  ];

  function enterCombat(attackTargets) {
    store.beginTransport(1);
    store.setConnected(true);
    const snapshot = fx.snapshot({
      mode: "combat",
      panels: {
        status: fx.statusPanel(),
        context_actions: fx.combatActions({ skills: skills(attackTargets), participants: PARTICIPANTS }),
        local_map: fx.localMapPanel(),
      },
    });
    const result = store.receive(1, "ui_snapshot", [snapshot], {});
    expect(result, JSON.stringify(result)).toMatchObject({ accepted: true });
    expect(store.view.focus.key).toBe("attack");
  }

  it("opens basic attack on the listed foe behind an ally, keeping the order and sending nothing", () => {
    enterCombat([ALLY, FOE]);
    expect(store.focusPress("Enter")).toBe(true);
    expect(store.router.currentDescriptor()).toEqual({ source: "combat.skill", params: { skillKey: ATTACK } });
    expect(store.view.combatMenu.items.map((item) => item.key)).toEqual([`target-${ALLY}`, `target-${FOE}`]);
    expect(store.view.focus.key).toBe(`target-${FOE}`);
    expect(sender.sent.actions).toHaveLength(0);
    // The ally stays reachable and selectable by an explicit move.
    expect(store.focusPress("ArrowRight")).toBe(false);
    expect(store.focusPress("ArrowUp")).toBe(true);
    expect(store.view.focus.key).toBe(`target-${ALLY}`);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("confirming the initial focus casts at the foe exactly once", () => {
    enterCombat([ALLY, FOE]);
    store.focusPress("Enter");
    expect(store.focusPress("Enter")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].action_id).toBe("combat.cast");
    expect(sender.sent.actions[0].payload).toEqual({ skill_key: ATTACK, target_ids: [FOE] });
  });

  it("falls back to the first candidate when no opposing candidate is listed", () => {
    enterCombat([ALLY]);
    store.focusPress("Enter");
    expect(store.view.focus.key).toBe(`target-${ALLY}`);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("shows the category, not the previously opened skill, after backing out", () => {
    enterCombat([FOE]);
    expect(store.view.focusedSkill).toBeNull();
    // 技能 → the category list → 武技's skill frame (one sub-group).
    store.focusPress("ArrowDown");
    expect(store.view.focus.key).toBe("skills");
    store.focusPress("Enter");
    expect(store.router.currentDescriptor().source).toBe("combat.categories");
    expect(store.view.focusedSkill).toBeNull();
    store.focusPress("Enter");
    store.focusPress("ArrowDown");
    expect(store.view.focus.key).toBe("heavy_slash");
    expect(store.view.focusedSkill.key).toBe("heavy_slash");
    // Open the skill's target frame: the detail stays on that skill.
    store.focusPress("Enter");
    expect(store.router.currentDescriptor().source).toBe("combat.skill");
    expect(store.view.focusedSkill.key).toBe("heavy_slash");
    // Back out twice to the category list: no skill detail survives.
    store.focusPress("Escape");
    store.focusPress("Escape");
    expect(store.router.currentDescriptor().source).toBe("combat.categories");
    expect(store.view.focus.key).toBe("skill-cat-0");
    expect(store.view.focusedSkill).toBeNull();
    store.focusPress("Escape");
    expect(store.view.focus.key).toBe("skills");
    expect(store.view.focusedSkill).toBeNull();
    expect(sender.sent.actions).toHaveLength(0);
  });
});
