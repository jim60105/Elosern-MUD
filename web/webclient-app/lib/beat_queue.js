// The combat beat queue: the one pure plan, state machine, and page model for
// playing a settled combat round one beat at a time (docs/superpowers/specs/
// 2026-09-23-webclient-avg-stage-redesign-design.md §10.2, "Beat queue (C13b)";
// OpenSpec change webclient-combat-beat-queue, design D3/D4/D6).
//
// The input is committed data only: C12's `combat_beats` panel (the round id
// and the beats `{seq, action, kind, actor, target, amount, hp_after, text}`
// whose `action` is the 0-based ordinal of the source EventLog), the
// pre-publication roster and hit points, and the player's committed catalog
// key. Nothing here parses narrative prose: the tail rule counts the
// response's `out` blocks, it never reads their text.
//
// No Vue, no DOM, no side effects: the store applies the reducer, the message
// window pages the blocks.
import { paginate } from "./message_pages.js";

// `known` is the design's identity test: the key is the player's own catalog
// key or one of the roster's `portrait_ref`s (the combat panel's
// `portrait_ref` is the same decimal key as its `identity`, C12 D6).
// `values` is the pre-round hit points of those same keys, where the panel
// carries one. A step's HP is displayed only when its target has such a
// value; whether it does is recorded on the step, never re-derived later.
function knownKeys(roster, playerKey) {
  const known = new Set();
  if (playerKey != null) {
    known.add(String(playerKey));
  }
  for (const row of Array.isArray(roster) ? roster : []) {
    if (row && row.portrait_ref != null) {
      known.add(String(row.portrait_ref));
    }
  }
  return known;
}

function preRoundHp(roster, statusHp, playerKey, known) {
  const values = new Map();
  if (playerKey != null && known.has(String(playerKey)) && typeof statusHp === "number") {
    values.set(String(playerKey), statusHp);
  }
  for (const row of Array.isArray(roster) ? roster : []) {
    if (!row || row.portrait_ref == null || typeof row.hp_current !== "number") {
      continue;
    }
    values.set(String(row.portrait_ref), row.hp_current);
  }
  return values;
}

// D3: map one committed panel to the round's plan. Returns null when the
// publication carries no available panel (the fallback case), so a caller can
// treat "no plan" as "page this round as an ordinary response".
export function planRound({ panel, roster, statusHp, playerKey, level, startSeq, terminal }) {
  if (!panel || panel.available !== true || !Array.isArray(panel.beats)) {
    return null;
  }
  const known = knownKeys(roster, playerKey);
  const values = preRoundHp(roster, statusHp, playerKey, known);

  const steps = [];
  let previousAction = null;
  let coveredLines = 0;
  for (const beat of panel.beats) {
    if (!beat || typeof beat.seq !== "number") {
      continue;
    }
    const action = typeof beat.action === "number" ? beat.action : 0;
    const target = beat.target == null ? null : String(beat.target);
    const actor = beat.actor == null ? null : String(beat.actor);
    // The panel validator guarantees contiguous `seq` and non-decreasing
    // `action`, so this comparison is the action grouping; `firstOfAction` is
    // the hook a later change reads to start a new action's gestures.
    const firstOfAction = previousAction === null || action !== previousAction;
    previousAction = action;
    coveredLines = Math.max(coveredLines, action + 1);
    const hpAfter = typeof beat.hp_after === "number" ? beat.hp_after : null;
    const affectsHp = beat.kind === "damage" && target !== null && values.has(target);
    steps.push({
      seq: beat.seq,
      action,
      kind: typeof beat.kind === "string" ? beat.kind : "other",
      actor,
      target,
      amount: typeof beat.amount === "number" ? beat.amount : null,
      hpAfter,
      text: beat.text == null ? "" : String(beat.text),
      firstOfAction,
      actorKnown: actor !== null && known.has(actor),
      targetKnown: target !== null && known.has(target),
      affectsHp,
    });
  }

  // Only a damaged participant with a known pre-round value carries a
  // displayed value: every other key follows the committed state (D3).
  const hpStart = {};
  for (const step of steps) {
    if (step.affectsHp) {
      hpStart[step.target] = values.get(step.target);
    }
  }

  return {
    round: typeof panel.round === "string" ? panel.round : "",
    startSeq: typeof startSeq === "number" ? startSeq : null,
    terminal: !!terminal,
    // `off` never waits, so it never plays by itself (D2's 0ms token, D4's
    // start-at-done rule).
    auto: level !== "off",
    steps,
    coveredLines,
    hpStart,
  };
}

// How many steps' hit points are in effect: the step being shown applies its
// HP once it is fully shown (`shown`), so the pause phase has applied it.
function appliedCount(state) {
  if (state.phase === "pause") {
    return state.index + 1;
  }
  return state.index;
}

// D4: the state machine. `state` is `{plan, index, phase}` with
// `phase ∈ {text, pause, done}`, or null for "no round". No event throws and
// no event moves a state backwards, so a late timer or a double click cannot
// corrupt it.
export function beatReducer(state, event) {
  const type = event ? event.type : null;
  if (type === "start") {
    const plan = event.plan;
    if (!plan || !Array.isArray(plan.steps)) {
      return null;
    }
    // `off` is done at once, and so is a round with nothing to step: its
    // pages remain for the reader, but nothing plays and nothing locks.
    if (plan.steps.length === 0 || !plan.auto) {
      return { plan, index: 0, phase: "done" };
    }
    return { plan, index: 0, phase: "text" };
  }
  if (type === "reset") {
    return null;
  }
  if (!state) {
    return state;
  }
  if (type === "skip" || type === "flush") {
    return state.phase === "done" ? state : { ...state, phase: "done" };
  }
  if (type === "shown") {
    // A stale `shown(i)` for a beat that is no longer current is ignored.
    if (state.phase !== "text" || event.index !== state.index) {
      return state;
    }
    return { ...state, phase: "pause" };
  }
  if (type === "paused") {
    if (state.phase !== "pause") {
      return state;
    }
    const next = state.index + 1;
    return next < state.plan.steps.length
      ? { ...state, index: next, phase: "text" }
      : { ...state, phase: "done" };
  }
  return state;
}

// D3: the hit points each damaged participant displays. Null once the
// presentation has ended, so every surface snaps to the committed values.
export function displayHpFor(state) {
  if (!state || state.phase === "done") {
    return null;
  }
  const { plan } = state;
  const applied = appliedCount(state);
  const displayed = {};
  for (const key of Object.keys(plan.hpStart)) {
    displayed[key] = plan.hpStart[key];
  }
  for (let i = 0; i < applied; i += 1) {
    const step = plan.steps[i];
    if (step.affectsHp) {
      displayed[step.target] = step.hpAfter;
    }
  }
  return displayed;
}

// D6: one plain-text `out` block per beat. The token stream is built directly
// and the block is marked as prose, so beat text is never parsed as markup and
// is never treated as box-drawing art.
//
// Accepts the plan, a bare list of steps, or a bare list of beat texts (the
// message window holds the published `texts`).
export function beatBlocks(plan) {
  const source = Array.isArray(plan) ? plan : plan && Array.isArray(plan.steps) ? plan.steps : [];
  return source.map((step) => {
    const text =
      typeof step === "string" ? step : step && step.text != null ? String(step.text) : "";
    return {
      kind: "out",
      seq: null,
      text,
      tokens: [{ kind: "text", value: text }],
      mapArt: false,
    };
  });
}

// D6: a response's blocks after its first `coveredLines` `out` blocks. Only
// the count is read, never the text; later `sys`/`err` blocks and later `out`
// blocks (a fight's outcome, its aftermath) are kept.
export function tailBlocks(blocks, coveredLines) {
  const list = Array.isArray(blocks) ? blocks : [];
  const drop = typeof coveredLines === "number" && coveredLines > 0 ? Math.floor(coveredLines) : 0;
  const tail = [];
  let seen = 0;
  for (const block of list) {
    if (block && block.kind === "out" && seen < drop) {
      seen += 1;
      continue;
    }
    tail.push(block);
  }
  return tail;
}

// D6: the rounds's page list — each beat paginated alone (a beat is one page
// unless it does not fit) followed by the tail's pages. `fits` is the caller's
// measured fit predicate; each returned page carries the beat ordinal it
// belongs to (`beat`), and the tail's pages carry none.
export function beatPages(texts, tail, fits) {
  const pages = [];
  const beatStarts = [];
  const blocks = beatBlocks(Array.isArray(texts) ? texts : []);
  for (let i = 0; i < blocks.length; i += 1) {
    beatStarts.push(pages.length);
    for (const page of paginate([blocks[i]], fits)) {
      pages.push({ ...page, beat: i });
    }
  }
  const tailStart = pages.length;
  for (const page of paginate(tail, fits)) {
    pages.push(page);
  }
  return { pages, beatStarts, tailStart };
}
