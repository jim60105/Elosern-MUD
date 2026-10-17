// webclient-party-command-selection: the store side of the commanded-actor
// selector — one read-only combat.actor_choices query per switch, the guarded
// combat.command envelope with the committed session/round/draft versions,
// commanded-actor SELF lighting and cross-side wording, revisit/replacement,
// the one-shot advance after a nonfinal draft save, and the reconnect and
// invalidation paths that must never auto-send or replay intent.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("../../lib/motion_tokens.js", () => ({ readMotionMs: vi.fn(() => 400) }));

import { useElosernStore } from "../../stores/elosern.js";
import CombatMenu from "../../lib/combat_menu.js";
import * as fx from "./protocol_fixtures.js";

const ATTACK = CombatMenu.BASIC_ATTACK_KEY;
const PLAYER = 42;
const ALLY = 8;
const FOE = 11;

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
  participant(FOE, "e1", "灰袍盜賊", "foes"),
];

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

function skills() {
  return [
    {
      category: "martial_arts",
      label: "武技",
      groups: [
        {
          group: null,
          label: null,
          skills: [
            skill(ATTACK, "普通攻擊", "single", [ALLY, FOE], { hostile: true }),
            skill("t_mend", "急救", "single", [PLAYER, ALLY], { beneficial: true }),
            skill("t_guard", "守勢", "self", []),
            skill("t_curse", "自縛", "self", [], { hostile: true }),
          ],
        },
      ],
    },
  ];
}

describe("party command selection (store)", () => {
  let store;
  let sender;
  let gen = 0;
  let revision = 1;

  beforeEach(() => {
    window.localStorage.clear();
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    gen = 0;
    revision = 1;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // One committed v7 combat panel for the requested actor. `draft` is the
  // authoritative progress; the entries are the server's, never client state.
  function panel({
    actorId = PLAYER,
    draftVersion = 0,
    entries = [],
    needs = [PLAYER, ALLY],
    actors = [
      { identity: PLAYER, commandable: true, reason: null },
      { identity: ALLY, commandable: true, reason: null },
    ],
    participants = ROSTER,
  } = {}) {
    return fx.combatActions({
      participants,
      actors,
      choices: { actor_id: actorId, skills: skills(), items: [], tactics: [] },
      draft: {
        round_revision: 0,
        draft_version: draftVersion,
        required_actor_ids: [PLAYER, ALLY],
        entries,
        needs_selection_ids: needs,
        reselection_reasons: [],
      },
      session: { session_id: "s-1", mode: "hostile", round: 1, round_revision: 0, state: "ready", reason: null },
    });
  }

  function enterCombat(options = {}) {
    // A second entry in one test is a fresh client (a new transport
    // generation retires the previous epoch).
    if (gen > 0) {
      setActivePinia(createPinia());
      store = useElosernStore();
      sender = fx.createFakeSender();
      store.setSender(sender);
    }
    gen += 1;
    revision = 1;
    store.beginTransport(gen);
    store.setConnected(true);
    store.setLoggedIn(true);
    const result = store.receive(
      gen,
      "ui_snapshot",
      [fx.snapshot({ mode: "combat", revision, panels: { status: fx.statusPanel(), context_actions: panel(options) } })],
      {},
    );
    expect(result.accepted, JSON.stringify(result)).toBe(true);
  }

  // Commit a replacement panel (the server's answer to anything).
  function commit(options, { mode = "combat", extra = {} } = {}) {
    revision += 1;
    const body = mode === "combat" ? { context_actions: panel(options) } : { context_actions: fx.explorationActions() };
    const result = store.receive(
      gen,
      "ui_update",
      [fx.update({ revision, mode, panels: { ...body, ...extra } })],
      {},
    );
    expect(result.accepted, JSON.stringify(result)).toBe(true);
    return revision;
  }

  // Answer one dispatched action with its success result at a revision the
  // client has already committed (the ordinary result ordering).
  function answer(action, code, { at = revision } = {}) {
    store.receive(
      gen,
      "ui_action_result",
      [fx.actionResult({ request_id: action.request_id, code, presentation_revision: at })],
      {},
    );
  }

  function lastAction() {
    return sender.sent.actions.at(-1);
  }

  function openAttack() {
    store.focusItemByKey("attack");
    store.focusPress("Enter");
  }

  it("switches actors with exactly one read-only query and opens the root flow", () => {
    enterCombat();
    expect(store.openCombatActor()).toBe(true);
    expect(store.router.currentDescriptor().source).toBe("combat.actor");
    // The actor rows carry the authoritative draft status.
    const menu = store.resolveFrame({ source: "combat.actor", params: {} });
    expect(menu.items.map((item) => item.key)).toEqual([`actor-${PLAYER}`, `actor-${ALLY}`]);
    expect(menu.items.every((item) => item.description === "待選擇")).toBe(true);

    store.focusItemByKey(`actor-${ALLY}`);
    expect(store.focusPress("Enter")).toBe(true);
    // One read-only query; no command, no possession.
    expect(sender.sent.actions).toHaveLength(1);
    const query = lastAction();
    expect(query.action_id).toBe("combat.actor_choices");
    expect(query.payload).toEqual({ session_id: "s-1", round_revision: 0, actor_id: ALLY });

    // The server republishes the requested actor's canonical choices.
    const rev = commit({ actorId: ALLY });
    answer(query, "actor_choices", { at: rev });
    expect(store.router.currentDescriptor().source).toBe("combat.root");
    expect(store.view.focus.key).toBe("attack");
    expect(sender.sent.actions).toHaveLength(1);
  });

  it("selecting the already-commanded actor returns to the root without a query", () => {
    enterCombat();
    store.openCombatActor();
    store.focusItemByKey(`actor-${PLAYER}`);
    expect(store.focusPress("Enter")).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.router.currentDescriptor().source).toBe("combat.root");
  });

  it("drops the previous actor's unconfirmed selection when the actor changes", () => {
    enterCombat();
    // Choose a scale-capable flow state: open the attack target frame.
    openAttack();
    expect(store.router.currentDescriptor().source).toBe("combat.skill");
    // A committed actor switch (here through the selector) discards it.
    store.openCombatActor();
    store.selectCombatActor(ALLY);
    const query = lastAction();
    const rev = commit({ actorId: ALLY });
    answer(query, "actor_choices", { at: rev });
    expect(store.router.currentDescriptor().source).toBe("combat.root");
    expect(store.view.dockDepth).toBe(1);
  });

  it("revisit replaces the earlier entry and the final confirmation sends one command", () => {
    // The draft already holds the player's confirmed entry; the ally is missing.
    enterCombat({
      needs: [ALLY],
      entries: [{ actor_id: PLAYER, command: { kind: "skill", payload: { skill_key: ATTACK, target_ids: [FOE] } } }],
    });
    store.openCombatActor();
    const menu = store.resolveFrame({ source: "combat.actor", params: {} });
    expect(menu.items[0].description).toBe("已確認");
    expect(menu.items[1].description).toBe("待選擇");
    // Revisit the confirmed member and replace its selection.
    store.focusItemByKey(`actor-${PLAYER}`);
    expect(store.focusPress("Enter")).toBe(true);
    expect(store.router.currentDescriptor().source).toBe("combat.root");
    expect(sender.sent.actions).toHaveLength(0);
    openAttack();
    store.focusItemByKey(`target-${FOE}`);
    store.focusPress("Enter");
    expect(sender.sent.actions).toHaveLength(1);
    const command = lastAction();
    expect(command.action_id).toBe("combat.command");
    expect(command.payload.actor_id).toBe(PLAYER);
    expect(command.payload.command).toEqual({ kind: "skill", payload: { skill_key: ATTACK, target_ids: [FOE] } });
    // A final accepted command resolves the whole round; no party submit
    // screen and no further navigation.
    commit({
      needs: [],
      entries: [
        { actor_id: PLAYER, command: command.payload.command },
        { actor_id: ALLY, command: { kind: "skill", payload: { skill_key: "t_mend", target_ids: [PLAYER] } } },
      ],
    });
    answer(command, "round_committed");
    expect(sender.sent.actions).toHaveLength(1);
    expect(store.view.mode).toBe("combat");
  });

  it("the nonfinal confirmation sends combat.command with the committed versions", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${FOE}`);
    store.focusPress("Enter");
    const command = lastAction();
    expect(command.action_id).toBe("combat.command");
    expect(command.payload).toEqual({
      session_id: "s-1",
      round_revision: 0,
      draft_version: 0,
      actor_id: PLAYER,
      command: { kind: "skill", payload: { skill_key: ATTACK, target_ids: [FOE] } },
    });
  });

  it("after a nonfinal save it queries the first required member still needing a command once", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${FOE}`);
    store.focusPress("Enter");
    const command = lastAction();
    // The server saves the draft: version bumps, the ally still needs one.
    const rev = commit({ needs: [ALLY], draftVersion: 1 });
    answer(command, "draft_saved", { at: rev });
    const advance = lastAction();
    expect(advance.action_id).toBe("combat.actor_choices");
    expect(advance.payload).toEqual({ session_id: "s-1", round_revision: 0, actor_id: ALLY });
    // The advance envelope reads the freshly published revision, never the
    // one before the draft save.
    expect(advance.base_revision).toBe(rev);
    // The companion's choices commit: the advance opens ONE root and never
    // keeps the previous actor's skill/target frame.
    const rev2 = commit({ actorId: ALLY, needs: [ALLY], draftVersion: 1 });
    answer(advance, "actor_choices", { at: rev2 });
    expect(store.router.currentDescriptor().source).toBe("combat.root");
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.focus.key).toBe("attack");
    expect(store.view.focusedSkill).toBeNull();
    expect(store.view.stageTarget).toBeNull();
    // Re-observing the same result dispatches nothing more.
    answer(command, "draft_saved", { at: rev });
    expect(sender.sent.actions.filter((a) => a.action_id === "combat.actor_choices")).toHaveLength(1);
  });

  it("a needs_selection final preflight identifies the member and never advances", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${FOE}`);
    store.focusPress("Enter");
    const command = lastAction();
    const rev = commit({
      needs: [ALLY],
      draftVersion: 1,
      entries: [{ actor_id: PLAYER, command: command.payload.command }],
    });
    answer(command, "needs_selection", { at: rev });
    expect(sender.sent.actions).toHaveLength(1);
    // The rejected member is identifiable through the authoritative draft.
    const menu = store.resolveFrame({ source: "combat.actor", params: {} });
    expect(menu.items.find((item) => item.key === `actor-${ALLY}`).description).toBe("待選擇");
  });

  it("a stale rejection never replays the command", () => {
    enterCombat();
    openAttack();
    store.focusItemByKey(`target-${FOE}`);
    store.focusPress("Enter");
    const command = lastAction();
    commit({ draftVersion: 2 });
    answer(command, "stale_command");
    expect(sender.sent.actions).toHaveLength(1);
  });

  it("reconnect restores the confirmed entries and sends nothing automatically", () => {
    enterCombat();
    // An unconfirmed local target selection exists before the drop.
    openAttack();
    const entries = [{ actor_id: PLAYER, command: { kind: "skill", payload: { skill_key: ATTACK, target_ids: [FOE] } } }];
    // The transport resets into a new generation.
    gen += 1;
    revision = 1;
    store.beginTransport(gen);
    store.setConnected(true);
    const result = store.receive(
      gen,
      "ui_snapshot",
      [
        fx.snapshot({
          presentation_epoch: fx.EPOCH_B,
          mode: "combat",
          revision,
          panels: { status: fx.statusPanel(), context_actions: panel({ needs: [ALLY], entries }) },
        }),
      ],
      {},
    );
    expect(result.accepted, JSON.stringify(result)).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.view.combatProgress).toMatchObject({ confirmed: 1, total: 2, needsSelection: 1 });
    // The restored entries are the server's; the local selection is gone.
    expect(store.router.currentDescriptor().source).toBe("combat.root");
  });

  it("reconnect follows the server's first-missing-actor choice without a query", () => {
    // The server's reconnecting snapshot already names the member still
    // needing a command; the client adopts it and asks nothing.
    gen += 1;
    revision = 1;
    store.beginTransport(gen);
    store.setConnected(true);
    const entries = [
      { actor_id: PLAYER, command: { kind: "skill", payload: { skill_key: ATTACK, target_ids: [FOE] } } },
    ];
    const result = store.receive(
      gen,
      "ui_snapshot",
      [
        fx.snapshot({
          presentation_epoch: fx.EPOCH_C,
          mode: "combat",
          revision,
          panels: { status: fx.statusPanel(), context_actions: panel({ actorId: ALLY, needs: [ALLY], entries }) },
        }),
      ],
      {},
    );
    expect(result.accepted, JSON.stringify(result)).toBe(true);
    expect(store.view.combatProgress).toMatchObject({ actorId: ALLY, confirmed: 1, needsSelection: 1 });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a companion SELF lights the companion while a SINGLE target stays another member", () => {
    enterCombat({ actorId: ALLY });
    // SELF: the only stage position is the commanded companion.
    store.focusItemByKey("skills");
    store.focusPress("Enter");
    store.focusItemByKey("skill-cat-0");
    store.focusPress("Enter");
    store.focusItemByKey("t_guard");
    store.focusPress("Enter");
    expect(store.view.stageTarget.positions).toHaveLength(1);
    expect(store.view.stageTarget.positions[0]).toMatchObject({
      key: "self-confirm",
      kind: "self",
      identities: [String(ALLY)],
    });
    store.resetFramesToRoot();
    // A beneficial SINGLE targeted at the player: the actor stays the
    // commanded companion while the target is another party member.
    store.focusItemByKey("skills");
    store.focusPress("Enter");
    store.focusItemByKey("skill-cat-0");
    store.focusPress("Enter");
    store.focusItemByKey("t_mend");
    store.focusPress("Enter");
    store.focusItemByKey(`target-${PLAYER}`);
    store.focusPress("Enter");
    const command = lastAction();
    expect(command.payload.actor_id).toBe(ALLY);
    expect(command.payload.command.payload).toEqual({ skill_key: "t_mend", target_ids: [PLAYER] });
  });

  it("a companion SELF asks with the companion's own cross-side wording", () => {
    enterCombat({ actorId: ALLY });
    const openCurse = () => {
      store.focusItemByKey("skills");
      store.focusPress("Enter");
      store.focusItemByKey("skill-cat-0");
      store.focusPress("Enter");
      store.focusItemByKey("t_curse");
      store.focusPress("Enter");
    };
    openCurse();
    store.focusPress("Enter");
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.view.crossSideConfirm?.question).toBe("確定要對自己使用〈自縛〉？");
    // 是 sends exactly one envelope bound to the commanded companion.
    expect(store.confirmCrossSide()).toBeTruthy();
    const command = lastAction();
    expect(command.action_id).toBe("combat.command");
    expect(command.payload.actor_id).toBe(ALLY);
    expect(command.payload.command).toEqual({ kind: "skill", payload: { skill_key: "t_curse" } });
    // A committed draft change cancels a fresh held question without sending.
    enterCombat({ actorId: ALLY });
    openCurse();
    store.focusPress("Enter");
    expect(store.view.crossSideConfirm).not.toBeNull();
    commit({ actorId: ALLY, draftVersion: 9, needs: [PLAYER, ALLY] });
    expect(store.view.crossSideConfirm).toBeNull();
    expect(sender.sent.actions).toHaveLength(0);
  });
});
