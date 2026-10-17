// webclient-combat-cross-side-confirm: the cross-side predicate over fixed
// inputs (the target set of each form, the four question wordings, the
// fail-closed unresolvable target) and the store flow — a cast across sides
// is held behind the question card, 是 sends the held payload once, 否
// returns to the target step, the keys and the pointer behind the question
// do nothing, and a change under the question cancels it.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("../../lib/motion_tokens.js", () => ({ readMotionMs: vi.fn(() => 400) }));

import { useElosernStore } from "../../stores/elosern.js";
import { crossSide, crossSideQuestion, skillFacts, targetSetFor } from "../../stores/elosern/cross_side.js";
import CombatMenu from "../../lib/combat_menu.js";
import * as fx from "./protocol_fixtures.js";

const ATTACK = CombatMenu.BASIC_ATTACK_KEY;
// The status fixture's actor is "42".
const PLAYER = 42;
const ALLY = 8;
const FOE_A = 11;
const FOE_B = 12;
const GHOST = 99; // a candidate no participant row carries

function participant(identity, token, name, team) {
  return {
    identity,
    token,
    display_name: name,
    team,
    state: "active",
    hp_current: 50,
    hp_maximum: 60,
    portrait_ref: String(identity),
    conditions: [],
  };
}

const ROSTER = [
  participant(PLAYER, "a1", "影行者", "party"),
  participant(ALLY, "a2", "同行劍士", "party"),
  participant(FOE_A, "e1", "灰袍盜賊", "foes"),
  participant(FOE_B, "e2", "盜賊頭目", "foes"),
];

const HARM = { hostile: true, beneficial: false };
const HELP = { hostile: false, beneficial: true };
const BOTH = { hostile: true, beneficial: true };
const NEITHER = { hostile: false, beneficial: false };

function skill(key, label, spec, targets, facts, extra = {}) {
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
    ...facts,
    ...extra,
  };
}

const EVERYONE = [PLAYER, ALLY, FOE_A, FOE_B];
const AREA_SHORTHANDS = { shorthands: ["all-enemies", "all-allies", "all"] };

function skills({ attackTargets = [ALLY, FOE_A, FOE_B], disableAttack = false, stormTargets = [ALLY, FOE_A, FOE_B] } = {}) {
  return [
    {
      category: "martial_arts",
      label: "武技",
      groups: [
        {
          group: null,
          label: null,
          skills: [
            skill(ATTACK, "基本攻擊", "single", attackTargets, HARM, disableAttack
              ? { enabled: false, disabled_reason: { code: "unavailable", message: "暫時無法使用。" } }
              : {}),
            skill("x_heal", "治癒術", "single", EVERYONE, HELP),
            skill("x_ward", "守護祝福", "single", EVERYONE, HELP),
            skill("x_drain", "汲取", "single", EVERYONE, HARM),
            skill("x_curse", "自縛", "self", [], HARM),
            skill("x_rally", "鼓舞", "self", [], HELP),
            skill("x_storm", "雷暴", "area", stormTargets, HARM, AREA_SHORTHANDS),
            skill("x_bloom", "群體治癒", "area", [PLAYER, ALLY, FOE_A], HELP, AREA_SHORTHANDS),
            skill("x_tide", "潮汐逆轉", "area", [ALLY, FOE_A], BOTH, AREA_SHORTHANDS),
            skill("x_push", "推移", "single", [FOE_A], NEITHER),
            skill("x_nova", "新星", "none", [], HARM),
          ],
        },
      ],
    },
  ];
}

describe("cross-side predicate (pure)", () => {
  const actor = String(PLAYER);
  const ask = (facts, form, payload, candidates = EVERYONE) =>
    crossSide(facts, targetSetFor({ form, payload, candidates, participants: ROSTER, actorIdentity: actor }), ROSTER, actor);

  it("builds the target set of each form", () => {
    const base = { candidates: [ALLY, FOE_A, FOE_B, GHOST], participants: ROSTER, actorIdentity: actor };
    expect(targetSetFor({ ...base, form: "single", payload: { target_ids: [FOE_A] } })).toEqual(["11"]);
    expect(targetSetFor({ ...base, form: "self", payload: {} })).toEqual(["42"]);
    expect(targetSetFor({ ...base, form: "area", payload: { target_ids: [ALLY, FOE_B] } })).toEqual(["8", "12"]);
    expect(targetSetFor({ ...base, form: "area", payload: { target_shorthand: "all-enemies" } })).toEqual(["11", "12"]);
    expect(targetSetFor({ ...base, form: "area", payload: { target_shorthand: "all-allies" } })).toEqual(["8"]);
    expect(targetSetFor({ ...base, form: "area", payload: { target_shorthand: "all" } })).toEqual(["8", "11", "12", "99"]);
    expect(targetSetFor({ ...base, form: "none", payload: {} })).toEqual([]);
  });

  it("a hostile skill asks on the party side", () => {
    expect(ask(HARM, "single", { target_ids: [ALLY] })).toEqual({ sides: "ally" });
    expect(ask(HARM, "single", { target_ids: [PLAYER] })).toEqual({ sides: "self" });
    expect(ask(HARM, "self", {})).toEqual({ sides: "self" });
    expect(ask(HARM, "single", { target_ids: [FOE_A] })).toBeNull();
    expect(ask(HARM, "area", { target_ids: [ALLY, FOE_A] })).toEqual({ sides: "ally" });
    expect(ask(HARM, "area", { target_ids: [PLAYER, FOE_A] })).toEqual({ sides: "self" });
    expect(ask(HARM, "area", { target_shorthand: "all" }, [ALLY, FOE_A])).toEqual({ sides: "ally" });
    expect(ask(HARM, "area", { target_shorthand: "all-enemies" }, [ALLY, FOE_A, FOE_B])).toBeNull();
  });

  it("a beneficial skill (heal or buff) asks on the foe side", () => {
    expect(ask(HELP, "single", { target_ids: [FOE_B] })).toEqual({ sides: "foe" });
    expect(ask(HELP, "single", { target_ids: [ALLY] })).toBeNull();
    expect(ask(HELP, "self", {})).toBeNull();
    expect(ask(HELP, "area", { target_shorthand: "all-allies" }, [PLAYER, ALLY, FOE_A])).toBeNull();
    expect(ask(HELP, "area", { target_shorthand: "all" }, [ALLY, FOE_A])).toEqual({ sides: "foe" });
  });

  it("a skill with both facts applies each to its side", () => {
    expect(ask(BOTH, "single", { target_ids: [FOE_A] })).toEqual({ sides: "foe" });
    expect(ask(BOTH, "single", { target_ids: [ALLY] })).toEqual({ sides: "ally" });
    expect(ask(BOTH, "single", { target_ids: [PLAYER] })).toEqual({ sides: "self" });
    expect(ask(BOTH, "area", { target_shorthand: "all" }, [ALLY, FOE_A])).toEqual({ sides: "both" });
  });

  it("neither fact and NONE never ask", () => {
    expect(ask(NEITHER, "single", { target_ids: [ALLY] })).toBeNull();
    expect(ask(NEITHER, "area", { target_shorthand: "all" })).toBeNull();
    expect(ask(HARM, "none", {})).toBeNull();
  });

  it("an unresolvable identity fails closed with the both-sides wording", () => {
    expect(ask(HARM, "single", { target_ids: [GHOST] })).toEqual({ sides: "both" });
    expect(ask(HELP, "single", { target_ids: [GHOST] })).toEqual({ sides: "both" });
    expect(ask(HARM, "area", { target_ids: [FOE_A, GHOST] })).toEqual({ sides: "both" });
    expect(ask(HELP, "area", { target_shorthand: "all" }, [ALLY, GHOST])).toEqual({ sides: "both" });
    expect(ask(NEITHER, "single", { target_ids: [GHOST] })).toBeNull();
    // An unknown actor on a SELF skill is unresolvable too.
    expect(crossSide(HARM, targetSetFor({ form: "self", payload: {}, actorIdentity: null }), ROSTER, null)).toEqual({ sides: "both" });
  });

  it("words the four questions exactly", () => {
    expect(crossSideQuestion("ally", "基本攻擊")).toBe("確定要對友方使用〈基本攻擊〉？");
    expect(crossSideQuestion("self", "汲取")).toBe("確定要對自己使用〈汲取〉？");
    expect(crossSideQuestion("foe", "治癒術")).toBe("確定要對敵方使用〈治癒術〉？");
    expect(crossSideQuestion("both", "潮汐逆轉")).toBe("確定要對友方與敵方使用〈潮汐逆轉〉？");
  });

  it("reads the facts from the committed descriptor", () => {
    const panel = { skills: skills() };
    expect(skillFacts(panel, ATTACK)).toMatchObject(HARM);
    expect(skillFacts(panel, "x_tide")).toMatchObject(BOTH);
    expect(skillFacts(panel, "missing")).toMatchObject(NEITHER);
  });
});

describe("cross-side question (store flow)", () => {
  let store;
  let sender;
  let revision = 1;
  let gen = 0;

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
    const participants = options.participants || ROSTER;
    const presented = new Set(participants.map((p) => p.identity));
    const list = skills(options);
    for (const entry of list[0].groups[0].skills) {
      entry.targets = entry.targets.filter((id) => presented.has(id));
    }
    return {
      status: fx.statusPanel(),
      context_actions: fx.combatActions({ skills: list, participants }),
      local_map: fx.localMapPanel(),
    };
  }

  // Each entry is a fresh client (a re-entry would retire the epoch).
  function enterCombat(options = {}) {
    if (gen > 0) {
      setActivePinia(createPinia());
      store = useElosernStore();
      sender = fx.createFakeSender();
      store.setSender(sender);
    }
    gen += 1;
    store.beginTransport(gen);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    const result = store.receive(gen, "ui_snapshot", [fx.snapshot({ mode: "combat", panels: panels(options) })], {});
    expect(result.accepted, JSON.stringify([result, store.lastPanelRejection])).toBe(true);
    store.setStageFormation([ALLY, PLAYER, FOE_B, FOE_A].map(String));
  }

  function replace(options, mode = "combat", extra = {}) {
    revision += 1;
    const body = mode === "combat" ? panels(options) : { context_actions: fx.explorationActions() };
    const result = store.receive(gen, "ui_update", [fx.update({ revision, mode, panels: { ...body, ...extra } })], {});
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

  const question = () => store.view.crossSideConfirm?.question ?? null;
  const focus = () => store.view.focus.key;
  const sent = () => sender.sent.actions;

  // The payload the same choice sends with no question: the held one is
  // re-sent verbatim, so the bytes must match the pre-question build.
  function heldPayload() {
    expect(sent()).toHaveLength(0);
    const request = store.confirmCrossSide();
    expect(request).toBeTruthy();
    expect(sent()).toHaveLength(1);
    return sent()[0];
  }

  it("Enter on an ally with Attack holds the cast; 是 sends it exactly once", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${ALLY}`);
    expect(store.focusPress("Enter")).toBe(true);
    expect(sent()).toHaveLength(0);
    expect(question()).toBe("確定要對友方使用〈基本攻擊〉？");
    expect(store.view.crossSideConfirm.sides).toBe("ally");
    // The step stays exactly as it was.
    expect(store.view.stageTarget.focusKey).toBe(`target-${ALLY}`);
    expect(store.view.stageTarget.lit).toEqual([String(ALLY)]);
    const focusRequests = store.view.dockFocusRequest;
    const envelope = heldPayload();
    expect(envelope.action_id).toBe("combat.cast");
    expect(JSON.stringify(envelope.payload)).toBe(JSON.stringify({ skill_key: ATTACK, target_ids: [ALLY] }));
    expect(question()).toBeNull();
    expect(store.view.dockFocusRequest).toBe(focusRequests + 1);
  });

  it("a digit and the pointer entry hold the cast the same way", () => {
    enterCombat();
    openAttack();
    expect(store.focusPress("1")).toBe(true); // server order: the ally first
    expect(sent()).toHaveLength(0);
    expect(question()).toBe("確定要對友方使用〈基本攻擊〉？");
    store.cancelCrossSide();
    expect(store.stageTargetPointer(`target-${ALLY}`, "activate")).toBe(true);
    expect(sent()).toHaveLength(0);
    expect(question()).toBe("確定要對友方使用〈基本攻擊〉？");
  });

  it("否 returns to the step with the same focus; Enter asks again", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${ALLY}`);
    store.focusPress("Enter");
    const focusRequests = store.view.dockFocusRequest;
    expect(store.cancelCrossSide()).toBe(true);
    expect(question()).toBeNull();
    expect(sent()).toHaveLength(0);
    expect(focus()).toBe(`target-${ALLY}`);
    expect(store.view.stageTarget.focusKey).toBe(`target-${ALLY}`);
    expect(store.view.dockFocusRequest).toBe(focusRequests + 1);
    // Nothing was sent, so the same row's Enter is not a suppressed repeat.
    store.focusPress("Enter");
    expect(question()).toBe("確定要對友方使用〈基本攻擊〉？");
    // One Escape that reaches the dock closes the question like 否; the next
    // pops the target frame as before.
    expect(store.focusPress("Escape")).toBe(true);
    expect(question()).toBeNull();
    expect(store.router.depth()).toBe(2);
    store.focusPress("Escape");
    expect(store.router.depth()).toBe(1);
    expect(sent()).toHaveLength(0);
  });

  it("no dock key or pointer acts behind the question", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${ALLY}`);
    store.focusPress("Enter");
    for (const key of ["Enter", " ", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "1", "2", "/"]) {
      expect(store.focusPress(key, false)).toBe(false);
    }
    expect(store.stageTargetPointer(`target-${FOE_A}`, "hover")).toBe(false);
    expect(store.stageTargetPointer(`target-${FOE_A}`, "activate")).toBe(false);
    expect(store.focusConfirm("pointer")).toBe(true); // the router's own confirm emits…
    expect(sent()).toHaveLength(0); // …but the held submit ignores it
    expect(focus()).toBe(`target-${ALLY}`);
    expect(question()).toBe("確定要對友方使用〈基本攻擊〉？");
  });

  it("a hostile SELF skill and a hostile SINGLE on the actor ask with 自己", () => {
    enterCombat();
    openSkill("x_curse");
    store.focusPress("Enter");
    expect(question()).toBe("確定要對自己使用〈自縛〉？");
    const envelope = heldPayload();
    expect(envelope.payload).toEqual({ skill_key: "x_curse" });
    enterCombat();
    openSkill("x_drain");
    store.focusItemByKey(`target-${PLAYER}`);
    store.focusPress("Enter");
    expect(question()).toBe("確定要對自己使用〈汲取〉？");
  });

  it("a heal and a buff on a foe ask with 敵方", () => {
    for (const [key, label] of [["x_heal", "治癒術"], ["x_ward", "守護祝福"]]) {
      enterCombat();
      openSkill(key);
      store.focusItemByKey(`target-${FOE_B}`);
      store.focusPress("Enter");
      expect(question()).toBe(`確定要對敵方使用〈${label}〉？`);
      store.cancelCrossSide();
    }
    expect(sent()).toHaveLength(0);
  });

  it("an AREA selection asks once if any member is cross-side; the selection survives 否", () => {
    enterCombat();
    openSkill("x_storm");
    for (const id of [ALLY, FOE_A]) {
      store.focusItemByKey(`area-${id}`);
      store.focusPress(" ");
    }
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(question()).toBe("確定要對友方使用〈雷暴〉？");
    store.cancelCrossSide();
    expect(store.view.combatSelected.map(String).sort()).toEqual([String(ALLY), String(FOE_A)].sort());
    expect(focus()).toBe("area-confirm");
    store.focusPress("Enter");
    const envelope = heldPayload();
    expect(envelope.payload).toEqual({ skill_key: "x_storm", target_ids: [ALLY, FOE_A] });
  });

  it("shorthands: `all` asks, `all-enemies` and a beneficial `all-allies` send at once", () => {
    enterCombat();
    openSkill("x_storm");
    store.focusItemByKey("shorthand-all");
    store.focusPress("Enter");
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(question()).toBe("確定要對友方使用〈雷暴〉？");
    store.cancelCrossSide();
    store.focusItemByKey("shorthand-all-enemies");
    store.focusPress("Enter");
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(question()).toBeNull();
    expect(sent().at(-1).payload).toEqual({ skill_key: "x_storm", target_shorthand: "all-enemies" });

    enterCombat();
    openSkill("x_bloom");
    store.focusItemByKey("shorthand-all-allies");
    store.focusPress("Enter");
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(question()).toBeNull();
    expect(sent().at(-1).payload).toEqual({ skill_key: "x_bloom", target_shorthand: "all-allies" });
  });

  it("a both-facts skill names each side, and both with `all`", () => {
    enterCombat();
    openSkill("x_tide");
    store.focusItemByKey("shorthand-all");
    store.focusPress("Enter");
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(question()).toBe("確定要對友方與敵方使用〈潮汐逆轉〉？");
    store.cancelCrossSide();
    store.focusItemByKey(`area-${FOE_A}`);
    store.focusPress(" ");
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(question()).toBe("確定要對敵方使用〈潮汐逆轉〉？");
    store.cancelCrossSide();
    store.focusItemByKey(`area-${FOE_A}`);
    store.focusPress(" ");
    store.focusItemByKey(`area-${ALLY}`);
    store.focusPress(" ");
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(question()).toBe("確定要對友方使用〈潮汐逆轉〉？");
  });

  it("an unresolvable target fails closed with 友方與敵方", () => {
    // The protocol rejects a candidate with no participant row, so the one
    // reachable unresolvable target is a SELF cast whose actor no committed
    // row carries.
    const noActor = ROSTER.filter((p) => p.identity !== PLAYER);
    enterCombat({
      participants: noActor,
      attackTargets: [ALLY, FOE_A, FOE_B],
    });
    openSkill("x_curse");
    store.focusPress("Enter");
    expect(sent()).toHaveLength(0);
    expect(question()).toBe("確定要對友方與敵方使用〈自縛〉？");
  });

  it("same-side use sends at once", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${FOE_A}`);
    store.focusPress("Enter");
    expect(question()).toBeNull();
    expect(sent().at(-1).payload).toEqual({ skill_key: ATTACK, target_ids: [FOE_A] });
    const cases = [
      ["x_heal", `target-${ALLY}`],
      ["x_ward", `target-${ALLY}`],
      ["x_push", `target-${FOE_A}`],
      ["x_rally", "self-confirm"],
      ["x_nova", "none-confirm"],
    ];
    for (const [key, row] of cases) {
      enterCombat();
      openSkill(key);
      store.focusItemByKey(row);
      store.focusPress("Enter");
      expect(question(), key).toBeNull();
      expect(sent().at(-1).payload.skill_key, key).toBe(key);
    }
    // Flee and the Forfeit confirmation are untouched.
    enterCombat();
    store.focusItemByKey("forfeit");
    store.focusPress("Enter");
    store.focusItemByKey("confirm-forfeit");
    store.focusPress("Enter");
    expect(question()).toBeNull();
    expect(sent().at(-1).action_id).toBe("combat.forfeit");
  });

  it("a panel replacement that drops the target cancels; an unrelated one keeps it", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${ALLY}`);
    store.focusPress("Enter");
    replace({}); // the same candidates: a resync
    expect(question()).toBe("確定要對友方使用〈基本攻擊〉？");
    const focusRequests = store.view.dockFocusRequest;
    replace({ attackTargets: [FOE_A, FOE_B] });
    expect(question()).toBeNull();
    expect(sent()).toHaveLength(0);
    expect(store.view.dockFocusRequest).toBe(focusRequests + 1);
  });

  it("a disabled skill or a dropped shorthand cancels", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${ALLY}`);
    store.focusPress("Enter");
    replace({ disableAttack: true });
    expect(question()).toBeNull();

    enterCombat();
    openSkill("x_storm");
    store.focusItemByKey("shorthand-all");
    store.focusPress("Enter");
    store.focusItemByKey("area-confirm");
    store.focusPress("Enter");
    expect(question()).not.toBeNull();
    revision += 1;
    const next = panels();
    next.context_actions.skills[0].groups[0].skills.find((s) => s.key === "x_storm").shorthands = ["all-enemies"];
    store.receive(gen, "ui_update", [fx.update({ revision, mode: "combat", panels: next })], {});
    expect(question()).toBeNull();
    expect(sent()).toHaveLength(0);
  });

  it("a mode change cancels without a dock focus request", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${ALLY}`);
    store.focusPress("Enter");
    const focusRequests = store.view.dockFocusRequest;
    replace({}, "exploration");
    expect(question()).toBeNull();
    expect(sent()).toHaveLength(0);
    expect(store.view.dockFocusRequest).toBe(focusRequests);
  });

  it("a playing round cancels and requests the dock focus", () => {
    vi.useFakeTimers();
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${ALLY}`);
    store.focusPress("Enter");
    // Another surface's request plays a round under the question.
    const requestId = store.dispatchAction("combat.cast", { skill_key: ATTACK, target_ids: [FOE_A] });
    store.appendText("out", "你擲出了骰子。");
    const focusRequests = store.view.dockFocusRequest;
    replace({}, "combat", {
      combat_beats: {
        schema_version: 1, available: true, round: "s-1/1",
        beats: [{ seq: 0, action: 0, kind: "roll", actor: String(PLAYER), target: String(FOE_A), amount: null, hp_after: null, text: "你擲出了骰子。" }],
      },
    });
    store.receive(gen, "ui_action_result", [fx.actionResult({ request_id: requestId, presentation_revision: revision })], {});
    expect(store.view.dispatch.beatLocked).toBe(true);
    expect(question()).toBeNull();
    expect(store.view.dockFocusRequest).toBeGreaterThan(focusRequests);
    expect(sent()).toHaveLength(1);
  });

  it("是 waits while a mutation is in flight", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${ALLY}`);
    store.focusPress("Enter");
    store.dispatchAction("combat.flee", { session_id: "s-1" });
    expect(sent()).toHaveLength(1);
    expect(store.confirmCrossSide()).toBeNull();
    expect(sent()).toHaveLength(1);
    expect(question()).toBe("確定要對友方使用〈基本攻擊〉？");
    // 否 still answers.
    expect(store.cancelCrossSide()).toBe(true);
  });
});
