// webclient-combat-beat-queue (design D5/D8/D9): the store's combat beat
// playback — the bind rule, the lock, the pause, skip/flush, the terminal
// snapshot, the generation reset, and the fallback. The motion token is
// stubbed so the pause is asserted in milliseconds, not wall time; the
// protocol fixtures are the payloads the preserved reducer already proves
// valid.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

// The script-side token reader is the one DOM seam; the store stub pins the
// pause and can be re-pointed at 0 for the "a missing token never holds
// anything" case.
vi.mock("../../lib/motion_tokens.js", () => ({ readMotionMs: vi.fn(() => 400) }));

import { readMotionMs } from "../../lib/motion_tokens.js";
import CombatMenu from "../../lib/combat_menu.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

// The attack key is wire vocabulary owned by the combat model (the root
// attack opener resolves it), never a literal in the suite.
const ATTACK_KEY = CombatMenu.BASIC_ATTACK_KEY;

const FOE_REF = "7";
const PLAYER_REF = "42";
const ROUND = "s-1/1";
const PAUSE_MS = 400;

// The round's two beats: one roll and one damage beat whose `action` is the
// 0-based ordinal of its source EventLog, so the round's own lines are the
// response's first two `out` blocks.
const ROUND_BEATS = [
  {
    seq: 0,
    action: 0,
    kind: "roll",
    actor: PLAYER_REF,
    target: FOE_REF,
    amount: null,
    hp_after: null,
    text: "你擲出了骰子。",
  },
  {
    seq: 1,
    action: 1,
    kind: "damage",
    actor: PLAYER_REF,
    target: FOE_REF,
    amount: 12,
    hp_after: 68,
    text: "你擊中了灰袍盜賊，造成 12 點傷害。",
  },
];

const ROUND_LINES = ["你擲出了骰子。", "你擊中了灰袍盜賊，造成 12 點傷害。"];

function beatPanel(round = ROUND, beats = ROUND_BEATS) {
  return { schema_version: 1, available: true, round, beats };
}

function participants(foeHp = 80) {
  return [
    {
      identity: 7,
      token: "e1",
      display_name: "灰袍盜賊",
      team: "foes",
      state: foeHp > 0 ? "active" : "defeated",
      hp_current: foeHp,
      hp_maximum: 80,
      portrait_ref: FOE_REF,
    },
    {
      identity: 42,
      token: "a1",
      display_name: "影行者",
      team: "party",
      state: "active",
      hp_current: 80,
      hp_maximum: 100,
      portrait_ref: PLAYER_REF,
    },
  ];
}

describe("store combat beat playback (webclient-combat-beat-queue)", () => {
  let store;
  let sender;

  function snapshotPayload(revision, foeHp = 80) {
    return fx.snapshot({
      revision,
      mode: "combat",
      panels: {
        status: fx.statusPanel(),
        context_actions: fx.combatActions({ participants: participants(foeHp) }),
      },
    });
  }

  function openCombat() {
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    store.setSender(sender);
    expect(store.receive(1, "ui_snapshot", [snapshotPayload(1)], {}).accepted).toBe(true);
  }

  // The wire order: the round's lines, then the publication carrying its
  // panel, then the result.
  function settleRound({ panel = beatPanel(), revision = 2, action = "combat.cast", result = true } = {}) {
    const requestId = store.dispatchAction(action, ATTACK_KEY);
    for (const line of ROUND_LINES) {
      store.appendText("out", line);
    }
    expect(
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            revision,
            mode: "combat",
            panels: {
              status: fx.statusPanel(),
              context_actions: fx.combatActions({ participants: participants() }),
              combat_beats: panel,
            },
          }),
        ],
        {},
      ).accepted,
    ).toBe(true);
    if (result) {
      store.receive(
        1,
        "ui_action_result",
        [fx.actionResult({ request_id: requestId, presentation_revision: revision })],
        {},
      );
    }
    return requestId;
  }

  function playback() {
    return store.view.beatPlayback;
  }

  // The `off` level (design D2/D4): the store's own preference, applied to
  // <html data-motion> exactly as the live client applies it.
  function scaleToOff() {
    store.setMotionLevel("off");
    expect(store.view.motionLevel).toBe("off");
  }

  beforeEach(() => {
    // The presentation preferences persist through the versioned layout
    // store; every case starts from nothing stored.
    window.localStorage.clear();
    vi.useFakeTimers();
    vi.mocked(readMotionMs).mockReturnValue(PAUSE_MS);
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
  });

  afterEach(() => {
    window.localStorage.clear();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("binds one round to the dispatch that produced it", () => {
    openCombat();
    settleRound();
    const bound = playback();
    expect(bound).not.toBeNull();
    expect(bound.round).toBe(ROUND);
    expect(bound.startSeq).toBe(1);
    expect(bound.auto).toBe(true);
    expect(bound.index).toBe(0);
    expect(bound.count).toBe(2);
    expect(bound.phase).toBe("text");
    expect(bound.texts).toEqual(ROUND_LINES);
    expect(bound.coveredLines).toBe(2);
    expect(bound.terminal).toBe(false);
    // The response really starts at the recorded mark: the echo's `in` line.
    expect(store.responseMarks).toEqual([1]);
    // The displayed hit points are the damaged participant's pre-round value.
    expect(store.view.displayHp).toEqual({ [FOE_REF]: 80 });
  });

  it("holds the dispatch lock until the round is done AND the revision is accepted", () => {
    openCombat();
    settleRound();
    // The revision is declared and committed in the same pass, so the
    // revision lock is already clear; the playback lock is not.
    expect(store.view.dispatch.inFlight).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(true);
    expect(store.dispatchAction("combat.cast", {})).toBeNull();
    expect(sender.sent.actions).toHaveLength(1);
    // The router is gated on the same pair.
    expect(store.view.dispatch.beatLocked).toBe(true);

    store.skipBeats();
    expect(store.view.dispatch.beatLocked).toBe(false);
    expect(store.dispatchAction("combat.cast", {})).toBe("session:2");
  });

  it("keeps the revision lock while the round plays, and both locks clear together", () => {
    openCombat();
    // The panel publication alone (before the result) binds the round and
    // leaves the revision lock held.
    const requestId = store.dispatchAction("combat.cast", ATTACK_KEY);
    for (const line of ROUND_LINES) {
      store.appendText("out", line);
    }
    store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, mode: "combat", panels: { combat_beats: beatPanel() } })],
      {},
    );
    expect(store.view.dispatch.inFlight).toEqual({ requestId, presentationRevision: null });
    expect(store.view.dispatch.beatLocked).toBe(true);
    expect(store.dispatchAction("combat.cast", {})).toBeNull();

    // The result declares the revision: the revision lock releases, the
    // playback lock still holds.
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: requestId, presentation_revision: 2 })], {});
    expect(store.view.dispatch.inFlight).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(true);
    expect(store.dispatchAction("combat.cast", {})).toBeNull();

    // The round ends by itself and the dock accepts again.
    store.beatShown(0);
    vi.advanceTimersByTime(PAUSE_MS);
    store.beatShown(1);
    vi.advanceTimersByTime(PAUSE_MS);
    expect(playback().phase).toBe("done");
    expect(store.view.dispatch.beatLocked).toBe(false);
    expect(store.dispatchAction("combat.cast", {})).toBe("session:2");
  });

  it("waits the beat pause read from the motion token between beats", () => {
    openCombat();
    settleRound();
    store.beatShown(0);
    expect(readMotionMs).toHaveBeenCalledWith("--motion-beat");
    expect(playback().phase).toBe("pause");
    expect(playback().index).toBe(0);
    // The roll beat damages nobody, so the target still shows its pre-round
    // value until its own damage beat is shown.
    expect(store.view.displayHp).toEqual({ [FOE_REF]: 80 });
    vi.advanceTimersByTime(PAUSE_MS - 1);
    expect(playback().index).toBe(0);
    expect(playback().phase).toBe("pause");
    vi.advanceTimersByTime(1);
    expect(playback().index).toBe(1);
    expect(playback().phase).toBe("text");
    // The damage beat applies its `hp_after` the moment it is fully shown.
    store.beatShown(1);
    expect(store.view.displayHp).toEqual({ [FOE_REF]: 68 });
  });

  it("never reads the beat token at off: nothing plays and no timer is armed", () => {
    vi.mocked(readMotionMs).mockReturnValue(PAUSE_MS);
    openCombat();
    // The level is read when the round binds: `off` is already in effect.
    scaleToOff();
    settleRound();
    expect(readMotionMs).not.toHaveBeenCalled();
    expect(playback().auto).toBe(false);
    expect(playback().phase).toBe("done");
    expect(store.view.dispatch.beatLocked).toBe(false);
    expect(store.dispatchAction("combat.cast", {})).toBe("session:2");
  });

  it("never holds the lock when the token is unset (the reader's 0ms)", () => {
    vi.mocked(readMotionMs).mockReturnValue(0);
    openCombat();
    settleRound();
    store.beatShown(0);
    expect(playback().phase).toBe("pause");
    vi.advanceTimersByTime(0);
    expect(playback().index).toBe(1);
    store.beatShown(1);
    vi.advanceTimersByTime(0);
    expect(playback().phase).toBe("done");
    expect(store.view.dispatch.beatLocked).toBe(false);
  });

  it("releases at once on skipBeats and on a typed command's flush", () => {
    openCombat();
    settleRound();
    store.skipBeats();
    expect(playback().phase).toBe("done");
    expect(store.view.displayHp).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(false);
    // A completed round does not re-arm the timer.
    vi.advanceTimersByTime(PAUSE_MS * 4);
    expect(playback().phase).toBe("done");
  });

  it("flushes a playing round before the typed command's own line is appended", () => {
    openCombat();
    settleRound();
    expect(playback().phase).toBe("text");
    expect(store.sendText("look")).toBe(true);
    expect(playback().phase).toBe("done");
    expect(store.view.dispatch.beatLocked).toBe(false);
    // The input line is the last retained line, so the flush preceded it.
    const lines = store.narrative;
    expect(lines[lines.length - 1].kind).toBe("in");
    expect(lines[lines.length - 1].text).toBe("look");
    expect(sender.sent.texts).toEqual(["look"]);
  });

  it("ignores a stale shown and a repeated round id", () => {
    openCombat();
    settleRound();
    store.beatShown(1);
    expect(playback().index).toBe(0);
    expect(playback().phase).toBe("text");
    store.skipBeats();

    // A second action whose publication carries the SAME round id never
    // replays it (a retained panel included).
    store.dispatchAction("combat.cast", ATTACK_KEY);
    store.appendText("out", "你擲出了骰子。");
    store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 3, mode: "combat", panels: { combat_beats: beatPanel() } })],
      {},
    );
    expect(playback().phase).toBe("done");
    expect(playback().index).toBe(0);
    expect(store.view.dispatch.beatLocked).toBe(false);
  });

  it("binds nothing when no combat action is in flight", () => {
    openCombat();
    // An ordinary exploration dispatch: its publication carries a panel, but
    // the action is not one that can settle a round.
    const requestId = store.dispatchAction("explore.wait", { daypart: "dusk" });
    store.appendText("out", "你等待了一陣。");
    store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, panels: { combat_beats: beatPanel() } })],
      {},
    );
    expect(playback()).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(false);
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: requestId, presentation_revision: 2 })], {});
    // Once seen, that round never plays later either.
    store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 3, panels: { combat_beats: beatPanel() } })],
      {},
    );
    expect(playback()).toBeNull();
  });

  it("binds nothing for the unavailable panel form", () => {
    openCombat();
    store.dispatchAction("combat.cast", ATTACK_KEY);
    store.appendText("out", "你等待了一陣。");
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          mode: "combat",
          panels: {
            combat_beats: {
              schema_version: 1,
              available: false,
              reason: { code: "round_unavailable", message: "本回合沒有可用的節拍" },
            },
          },
        }),
      ],
      {},
    );
    expect(playback()).toBeNull();
    expect(store.view.displayHp).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(false);
  });

  it("binds a terminal snapshot's round from the pre-round roster and status", () => {
    openCombat();
    const requestId = store.dispatchAction("combat.cast", ATTACK_KEY);
    for (const line of ROUND_LINES) {
      store.appendText("out", line);
    }
    store.appendText("out", "灰袍盜賊倒下了。");
    store.appendText("out", "戰鬥勝利。");
    // The completing publication is a full snapshot whose mode is already
    // `exploration` and whose context_actions is the exploration kind, so the
    // pre-round roster can only come from `prev`.
    expect(
      store.receive(
        1,
        "ui_snapshot",
        [
          fx.snapshot({
            revision: 2,
            mode: "exploration",
            panels: {
              status: fx.statusPanel({ resources: { hp: { current: 80, maximum: 100 }, mp: { current: 30, maximum: 50 }, sp: { current: 12, maximum: 40 } } }),
              context_actions: fx.explorationActions(),
              combat_beats: beatPanel(),
            },
          }),
        ],
        {},
      ).accepted,
    ).toBe(true);
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: requestId, presentation_revision: 2 })], {});
    const bound = playback();
    expect(bound).not.toBeNull();
    expect(bound.terminal).toBe(true);
    expect(bound.coveredLines).toBe(2);
    expect(store.view.mode).toBe("exploration");
    expect(store.view.combatParticipants).toEqual([]);
    expect(store.view.displayHp).toEqual({ [FOE_REF]: 80 });
  });

  it("plays a stale outcome's round under the still-held revision lock", () => {
    openCombat();
    settleRound({ result: false });
    expect(playback().phase).toBe("text");
    store.receive(
      1,
      "ui_action_result",
      [fx.actionResult({ request_id: "session:1", outcome: "stale", code: "stale", presentation_revision: 3 })],
      {},
    );
    // The stale outcome keeps the revision lock until the recovery commits,
    // and the round keeps playing in the meantime.
    expect(store.view.dispatch.inFlight).toEqual({ requestId: "session:1", presentationRevision: 3 });
    expect(store.view.dispatch.beatLocked).toBe(true);
    expect(store.dispatchAction("combat.cast", {})).toBeNull();
    // The recovery publication carries the unavailable form; it cannot
    // unbind the round, and the round still ends on its own.
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 3,
          mode: "combat",
          panels: {
            combat_beats: {
              schema_version: 1,
              available: false,
              reason: { code: "round_unavailable", message: "本回合沒有可用的節拍" },
            },
          },
        }),
      ],
      {},
    );
    expect(store.view.dispatch.inFlight).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(true);
    store.beatShown(0);
    vi.advanceTimersByTime(PAUSE_MS);
    store.beatShown(1);
    vi.advanceTimersByTime(PAUSE_MS);
    expect(playback().phase).toBe("done");
    expect(store.dispatchAction("combat.cast", {})).toBe("session:2");
  });

  it("resets without playing on a new transport generation", () => {
    openCombat();
    settleRound();
    expect(playback().phase).toBe("text");
    store.beginTransport(2);
    expect(playback()).toBeNull();
    expect(store.view.displayHp).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(false);
    // A pending pause timer cannot revive it.
    vi.advanceTimersByTime(PAUSE_MS * 4);
    expect(playback()).toBeNull();
  });

  it("resets without playing on a detach", () => {
    openCombat();
    settleRound();
    store.receive(1, "ui_protocol_error", [fx.protocolError()], {});
    expect(store.view.phase).toBe("detached");
    expect(playback()).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(false);
  });

  it("publishes nothing for the round while no round is bound", () => {
    openCombat();
    expect(playback()).toBeNull();
    expect(store.view.displayHp).toBeNull();
    expect(store.view.dispatch.beatLocked).toBe(false);
    expect(store.view.dispatch.inFlight).toBeNull();
  });
});
