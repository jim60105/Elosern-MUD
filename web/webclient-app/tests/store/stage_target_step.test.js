// webclient-combat-stage-target-picking: the store side of the stage target
// step — the pure step model (positions per TargetSpec in stage order, the
// lit sets, the digits, the announcements), the arrow-key claim that walks
// the positions through the router's own focus-by-key, the pointer entry,
// and the step's absence outside the target frames of enabled SINGLE / SELF
// / AREA skills and while a round plays. Every payload is compared with the
// one the card's row produced for the same choice (focus + confirm through
// the router), so a byte drift in the step is caught.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

// The beat pause reads one DOM token; the stub keeps a playing round playing
// until the case skips it.
vi.mock("../../lib/motion_tokens.js", () => ({ readMotionMs: vi.fn(() => 400) }));

import { useElosernStore } from "../../stores/elosern.js";
import { stageTargetModel, arrowTarget, fallbackFormationOrder } from "../../stores/elosern/stage_targets.js";
import CombatMenu from "../../lib/combat_menu.js";
import * as fx from "./protocol_fixtures.js";

const ATTACK = CombatMenu.BASIC_ATTACK_KEY;
// The controlled figure is the status fixture's actor ("42").
const PLAYER = 42;
const ALLY = 8;
const FOE_A = 11;
const FOE_B = 12;
const FOE_C = 13;
const FLED = 14;

function participant(identity, token, name, team, state = "active") {
  return {
    identity,
    token,
    display_name: name,
    team,
    state,
    hp_current: state === "active" ? 50 : 0,
    hp_maximum: 60,
    portrait_ref: String(identity),
    conditions: [],
  };
}

function roster({ allyState = "active", foeBState = "active", sameNames = false } = {}) {
  return [
    participant(PLAYER, "a1", "影行者", "party"),
    participant(ALLY, "a2", "同行劍士", "party", allyState),
    participant(FOE_A, "e1", sameNames ? "哥布林" : "灰袍盜賊", "foes"),
    participant(FOE_B, "e2", "哥布林", "foes", foeBState),
    participant(FOE_C, "e3", "史萊姆", "foes"),
    participant(FLED, "e4", "逃兵", "foes", "fled"),
  ];
}

function skill(key, label, spec, targets, extra = {}) {
  return {
    key,
    label,
    description: `${label}的合成描述。`,
    cost: key === ATTACK ? {} : { mp: 5 },
    target_spec: spec,
    element: null,
    enabled: true,
    disabled_reason: null,
    targets,
    shorthands: [],
    hostile: false,
    beneficial: false,
    ...extra,
  };
}

// One category with one sub-group, so the category opens the skill frame.
function skills({ attackTargets = [ALLY, FOE_A, FOE_B, FOE_C] } = {}) {
  return [
    {
      category: "martial_arts",
      label: "武技",
      groups: [
        {
          group: null,
          label: null,
          skills: [
            skill(ATTACK, "普通攻擊", "single", attackTargets),
            skill("t_mend", "急救", "single", [ALLY, FOE_B]),
            skill("t_call", "呼喚", "single", [FOE_A, FLED]),
            skill("t_guard", "守勢", "self", []),
            skill("t_storm", "風暴", "area", [ALLY, FOE_A, FOE_B, FOE_C], {
              shorthands: ["all-enemies", "all-allies", "all"],
            }),
            skill("t_nova", "新星", "none", []),
            skill("t_locked", "封印", "single", [FOE_A], {
              enabled: false,
              disabled_reason: { code: "insufficient_mp", message: "魔力不足。" },
            }),
            skill("t_empty", "空擊", "single", []),
            skill("t_bolt", "雷矢", "single", [FOE_A, FOE_B], {
              cost: { mp: 8 },
              freeform_scales: [
                { scale: 0.25, label: "1/4", mp_cost: 2 },
                { scale: 0.5, label: "1/2", mp_cost: 4 },
                { scale: 1, label: "1", mp_cost: 8 },
                { scale: 2, label: "2", mp_cost: 16 },
                { scale: 4, label: "4", mp_cost: 32 },
              ],
            }),
            skill("t_rally_all", "總動員", "area", [FOE_A, FLED], { shorthands: ["all-enemies"] }),
          ],
        },
      ],
    },
  ];
}

// The formation draws the ally left of the player, then the foes with the
// front foe (first in presenter order) rightmost.
const STAGE_ORDER = [ALLY, PLAYER, FOE_C, FOE_B, FOE_A];

describe("stage target step (store)", () => {
  let store;
  let sender;

  beforeEach(() => {
    window.localStorage.clear();
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function panels(options = {}) {
    return {
      status: fx.statusPanel(),
      context_actions: fx.combatActions({
        skills: skills(options),
        participants: options.participants || roster(options),
      }),
      local_map: fx.localMapPanel(),
    };
  }

  let revision = 1;
  function enterCombat(options = {}) {
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    const result = store.receive(1, "ui_snapshot", [fx.snapshot({ mode: "combat", panels: panels(options) })], {});
    expect(result, JSON.stringify(result)).toMatchObject({ accepted: true });
    store.setStageFormation(STAGE_ORDER);
  }

  function replacePanels(options) {
    revision += 1;
    const result = store.receive(1, "ui_update", [fx.update({ revision, mode: "combat", panels: panels(options) })], {});
    expect(result.accepted).toBe(true);
  }

  function openAttack() {
    store.focusItemByKey("attack");
    store.focusPress("Enter");
  }

  function openSkill(key) {
    store.focusItemByKey("skills");
    store.focusPress("Enter");
    store.focusItemByKey("skill-cat-0");
    store.focusPress("Enter");
    store.focusItemByKey(key);
    store.focusPress("Enter");
  }

  const step = () => store.view.stageTarget;
  const keys = () => step().positions.map((p) => p.key);
  const focus = () => store.view.focus.key;

  // The payload the card's row sends for the same item, in a separate
  // client: focus the row through the router and confirm (the row path).
  function rowPayload(open, key) {
    const mainStore = store;
    const mainSender = sender;
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    enterCombat();
    open();
    store.focusItemByKey(key);
    store.focusConfirm("keyboard");
    const payload = sender.sent.actions.at(-1).payload;
    store = mainStore;
    sender = mainSender;
    return payload;
  }

  it("lays SINGLE candidates out in stage order and walks them with wrapping arrows", () => {
    enterCombat();
    openAttack();
    expect(store.view.combatMenu.items.map((i) => i.key)).toEqual([
      `target-${ALLY}`, `target-${FOE_A}`, `target-${FOE_B}`, `target-${FOE_C}`,
    ]);
    const s = step();
    expect(s.form).toBe("single");
    // Server order is untouched; positions follow the stage left to right.
    expect(keys()).toEqual([`target-${ALLY}`, `target-${FOE_C}`, `target-${FOE_B}`, `target-${FOE_A}`]);
    // Attack opens on the first foe the server listed, exactly as before.
    expect(focus()).toBe(`target-${FOE_A}`);
    expect(s.lit).toEqual([String(FOE_A)]);
    expect(s.selectable.sort()).toEqual([ALLY, FOE_A, FOE_B, FOE_C].map(String).sort());
    // The digits stay the server's order.
    expect(s.digits).toEqual({ [ALLY]: 1, [FOE_A]: 2, [FOE_B]: 3, [FOE_C]: 4 });
    expect(store.focusPress("ArrowRight")).toBe(true);
    expect(focus()).toBe(`target-${ALLY}`); // wrapped from the last position
    expect(store.focusPress("ArrowDown")).toBe(true);
    expect(focus()).toBe(`target-${FOE_C}`);
    expect(store.focusPress("ArrowLeft")).toBe(true);
    expect(focus()).toBe(`target-${ALLY}`);
    expect(store.focusPress("ArrowUp")).toBe(true);
    expect(focus()).toBe(`target-${FOE_A}`); // wrapped from the first position
    expect(step().lit).toEqual([String(FOE_A)]);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("Enter on a SINGLE position casts once, byte-identical to the card row", () => {
    const expected = rowPayload(openAttack, `target-${FOE_B}`);
    const before = sender.sent.actions.length;
    enterCombat();
    openAttack();
    store.focusPress("ArrowLeft"); // FOE_A → FOE_B
    expect(focus()).toBe(`target-${FOE_B}`);
    expect(store.focusPress("Enter")).toBe(true);
    expect(sender.sent.actions).toHaveLength(before + 1);
    expect(sender.sent.actions.at(-1).action_id).toBe("combat.command");
    expect(JSON.stringify(sender.sent.actions.at(-1).payload)).toBe(JSON.stringify(expected));
    expect(expected).toEqual({ skill_key: ATTACK, target_ids: [FOE_B] });
  });

  it("the pointer entry focuses on hover and casts once on activation", () => {
    enterCombat();
    openAttack();
    expect(store.stageTargetPointer(`target-${FOE_C}`, "hover")).toBe(true);
    expect(focus()).toBe(`target-${FOE_C}`);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.stageTargetPointer("attack", "activate")).toBe(false);
    expect(store.stageTargetPointer(`target-${FOE_C}`, "activate")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].payload).toEqual({ skill_key: ATTACK, target_ids: [FOE_C] });
  });

  it("a digit still picks the server's N-th item", () => {
    enterCombat();
    openAttack();
    expect(store.focusPress("1")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].payload).toEqual({ skill_key: ATTACK, target_ids: [ALLY] });
  });

  it("SELF is one position on the controlled figure; arrows keep it; no target field", () => {
    enterCombat();
    openSkill("t_guard");
    const s = step();
    expect(s.form).toBe("self");
    expect(keys()).toEqual(["self-confirm"]);
    expect(s.positions[0].identities).toEqual([String(PLAYER)]);
    expect(s.selectable).toEqual([String(PLAYER)]);
    expect(s.announce).toBe("目標：自己");
    for (const key of ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"]) {
      expect(store.focusPress(key)).toBe(true);
      expect(focus()).toBe("self-confirm");
    }
    expect(s.lit).toEqual([String(PLAYER)]);
    store.focusPress("Enter");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].payload).toEqual({ skill_key: "t_guard" });
  });

  it("AREA: members, then groups, then confirm; Space toggles; groups light their side", () => {
    enterCombat();
    openSkill("t_storm");
    expect(keys()).toEqual([
      `area-${ALLY}`, `area-${FOE_C}`, `area-${FOE_B}`, `area-${FOE_A}`,
      "shorthand-all-enemies", "shorthand-all-allies", "shorthand-all", "area-confirm",
    ]);
    store.focusItemByKey(`area-${FOE_C}`);
    store.focusPress(" ");
    store.focusPress("ArrowRight");
    store.focusPress("Enter"); // Enter toggles a member too
    expect(step().selectedIds).toEqual([String(FOE_C), String(FOE_B)]);
    expect(step().announce).toBe("目標：哥布林，敵方，已選");
    // Confirm lights exactly the selection.
    store.focusItemByKey("area-confirm");
    expect(step().lit).toEqual([String(FOE_C), String(FOE_B)]);
    expect(step().announce).toBe("施展：已選 2 名");
    // Groups light every candidate of their side; focus moves between groups.
    store.focusItemByKey("shorthand-all-enemies");
    expect(step().lit).toEqual([FOE_A, FOE_B, FOE_C].map(String));
    expect(step().announce).toBe("目標：全體敵人，共 3 名");
    store.focusPress("ArrowRight");
    expect(focus()).toBe("shorthand-all-allies");
    expect(step().lit).toEqual([String(ALLY)]);
    expect(step().announce).toBe("目標：全體我方，共 1 名");
    store.focusPress("ArrowRight");
    expect(step().lit).toEqual([ALLY, FOE_A, FOE_B, FOE_C].map(String));
    // Enter on all-allies chooses it and clears the explicit selection.
    store.focusItemByKey("shorthand-all-allies");
    store.focusPress("Enter");
    expect(step().selectedIds).toEqual([]);
    store.focusItemByKey("area-confirm");
    expect(step().lit).toEqual([String(ALLY)]);
    expect(step().announce).toBe("施展：全體我方，共 1 名");
    store.focusPress("Enter");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].payload).toEqual({ skill_key: "t_storm", target_shorthand: "all-allies" });
  });

  it("AREA explicit confirm sends presenter order; nothing chosen announces so", () => {
    enterCombat();
    openSkill("t_storm");
    store.focusItemByKey("area-confirm");
    expect(step().announce).toBe("施展：尚未選擇目標");
    expect(step().lit).toEqual([]);
    store.focusItemByKey(`area-${FOE_C}`);
    store.focusPress(" ");
    store.focusItemByKey(`area-${FOE_A}`);
    store.focusPress(" ");
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(sender.sent.actions[0].payload).toEqual({ skill_key: "t_storm", target_ids: [FOE_A, FOE_C] });
  });

  it("NONE, a disabled skill, a zero-candidate frame and the scale-free lists start no step", () => {
    enterCombat();
    expect(step()).toBeNull(); // the root
    expect(store.focusPress("ArrowDown")).toBe(true);
    expect(focus()).toBe("skills"); // the root's arrows reach the router
    for (const key of ["t_nova", "t_empty"]) {
      store.resetFramesToRoot();
      openSkill(key);
      expect(store.router.currentDescriptor().params.skillKey).toBe(key);
      expect(step(), key).toBeNull();
      // The router keeps its own (vertical) arrows in the frame.
      expect(store.focusPress("ArrowRight"), key).toBe(false);
    }
    // A disabled skill's frame is its one explanation row: no step.
    const disabled = CombatMenu.openSkill(
      CombatMenu.buildMenus(fx.combatActions({ skills: skills(), participants: roster() })),
      "t_locked",
    );
    expect(disabled.items.map((i) => i.key)).toEqual(["skill-disabled"]);
    expect(stageTargetModel({
      source: "combat.skill", menu: disabled,
      skill: { key: "t_locked", enabled: false, targetSpec: "single", targets: [FOE_A] },
      participants: roster(), formationOrder: STAGE_ORDER, controlledIdentity: "42",
      focusKey: "skill-disabled", locked: false,
    })).toBeNull();
  });

  it("a knocked-out candidate is a position; an unlisted fallen foe is none", () => {
    enterCombat({ allyState: "knocked_out", foeBState: "knocked_out" });
    openSkill("t_mend");
    expect(keys()).toEqual([`target-${ALLY}`, `target-${FOE_B}`]);
    expect(step().selectable.sort()).toEqual([String(ALLY), String(FOE_B)].sort());
  });

  it("a listed fled participant is the only off-stage position: named 場外, lights nothing", () => {
    enterCombat();
    openSkill("t_call");
    expect(keys()).toEqual([`target-${FOE_A}`, `target-${FLED}`]);
    expect(step().positions.map((p) => p.offStage)).toEqual([false, true]);
    store.focusItemByKey(`target-${FLED}`);
    expect(step().lit).toEqual([]);
    expect(step().announce).toBe("目標：逃兵，敵方，場外");
  });

  it("announces an ally by side and repeats a duplicate name with its token", () => {
    enterCombat({ sameNames: true });
    openAttack();
    expect(step().announce).toBe("目標：哥布林（e1），敵方");
    store.focusItemByKey(`target-${ALLY}`);
    expect(step().announce).toBe("目標：同行劍士，我方");
  });

  it("a panel replacement that removes the focused candidate repairs focus and the lit set", () => {
    enterCombat();
    openAttack();
    expect(focus()).toBe(`target-${FOE_A}`);
    replacePanels({ attackTargets: [ALLY, FOE_B, FOE_C] });
    expect(keys()).not.toContain(`target-${FOE_A}`);
    expect(keys()).toContain(focus());
    expect(step().lit).toEqual(step().positions.find((p) => p.key === focus()).identities);
    replacePanels({ attackTargets: [ALLY, FOE_A, FOE_B, FOE_C] });
    expect(keys()).toEqual([`target-${ALLY}`, `target-${FOE_C}`, `target-${FOE_B}`, `target-${FOE_A}`]);
  });

  it("a master's 威力 step is no step; its target frame is, naming the chosen 威力", () => {
    enterCombat();
    openSkill("t_bolt");
    expect(store.router.currentDescriptor().source).toBe("combat.skill");
    expect(step()).toBeNull(); // the scale chips keep the router's arrows
    store.focusItemByKey("scale-2");
    store.focusPress("Enter");
    expect(store.router.currentDescriptor().source).toBe("combat.target");
    expect(step().form).toBe("single");
    expect(step().scaleLabel).toBe("威力 ×2");
    expect(keys()).toEqual([`target-${FOE_B}`, `target-${FOE_A}`]);
    store.focusPress("Enter");
    expect(sender.sent.actions.at(-1).payload).toMatchObject({ skill_key: "t_bolt", scale: 2 });
  });

  it("a group counts and lights only the candidates standing on the stage", () => {
    enterCombat();
    openSkill("t_rally_all");
    store.focusItemByKey("shorthand-all-enemies");
    expect(step().lit).toEqual([String(FOE_A)]);
    expect(step().announce).toBe("目標：全體敵人，共 1 名");
  });

  it("an arrow from a focus that is no position goes to the first or last position", () => {
    const model = stageTargetModel({
      source: "combat.target",
      menu: { items: [{ key: `target-${FOE_A}`, payload: { target_ids: [FOE_A] } }, { key: `target-${FOE_B}`, payload: { target_ids: [FOE_B] } }] },
      skill: { key: "t_x", enabled: true, targetSpec: "single", targets: [FOE_A, FOE_B] },
      participants: roster(),
      formationOrder: STAGE_ORDER,
      controlledIdentity: "42",
      focusKey: "back",
      locked: false,
    });
    expect(model.focusKey).toBeNull();
    expect(model.lit).toEqual([]);
    expect(arrowTarget(model, "ArrowRight")).toBe(`target-${FOE_B}`);
    expect(arrowTarget(model, "ArrowDown")).toBe(`target-${FOE_B}`);
    expect(arrowTarget(model, "ArrowLeft")).toBe(`target-${FOE_A}`);
    expect(arrowTarget(model, "ArrowUp")).toBe(`target-${FOE_A}`);
    // A lock (a playing round) or a non-target frame is no step.
    expect(stageTargetModel({ ...model, locked: true })).toBeNull();
    expect(fallbackFormationOrder(roster())).toEqual([PLAYER, ALLY, FOE_A, FOE_B, FOE_C].map(String));
  });

  it("a playing round suspends the step and releases the arrows; it resumes after", () => {
    vi.useFakeTimers();
    enterCombat();
    openAttack();
    const requestId = store.dispatchAction("combat.command", { skill_key: ATTACK, target_ids: [FOE_A] });
    store.appendText("out", "你擲出了骰子。");
    revision += 1;
    store.receive(1, "ui_update", [fx.update({
      revision,
      mode: "combat",
      panels: {
        ...panels(),
        combat_beats: {
          schema_version: 1, available: true, round: "s-1/1",
          beats: [{ seq: 0, action: 0, kind: "roll", actor: String(PLAYER), target: String(FOE_A), amount: null, hp_after: null, text: "你擲出了骰子。" }],
        },
      },
    })], {});
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: requestId, presentation_revision: revision })], {});
    expect(store.view.dispatch.beatLocked).toBe(true);
    expect(step()).toBeNull();
    const before = focus();
    expect(store.focusPress("ArrowRight")).toBe(false); // unclaimed: the router's no-op
    expect(focus()).toBe(before);
    // The pointer is inert too: the figures' entry finds no step.
    expect(store.stageTargetPointer(`target-${FOE_B}`, "activate")).toBe(false);
    store.skipBeats();
    expect(store.view.dispatch.beatLocked).toBe(false);
    // The frame is still current when the round ends: the step resumes.
    expect(store.router.currentDescriptor().source).toBe("combat.skill");
    expect(step()).not.toBeNull();
    expect(step().focusKey).toBe(focus());
  });
});
