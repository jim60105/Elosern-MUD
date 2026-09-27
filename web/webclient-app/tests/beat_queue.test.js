// webclient-combat-beat-queue (design D3/D4/D6/D9): the pure beat queue —
// the plan built from one committed `combat_beats` panel, the state machine,
// the displayed hit points, and the block/page model. No Vue, no DOM: the
// module is exercised directly.
import { describe, expect, it } from "vitest";

import {
  beatBlocks,
  beatPages,
  beatReducer,
  displayHpFor,
  planRound,
  tailBlocks,
} from "../lib/beat_queue.js";

// The panel the protocol validator admits: contiguous `seq`, non-decreasing
// `action`, `amount`/`hp_after` only on damage beats.
function panel(beats, overrides = undefined) {
  return { schema_version: 1, available: true, round: "s-1/1", beats, ...overrides };
}

const ROLL = {
  seq: 0,
  action: 0,
  kind: "roll",
  actor: "42",
  target: "3",
  amount: null,
  hp_after: null,
  text: "你擲出了骰子。",
};
const HIT = {
  seq: 1,
  action: 1,
  kind: "damage",
  actor: "42",
  target: "3",
  amount: 12,
  hp_after: 18,
  text: "你擊中了灰袍盜賊。",
};
const HIT_AGAIN = {
  seq: 2,
  action: 2,
  kind: "damage",
  actor: "42",
  target: "3",
  amount: 18,
  hp_after: 0,
  text: "灰袍盜賊的傷勢加重了。",
};
const DEFEAT = {
  seq: 3,
  action: 3,
  kind: "target_defeated",
  actor: "42",
  target: "3",
  amount: null,
  hp_after: null,
  text: "灰袍盜賊倒下了。",
};

// The shipped panel row vocabulary: `portrait_ref` is the same decimal key as
// the row's `identity` (C12 D6).
const ROSTER = [
  {
    identity: 3,
    token: "e1",
    display_name: "灰袍盜賊",
    team: "foes",
    state: "active",
    hp_current: 30,
    hp_maximum: 30,
    portrait_ref: "3",
  },
  {
    identity: 42,
    token: "a1",
    display_name: "影行者",
    team: "party",
    state: "active",
    hp_current: 80,
    hp_maximum: 100,
    portrait_ref: "42",
  },
];

const PLAYER = "42";

function plan(overrides = undefined, options = undefined) {
  return planRound({
    panel: panel([ROLL, HIT, HIT_AGAIN, DEFEAT], overrides),
    roster: ROSTER,
    statusHp: 80,
    playerKey: PLAYER,
    level: "full",
    startSeq: 7,
    terminal: false,
    ...options,
  });
}

// Drive the state machine the way the store does: start, then shown/paused
// until it settles.
function stepTo(state, event) {
  return beatReducer(state, event);
}

describe("planRound (design D3)", () => {
  it("maps the beats in seq order and flags the first beat of each action group", () => {
    const planned = plan();
    expect(planned.steps.map((step) => step.seq)).toEqual([0, 1, 2, 3]);
    // One action group per beat here, so every step opens its group.
    expect(planned.steps.map((step) => step.firstOfAction)).toEqual([true, true, true, true]);
    expect(planned.round).toBe("s-1/1");
    expect(planned.startSeq).toBe(7);
    expect(planned.terminal).toBe(false);
    expect(planned.auto).toBe(true);
  });

  it("flags only the first beat of a multi-beat action group", () => {
    const second = {
      seq: 1,
      action: 0,
      kind: "other",
      actor: "42",
      target: null,
      amount: null,
      hp_after: null,
      text: "同一行動的第二個事件。",
    };
    const planned = plan(undefined, { panel: panel([ROLL, second, HIT]) });
    expect(planned.steps.map((step) => step.firstOfAction)).toEqual([true, false, true]);
  });

  it("covers the response's first max(action) + 1 out lines", () => {
    expect(plan().coveredLines).toBe(4);
    expect(plan(undefined, { panel: panel([]) }).coveredLines).toBe(0);
  });

  it("builds each damaged participant's pre-round hit points from the roster and the status", () => {
    // The player takes a hit too: their pre-round value is the committed
    // `status` value, the roster row's `hp_current` is the participant's.
    const onPlayer = { ...HIT, target: PLAYER, hp_after: 62 };
    const planned = plan(undefined, { panel: panel([onPlayer, HIT]) });
    expect(planned.hpStart).toEqual({ "42": 80, "3": 30 });
  });

  it("keeps an undamaged participant out of the displayed set", () => {
    expect(Object.keys(plan().hpStart)).toEqual(["3"]);
  });

  it("leaves an unknown participant as a text-only step", () => {
    const unknown = { ...HIT, target: "999", hp_after: 4 };
    const planned = plan(undefined, { panel: panel([unknown]) });
    const step = planned.steps[0];
    expect(step.targetKnown).toBe(false);
    expect(step.affectsHp).toBe(false);
    expect(planned.hpStart).toEqual({});
    // Its text still pages: the block list has the beat.
    expect(beatBlocks(planned).map((block) => block.text)).toEqual(["你擊中了灰袍盜賊。"]);
  });

  it("leaves a damage beat with no known pre-round value text-only", () => {
    const planned = plan(undefined, { panel: panel([HIT]), roster: [], statusHp: null, playerKey: null });
    expect(planned.steps[0].targetKnown).toBe(false);
    expect(planned.steps[0].affectsHp).toBe(false);
    expect(displayHpFor(beatReducer(null, { type: "start", plan: planned }))).toEqual({});
  });

  it("marks known participants by the player's key and each roster portrait_ref", () => {
    const planned = plan();
    expect(planned.steps[0].actorKnown).toBe(true);
    expect(planned.steps[0].targetKnown).toBe(true);
  });

  it("never plays at off, and returns null for the unavailable form", () => {
    expect(plan(undefined, { level: "off" }).auto).toBe(false);
    expect(planRound({ panel: { schema_version: 1, available: false, reason: null }, roster: [], statusHp: null, playerKey: null, level: "full", startSeq: 1, terminal: false })).toBeNull();
    expect(planRound({ panel: null, roster: [], statusHp: null, playerKey: null, level: "full", startSeq: 1, terminal: false })).toBeNull();
  });

  it("keeps the plan pure: repeated calls agree", () => {
    expect(plan()).toEqual(plan());
  });
});

describe("beatReducer (design D4)", () => {
  it("starts at the first beat in the text phase", () => {
    const state = beatReducer(null, { type: "start", plan: plan() });
    expect(state.index).toBe(0);
    expect(state.phase).toBe("text");
  });

  it("starts done at off", () => {
    const state = beatReducer(null, { type: "start", plan: plan(undefined, { level: "off" }) });
    expect(state.phase).toBe("done");
    expect(state.index).toBe(0);
  });

  it("starts done for a round with no beats", () => {
    const state = beatReducer(null, { type: "start", plan: plan(undefined, { panel: panel([]) }) });
    expect(state.phase).toBe("done");
  });

  it("has no round when there is no plan to start", () => {
    expect(beatReducer(null, { type: "start", plan: null })).toBeNull();
  });

  it("walks text -> act -> pause -> next text and ends done after the last beat", () => {
    let state = beatReducer(null, { type: "start", plan: plan() });
    for (let index = 0; index < 4; index += 1) {
      expect(state.phase).toBe("text");
      expect(state.index).toBe(index);
      state = stepTo(state, { type: "shown", index });
      // The step's stage gesture plays before its pause
      // (webclient-combat-beat-choreography D2).
      expect(state.phase).toBe("act");
      state = stepTo(state, { type: "acted" });
      expect(state.phase).toBe("pause");
      state = stepTo(state, { type: "paused" });
    }
    expect(state.phase).toBe("done");
    expect(state.index).toBe(3);
  });

  it("ignores a stale or out-of-order shown", () => {
    const state = beatReducer(null, { type: "start", plan: plan() });
    expect(stepTo(state, { type: "shown", index: 2 })).toBe(state);
    const acting = stepTo(state, { type: "shown", index: 0 });
    expect(acting.phase).toBe("act");
    // A second shown for the same beat, a paused while acting, and an acted
    // or a paused while not in that phase.
    expect(stepTo(acting, { type: "shown", index: 0 })).toBe(acting);
    expect(stepTo(acting, { type: "paused" })).toBe(acting);
    expect(stepTo(state, { type: "acted" })).toBe(state);
    expect(stepTo(state, { type: "paused" })).toBe(state);
    const paused = stepTo(acting, { type: "acted" });
    expect(paused.phase).toBe("pause");
    expect(stepTo(paused, { type: "acted" })).toBe(paused);
  });

  it("skips and flushes from every phase and is idempotent", () => {
    const phases = [
      beatReducer(null, { type: "start", plan: plan() }), // text
      beatReducer(beatReducer(null, { type: "start", plan: plan() }), { type: "shown", index: 0 }), // act
      beatReducer(beatReducer(beatReducer(null, { type: "start", plan: plan() }), { type: "shown", index: 0 }), {
        type: "acted",
      }), // pause
      beatReducer(null, { type: "start", plan: plan(undefined, { level: "off" }) }), // done
    ];
    for (const state of phases) {
      for (const type of ["skip", "flush"]) {
        const done = beatReducer(state, { type });
        expect(done.phase).toBe("done");
        expect(beatReducer(done, { type })).toBe(done);
      }
    }
  });

  it("resets to no round from any phase", () => {
    const state = beatReducer(null, { type: "start", plan: plan() });
    expect(beatReducer(state, { type: "reset" })).toBeNull();
    expect(beatReducer(null, { type: "reset" })).toBeNull();
  });

  it("never throws and never moves on an unknown event", () => {
    const state = beatReducer(null, { type: "start", plan: plan() });
    expect(beatReducer(state, { type: "wat" })).toBe(state);
    expect(beatReducer(state, null)).toBe(state);
    expect(beatReducer(null, { type: "paused" })).toBeNull();
  });
});

describe("displayHpFor (design D3)", () => {
  it("shows the pre-round value until the target's first damage beat, then each hp_after", () => {
    let state = beatReducer(null, { type: "start", plan: plan() });
    expect(displayHpFor(state)).toEqual({ "3": 30 });
    state = beatReducer(state, { type: "shown", index: 0 }); // roll: no damage
    expect(displayHpFor(state)).toEqual({ "3": 30 });
    state = beatReducer(state, { type: "acted" });
    state = beatReducer(state, { type: "paused" });
    expect(displayHpFor(state)).toEqual({ "3": 30 });
    // The damage applies as its act starts (webclient-combat-beat-
    // choreography D2), so the gauge and the fill move with the shake.
    state = beatReducer(state, { type: "shown", index: 1 }); // 30 -> 18
    expect(state.phase).toBe("act");
    expect(displayHpFor(state)).toEqual({ "3": 18 });
    state = beatReducer(state, { type: "acted" });
    expect(displayHpFor(state)).toEqual({ "3": 18 });
    state = beatReducer(state, { type: "paused" });
    expect(displayHpFor(state)).toEqual({ "3": 18 });
    state = beatReducer(state, { type: "shown", index: 2 }); // 18 -> 0
    expect(displayHpFor(state)).toEqual({ "3": 0 });
  });

  it("is null once the presentation has ended, so every surface snaps to committed values", () => {
    const playing = beatReducer(null, { type: "start", plan: plan() });
    expect(displayHpFor(beatReducer(playing, { type: "skip" }))).toBeNull();
    expect(displayHpFor(beatReducer(playing, { type: "flush" }))).toBeNull();
    expect(displayHpFor(null)).toBeNull();
  });

  it("carries no heals, markers, or other resources", () => {
    const heal = {
      seq: 0,
      action: 0,
      kind: "other",
      actor: "42",
      target: PLAYER,
      amount: null,
      hp_after: null,
      text: "你恢復了。",
    };
    const planned = plan(undefined, { panel: panel([heal]) });
    const state = beatReducer(null, { type: "start", plan: planned });
    expect(state.phase).toBe("text");
    expect(displayHpFor(state)).toEqual({});
  });
});

describe("beatBlocks (design D6)", () => {
  it("emits one plain-text out block per beat", () => {
    const blocks = beatBlocks(plan());
    expect(blocks).toHaveLength(4);
    expect(blocks.every((block) => block.kind === "out")).toBe(true);
    expect(blocks.map((block) => block.text)).toEqual([
      "你擲出了骰子。",
      "你擊中了灰袍盜賊。",
      "灰袍盜賊的傷勢加重了。",
      "灰袍盜賊倒下了。",
    ]);
  });

  it("never tokenizes markup: a beat holding <b> renders literally", () => {
    const markup = { ...ROLL, text: "<b>粗體</b> 不是標記 &amp; 也一樣" };
    const [block] = beatBlocks(plan(undefined, { panel: panel([markup]) }));
    expect(block.tokens).toEqual([{ kind: "text", value: "<b>粗體</b> 不是標記 &amp; 也一樣" }]);
  });

  it("keeps box-drawing characters out of the map-art treatment", () => {
    const art = { ...ROLL, text: "──────" };
    const [block] = beatBlocks(plan(undefined, { panel: panel([art]) }));
    expect(block.mapArt).toBe(false);
  });

  it("accepts a bare list of beat texts (the published slice)", () => {
    expect(beatBlocks(["甲", "乙"]).map((block) => block.text)).toEqual(["甲", "乙"]);
  });
});

describe("tailBlocks (design D6)", () => {
  const blocks = [
    { kind: "out", text: "第一條戰報。" },
    { kind: "out", text: "第二條戰報。" },
    { kind: "sys", text: "系統提示。" },
    { kind: "out", text: "行動完成，繼續戰鬥。" },
    { kind: "err", text: "後續錯誤。" },
  ];

  it("drops exactly the first N out blocks and keeps every later block", () => {
    expect(tailBlocks(blocks, 2).map((block) => block.text)).toEqual([
      "系統提示。",
      "行動完成，繼續戰鬥。",
      "後續錯誤。",
    ]);
  });

  it("keeps a sys or err block that sits inside the covered range", () => {
    // A `sys` block between two covered `out` blocks is not one of the
    // covered lines: only the first three `out` blocks drop.
    const mixed = [
      { kind: "out", text: "第一條戰報。" },
      { kind: "sys", text: "系統提示。" },
      { kind: "out", text: "第二條戰報。" },
      { kind: "out", text: "行動完成，繼續戰鬥。" },
      { kind: "err", text: "後續錯誤。" },
    ];
    expect(tailBlocks(mixed, 3).map((block) => block.text)).toEqual([
      "系統提示。",
      "後續錯誤。",
    ]);
  });

  it("returns the whole list for zero coverage and an empty tail for over-coverage", () => {
    expect(tailBlocks(blocks, 0)).toEqual(blocks);
    expect(tailBlocks(blocks, 99)).toEqual([{ kind: "sys", text: "系統提示。" }, { kind: "err", text: "後續錯誤。" }]);
    expect(tailBlocks(null, 2)).toEqual([]);
  });
});

describe("beatPages (design D6)", () => {
  // A code-point fit: each page holds at most `budget` code points.
  const fit = (budget) => (fragments) =>
    fragments.reduce((sum, fragment) => sum + (fragment.end - fragment.start), 0) <= budget;

  // The text a page renders: `paginate` returns token fragments, not lines.
  const pageText = (page) =>
    page.blocks
      .map((fragment) => (fragment.tokens || []).map((token) => token.value || "").join(""))
      .join("");

  it("paginates each beat alone, then the tail, and names every beat's first page", () => {
    const texts = ["一二三四五。", "六七八九十。"];
    const tail = [{ kind: "out", text: "行動完成。" }];
    const layout = beatPages(texts, tail, fit(10));
    expect(layout.beatStarts).toEqual([0, 1]);
    expect(layout.tailStart).toBe(2);
    expect(layout.pages.map((page) => page.beat)).toEqual([0, 1, undefined]);
    expect(layout.pages.map(pageText)).toEqual(["一二三四五。", "六七八九十。", "行動完成。"]);
  });

  it("splits a beat that does not fit one page and keeps both pages on that beat", () => {
    const texts = ["一二三四五。六七八九十。"];
    const layout = beatPages(texts, [], fit(5));
    expect(layout.beatStarts).toEqual([0]);
    expect(layout.pages.length).toBeGreaterThan(1);
    expect(layout.pages.every((page) => page.beat === 0)).toBe(true);
    expect(pageText(layout.pages[0])).toBe("一二三四五");
    expect(layout.tailStart).toBe(layout.pages.length);
  });
});
