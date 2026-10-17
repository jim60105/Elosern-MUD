// webclient-party-exit-confirmation: the party-scope exit confirmation of the
// combat card. Retreat and Surrender are root rows that request one read-only
// `combat.exit_prompt`; the server-bound prompt opens the shared question card
// with 否 focused, and only 是 sends the one `combat.exit_confirm` with the
// token. Cancelling changes nothing — the draft, the menu, the focused row and
// the clock all stay exactly as they were — and every session/round/epoch/
// transport replacement cancels the prompt without a retry.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("../../lib/motion_tokens.js", () => ({ readMotionMs: vi.fn(() => 400) }));

import { useElosernStore } from "../../stores/elosern.js";
import CombatMenu from "../../lib/combat_menu.js";
import * as fx from "./protocol_fixtures.js";

const PROMPT_DATA = {
  operation: "surrender",
  confirmation_token: "S-0-9f8e7d6c5b4a39281706f5e4",
  scope: "party",
  consequence: "全隊退出戰鬥，並結算目前已累積的戰鬥時間。\n一般戰鬥會以戰敗收場。",
};

const RETREAT_DATA = {
  ...PROMPT_DATA,
  operation: "retreat",
  confirmation_token: "R-0-9f8e7d6c5b4a39281706f5e4",
  consequence: "全隊嘗試脫離戰鬥。\n撤退失敗會消耗全隊本回合行動。",
};

describe("party-scope exit confirmation (store flow)", () => {
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

  function panels(overrides = {}) {
    return {
      status: fx.statusPanel(),
      context_actions: fx.combatActions(overrides),
      local_map: fx.localMapPanel(),
    };
  }

  function enterCombat(overrides = {}) {
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
    const result = store.receive(gen, "ui_snapshot", [fx.snapshot({ mode: "combat", panels: panels(overrides) })], {});
    expect(result.accepted, JSON.stringify([result, store.lastPanelRejection])).toBe(true);
  }

  function replace(overrides, mode = "combat", extra = {}) {
    revision += 1;
    const body = mode === "combat" ? panels(overrides) : { context_actions: fx.explorationActions() };
    const result = store.receive(gen, "ui_update", [fx.update({ revision, mode, panels: { ...body, ...extra } })], {});
    expect(result.accepted).toBe(true);
  }

  const sent = () => sender.sent.actions;
  const requests = (actionId) => sent().filter((envelope) => envelope.action_id === actionId);
  const prompt = () => store.view.partyExitConfirm ?? null;

  // Activate the 投降 root row: one read-only prompt request, nothing else.
  function openExit(operation = "surrender") {
    store.focusItemByKey(operation);
    store.focusPress("Enter");
  }

  function deliverPrompt(data = PROMPT_DATA) {
    const request = requests("combat.exit_prompt").at(-1);
    store.receive(
      gen,
      "ui_action_result",
      [
        fx.actionResult({
          request_id: request.request_id,
          code: "party_exit_prompt",
          data,
          presentation_revision: revision,
        }),
      ],
      {},
    );
  }

  it("the root rows request the prompt, and only the prompt result opens the card", () => {
    enterCombat();
    const before = store.view.contextActions;
    openExit("retreat");
    // The request is the exact three-field guarded payload; it carries no
    // actor and changes no state.
    expect(sent()).toHaveLength(1);
    expect(sent()[0].action_id).toBe("combat.exit_prompt");
    expect(sent()[0].payload).toEqual({
      session_id: "s-1",
      round_revision: 0,
      operation: "retreat",
    });
    expect(prompt()).toBeNull();
    expect(store.view.contextActions).toEqual(before);

    deliverPrompt(RETREAT_DATA);
    expect(prompt()).toEqual({
      operation: "retreat",
      label: "撤退",
      question: "確定要全隊撤退？",
      consequence: RETREAT_DATA.consequence,
    });
  });

  it("否 / close / Escape discard the prompt and change nothing", () => {
    enterCombat();
    const before = store.view.contextActions;
    const revisionBefore = store.view.revision;
    openExit();
    deliverPrompt();
    const focusRequests = store.view.dockFocusRequest;
    expect(store.cancelPartyExit()).toBe(true);
    expect(prompt()).toBeNull();
    expect(sent().filter((envelope) => envelope.action_id === "combat.exit_confirm")).toHaveLength(0);
    // The whole draft, the committed panel and the clock are untouched, and
    // the row the prompt was opened from keeps focus at the root.
    expect(store.view.contextActions).toEqual(before);
    expect(store.view.revision).toBe(revisionBefore);
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.focus.key).toBe("surrender");
    expect(store.view.dockFocusRequest).toBe(focusRequests + 1);
  });

  it("是 sends exactly one combat.exit_confirm with the held token", () => {
    enterCombat();
    openExit();
    deliverPrompt();
    const requestId = store.confirmPartyExit();
    expect(requestId).toBeTruthy();
    const confirms = requests("combat.exit_confirm");
    expect(confirms).toHaveLength(1);
    expect(confirms[0].payload).toEqual({
      session_id: "s-1",
      round_revision: 0,
      operation: "surrender",
      confirmation_token: PROMPT_DATA.confirmation_token,
    });
    expect(prompt()).toBeNull();
    // The card is gone: a second activation (a repeated Enter, a reconnect or
    // a re-observed result) can never send the stored Yes again.
    expect(store.confirmPartyExit()).toBeNull();
    expect(requests("combat.exit_confirm")).toHaveLength(1);
  });

  it("no client path confirms without a held prompt", () => {
    enterCombat();
    expect(store.confirmPartyExit()).toBeNull();
    expect(sent()).toHaveLength(0);
    // Nor does a stale prompt tolerate a forged envelope: the only producer
    // of combat.exit_confirm is confirmPartyExit on the held record.
    expect(CombatMenu.ROOT_ACTIONS).not.toContain("flee");
    expect(CombatMenu.ROOT_ACTIONS).not.toContain("forfeit");
    const root = store.view.rootMenu.items;
    expect(root.map((item) => item.key)).toEqual([
      "attack",
      "skills",
      "items",
      "bag",
      "defend",
      "dodge",
      "taunt",
      "retreat",
      "surrender",
    ]);
    expect(root.some((item) => item.actionId === "combat.flee" || item.actionId === "combat.forfeit")).toBe(false);
  });

  it("the operation is actor-independent: an uncommandable member still exits", () => {
    enterCombat({
      actors: [{ identity: 8, commandable: false, reason: { code: "knocked_out", message: "這名成員已倒地。" } }],
    });
    openExit("retreat");
    expect(requests("combat.exit_prompt")).toHaveLength(1);
    expect(requests("combat.exit_prompt")[0].payload).toEqual({
      session_id: "s-1",
      round_revision: 0,
      operation: "retreat",
    });
    deliverPrompt(RETREAT_DATA);
    expect(prompt().label).toBe("撤退");
  });

  it("a round, session, mode, epoch or transport replacement cancels without a retry", () => {
    enterCombat();
    openExit();
    deliverPrompt();
    expect(prompt()).not.toBeNull();
    // The same-round resync keeps the prompt (its token is still valid).
    replace({});
    expect(prompt()).not.toBeNull();
    // A committed round revision invalidates it.
    replace({
      session: { session_id: "s-1", mode: "hostile", round: 2, round_revision: 1, state: "ready", reason: null },
      draft: { round_revision: 1, draft_version: 0, required_actor_ids: [8], entries: [], needs_selection_ids: [8], reselection_reasons: [] },
    });
    expect(prompt()).toBeNull();
    expect(requests("combat.exit_confirm")).toHaveLength(0);

    // Another session id too.
    openExit();
    deliverPrompt();
    replace({ session: { session_id: "s-2", mode: "hostile", round: 1, round_revision: 0, state: "ready", reason: null } });
    expect(prompt()).toBeNull();

    // A mode change (the terminal settlement) and a disconnect.
    openExit();
    deliverPrompt();
    replace({}, "exploration");
    expect(prompt()).toBeNull();

    enterCombat();
    openExit();
    deliverPrompt();
    store.setConnected(false);
    expect(prompt()).toBeNull();

    // A new epoch/transport generation (a reconnect) never reopens or
    // replays the old confirmation.
    enterCombat();
    openExit();
    deliverPrompt();
    store.beginTransport(gen + 1);
    gen += 1;
    store.setConnected(true);
    store.setLoggedIn(true);
    expect(prompt()).toBeNull();
    expect(requests("combat.exit_confirm")).toHaveLength(0);
  });

  it("an unrelated result never opens the card; a failed send releases the dock", () => {
    enterCombat();
    openExit();
    store.receive(
      gen,
      "ui_action_result",
      [fx.actionResult({ request_id: "session:999", code: "completed", presentation_revision: revision })],
      {},
    );
    expect(prompt()).toBeNull();

    // A synchronous transport failure releases the in-flight lock with no
    // result: the local intent is dropped and the next request works.
    const failing = {
      sent: { actions: [], texts: [] },
      sendAction() {
        throw new Error("socket closed");
      },
      sendText() {},
    };
    enterCombat();
    store.setSender(failing);
    openExit();
    expect(prompt()).toBeNull();
    const next = fx.createFakeSender();
    store.setSender(next);
    sender = next;
    openExit();
    expect(requests("combat.exit_prompt")).toHaveLength(1);
  });
});
