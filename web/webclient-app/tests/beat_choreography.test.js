// webclient-combat-beat-choreography (design D2/D3/D6/D7): the stage slice a
// playing combat round publishes — which figure plays which gesture on each
// step, which foes stand while the round plays, how long each step's act
// lasts, and the terminal-round hold. Pure: the queue module is exercised
// directly, with the motion-token reader stubbed by name.
import { describe, expect, it, vi } from "vitest";

import { actMs, beatHoldFor, beatReducer, GESTURE_TOKENS, planRound, stageFor } from "../lib/beat_queue.js";

const PLAYER = "42";
const ALLY = "43";
const ROUND = "s-1/2";

function foe(identity, hp = 30, state = "active") {
  return {
    identity,
    token: `e${identity}`,
    display_name: `敵${identity}`,
    team: "foes",
    state,
    hp_current: hp,
    hp_maximum: 30,
    portrait_ref: String(identity),
  };
}

const ROSTER = [
  foe(3),
  foe(4),
  foe(5, 0, "defeated"),
  foe(6),
  foe(7),
  foe(8),
  {
    identity: 42,
    token: "a1",
    display_name: "影行者",
    team: "party",
    state: "active",
    hp_current: 80,
    hp_maximum: 100,
    portrait_ref: PLAYER,
  },
  {
    identity: 43,
    token: "a2",
    display_name: "同行劍士",
    team: "party",
    state: "active",
    hp_current: 60,
    hp_maximum: 100,
    portrait_ref: ALLY,
  },
];

function beat(seq, action, kind, actor, target, extra = {}) {
  return {
    seq,
    action,
    kind,
    actor,
    target,
    amount: null,
    hp_after: null,
    text: `beat ${seq}`,
    ...extra,
  };
}

// Action 0: the player rolls, hits foe 3 twice (a multi-hit), and defeats
// it. Action 1: foe 4 hits the player. Action 2: the ally hits foe 8 (the
// fourth foe still standing, not on the stage). Action 3: foe 4 hits the
// ally.
const BEATS = [
  beat(0, 0, "roll", PLAYER, "3"),
  beat(1, 0, "damage", PLAYER, "3", { amount: 12, hp_after: 18 }),
  beat(2, 0, "damage", PLAYER, "3", { amount: 18, hp_after: 0 }),
  beat(3, 0, "target_defeated", PLAYER, "3"),
  beat(4, 1, "damage", "4", PLAYER, { amount: 9, hp_after: 71 }),
  beat(5, 2, "damage", ALLY, "8", { amount: 5, hp_after: 25 }),
  beat(6, 3, "damage", "4", ALLY, { amount: 4, hp_after: 56 }),
];

function plan(options = {}) {
  return planRound({
    panel: { schema_version: 1, available: true, round: ROUND, beats: options.beats || BEATS },
    roster: ROSTER,
    statusHp: 80,
    playerKey: PLAYER,
    level: options.level || "full",
    startSeq: 3,
    terminal: !!options.terminal,
  });
}

// The state at step `index` in `phase`, driven through the reducer exactly
// as the store drives it.
function at(index, phase, options = {}) {
  let state = beatReducer(null, { type: "start", plan: plan(options) });
  for (let i = 0; i < index; i += 1) {
    state = beatReducer(state, { type: "shown", index: i });
    state = beatReducer(state, { type: "acted" });
    state = beatReducer(state, { type: "paused" });
  }
  if (phase === "act" || phase === "pause") {
    state = beatReducer(state, { type: "shown", index });
  }
  if (phase === "pause") {
    state = beatReducer(state, { type: "acted" });
  }
  expect(state.phase).toBe(phase);
  expect(state.index).toBe(index);
  return state;
}

const refs = (stage) => stage.foes.map((row) => row.portrait_ref);

describe("stageFor (design D3)", () => {
  it("stands the pre-round active foes, in presenter order", () => {
    const stage = stageFor(at(0, "text"));
    expect(refs(stage)).toEqual(["3", "4", "6", "7", "8"]);
    expect(stage.defeated).toEqual([]);
    expect(stage.key).toBe(`${ROUND}:0`);
    expect(stage.step).toBe(0);
  });

  it("plays no gesture while a step's page types", () => {
    expect(stageFor(at(0, "text")).gestures).toEqual({});
    expect(stageFor(at(4, "text")).gestures).toEqual({});
  });

  it("steps the actor on the first beat of each action only", () => {
    expect(stageFor(at(0, "act")).gestures).toEqual({ [PLAYER]: { gesture: "lunge", amount: null } });
    // The same action's later beats: the target reacts, the actor stays.
    expect(stageFor(at(1, "act")).gestures).toEqual({ "3": { gesture: "hit", amount: 12 } });
    // A new action: the foe steps and the player is hit.
    expect(stageFor(at(4, "act")).gestures).toEqual({
      "4": { gesture: "lunge", amount: null },
      [PLAYER]: { gesture: "hit", amount: 9 },
    });
  });

  it("keeps the step's gestures through its pause, so the rising number runs on", () => {
    expect(stageFor(at(1, "pause")).gestures).toEqual({ "3": { gesture: "hit", amount: 12 } });
  });

  it("restarts a gesture on the same figure with each step's key", () => {
    const first = stageFor(at(1, "act"));
    const second = stageFor(at(2, "act"));
    expect(first.gestures["3"].gesture).toBe("hit");
    expect(second.gestures["3"].gesture).toBe("hit");
    expect(second.key).not.toBe(first.key);
  });

  it("drops a foe on its own defeat beat, and it leaves at the next step", () => {
    // Before and during its defeat beat the foe stands; the beat plays
    // `defeat` on it.
    expect(refs(stageFor(at(3, "text")))).toContain("3");
    const acting = stageFor(at(3, "act"));
    expect(acting.gestures).toEqual({ "3": { gesture: "defeat", amount: null } });
    expect(refs(acting)).toContain("3");
    expect(refs(stageFor(at(3, "pause")))).toContain("3");
    // From the next step it is gone, and the next foe steps up.
    const after = stageFor(at(4, "text"));
    expect(after.defeated).toEqual(["3"]);
    expect(refs(after)).toEqual(["4", "6", "7", "8"]);
  });

  it("never plays defeat on the player", () => {
    const beats = [beat(0, 0, "damage", "4", PLAYER, { amount: 80, hp_after: 0 }), beat(1, 0, "target_defeated", "4", PLAYER)];
    expect(stageFor(at(1, "act", { beats })).gestures).toEqual({});
    // The player is no foe, so it never joins the defeated list either.
    expect(stageFor(at(1, "pause", { beats })).defeated).toEqual([]);
  });

  it("animates nobody who has no stage actor: an ally, or a foe beyond the third", () => {
    // The ally's first beat hits the fourth foe still standing: neither
    // stands on the stage.
    expect(stageFor(at(5, "act")).gestures).toEqual({});
    // Foe 4 steps; the ally it hits has no stage actor.
    expect(stageFor(at(6, "act")).gestures).toEqual({ "4": { gesture: "lunge", amount: null } });
  });

  it("gives a key the plan does not know no gesture", () => {
    const beats = [beat(0, 0, "damage", "99", "98", { amount: 3, hp_after: 1 })];
    expect(stageFor(at(0, "act", { beats })).gestures).toEqual({});
  });

  it("is null at off, at the end, and after a skip or a flush", () => {
    expect(stageFor(beatReducer(null, { type: "start", plan: plan({ level: "off" }) }))).toBeNull();
    const playing = at(1, "act");
    expect(stageFor(beatReducer(playing, { type: "skip" }))).toBeNull();
    expect(stageFor(beatReducer(playing, { type: "flush" }))).toBeNull();
    expect(stageFor(null)).toBeNull();
    let state = at(6, "pause");
    state = beatReducer(state, { type: "paused" });
    expect(state.phase).toBe("done");
    expect(stageFor(state)).toBeNull();
  });
});

describe("actMs (design D2)", () => {
  const TOKENS = {
    "--motion-beat-step": 240,
    "--motion-beat-hit": 180,
    "--motion-beat-defeat": 350,
  };
  const read = vi.fn((name) => TOKENS[name] ?? 0);

  it("waits for the longest gesture the step plays", () => {
    expect(actMs(at(0, "act"), read)).toBe(240); // step only
    expect(actMs(at(1, "act"), read)).toBe(180); // hit only
    expect(actMs(at(3, "act"), read)).toBe(350); // defeat only
    expect(actMs(at(4, "act"), read)).toBe(240); // step and hit
    expect(read).toHaveBeenCalledWith(GESTURE_TOKENS.lunge);
    expect(read).toHaveBeenCalledWith(GESTURE_TOKENS.hit);
    expect(read).toHaveBeenCalledWith(GESTURE_TOKENS.defeat);
  });

  it("is 0 for a step that plays no gesture, and for the reduced level's 0ms tokens", () => {
    expect(actMs(at(5, "act"), read)).toBe(0);
    const reduced = (name) => (name === "--motion-beat-defeat" ? 150 : 0);
    expect(actMs(at(4, "act"), reduced)).toBe(0);
    expect(actMs(at(3, "act"), reduced)).toBe(150);
    // An unusable reading never holds anything.
    expect(actMs(at(4, "act"), () => Number.NaN)).toBe(0);
  });
});

describe("beatHoldFor (design D6)", () => {
  it("holds only while a terminal round plays by itself", () => {
    expect(beatHoldFor(at(0, "text", { terminal: true }))).toBe(true);
    expect(beatHoldFor(at(3, "act", { terminal: true }))).toBe(true);
    expect(beatHoldFor(at(0, "text"))).toBe(false);
    expect(beatHoldFor(beatReducer(at(3, "act", { terminal: true }), { type: "skip" }))).toBe(false);
    expect(beatHoldFor(beatReducer(null, { type: "start", plan: plan({ terminal: true, level: "off" }) }))).toBe(
      false,
    );
    expect(beatHoldFor(null)).toBe(false);
  });
});
