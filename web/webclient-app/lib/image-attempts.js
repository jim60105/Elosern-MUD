// image-attempts.js — the shared ordered-attempt image loading state machine.
//
// One pure reducer drives every image surface that resolves several ordered
// candidate resources (gallery editor, figure, avatar, scene, dream). It owns
// the attempt ORDER, reached-only faults, canonical resource-identity
// deduplication and safe exhaustion; it never parses a panel wire shape, never
// selects a business subject and never schedules a retry.
//
// Input is a normalized *internal* load request — the same construction every
// caller builds from whatever committed panel it consumes:
//
//   {
//     subjectId,                       // stable identity of the loaded subject
//     epoch,                           // resolution generation (a new value retires old callbacks)
//     attempts: [                      // ordered candidates, ranked, not index-ordered
//       { type: "image", source_id, rank, resource },
//       { type: "fault", source_id, rank, reason },
//     ],
//     terminal,                        // null, or { kind, source_id, rank, resource }
//   }
//
// `resource` is exactly `{ resource_id, version, url, origin, geometry }`.
// `reason` is a closed backend/browser reason string; browser-owned reasons are
// `image_load_failed` and `image_decode_failed`.
//
// Priority is the stable `rank`, never the attempt-array index: the reducer
// sorts first and only then drops duplicate resources (keeping the
// highest-priority occurrence), so a duplicate resource or terminal can never
// reorder or hide a higher-priority candidate. Resource identity/version is the
// deduplication key; a terminal whose resource key already appears in the
// attempts is not appended again.
//
// The machine walks forward exactly once per resolution: fault entries are
// recorded as *reached* and skipped; image entries either resolve to a load
// action, are reused from a known/provisional outcome, wait for a provisional
// source still loading, or exhaust. There is no recursion and no infinite
// fallback, and exhaustion always terminates with the reached faults attached.
//
// Two outcome stores feed resolution, both epoch-scoped and keyed by resource
// identity/version:
//   * `known`     — durable outcomes this driver already observed; a known
//                   success is reused for every later re-resolution without a
//                   new request (geometry-only updates), a known failure keeps
//                   its reached fault.
//   * `provisional` — a caller-supplied one-shot handoff for a source whose
//                   outcome is already known (a healthy preferred source still
//                   loading, or a lower source that already failed): a reached
//                   provisional outcome is consumed once.
// A stale epoch is ignored, so a superseded resolution can never overwrite or
// leak into the current one.

export const LOAD_PHASE = Object.freeze({
  loading: "loading",
  success: "success",
  exhausted: "exhausted",
});

export const IMAGE_LOAD_FAILED = "image_load_failed";
export const IMAGE_DECODE_FAILED = "image_decode_failed";

const MAX_RANK = Number.MAX_SAFE_INTEGER;

function rankOf(value) {
  return Number.isFinite(value) ? Number(value) : MAX_RANK;
}

function epochOf(value) {
  return value && typeof value === "object" && "epoch" in value ? value.epoch : null;
}

// Canonical identity/version key for a resource. Two facts about the same
// bytes share one key regardless of their rank or source.
export function resourceKey(resource) {
  if (!resource || typeof resource !== "object") {
    return null;
  }
  return `${resource.resource_id ?? ""}@${resource.version ?? ""}`;
}

function isLoadable(resource) {
  return !!resource && typeof resource === "object" && typeof resource.url === "string" && resource.url.length > 0;
}

// The ranked, deduplicated resolution order. Rank decides priority; ties keep
// declaration order (Array.prototype.sort is stable). Duplicate resources are
// collapsed after ranking, so the highest-priority occurrence survives.
export function canonicalOrder(request) {
  const entries = [];
  const attempts = Array.isArray(request?.attempts) ? request.attempts : [];
  for (const attempt of attempts) {
    if (!attempt || typeof attempt !== "object") {
      continue;
    }
    if (attempt.type === "fault") {
      if (typeof attempt.source_id !== "string" || typeof attempt.reason !== "string") {
        continue;
      }
      entries.push({
        kind: "fault",
        sourceId: attempt.source_id,
        rank: rankOf(attempt.rank),
        reason: attempt.reason,
      });
    } else if (attempt.type === "image" && isLoadable(attempt.resource)) {
      entries.push({
        kind: "image",
        sourceId: attempt.source_id,
        rank: rankOf(attempt.rank),
        key: resourceKey(attempt.resource),
        resource: attempt.resource,
        terminal: null,
      });
    }
  }
  const terminal = request?.terminal;
  if (terminal && typeof terminal === "object" && isLoadable(terminal.resource)) {
    entries.push({
      kind: "image",
      sourceId: terminal.source_id,
      rank: rankOf(terminal.rank),
      key: resourceKey(terminal.resource),
      resource: terminal.resource,
      terminal: typeof terminal.kind === "string" ? terminal.kind : null,
    });
  }
  entries.sort((left, right) => left.rank - right.rank);
  const seen = new Set();
  const order = [];
  for (const entry of entries) {
    if (entry.kind === "image") {
      if (seen.has(entry.key)) {
        continue;
      }
      seen.add(entry.key);
    }
    order.push(entry);
  }
  return order;
}

// Reached faults deduplicate by source/reason (a backend fact and a browser
// observation of the same source never double-report), keeping first-reached
// order and distinct reasons.
function appendFault(list, sourceId, rank, reason) {
  if (list.some((fault) => fault.sourceId === sourceId && fault.reason === reason)) {
    return list;
  }
  return [...list, { sourceId, rank, reason }];
}

function epochScoped(store, epoch) {
  const scoped = new Map();
  if (!store) {
    return scoped;
  }
  const entries = store instanceof Map ? store.entries() : Object.entries(store);
  for (const [key, value] of entries) {
    if (value && typeof value === "object" && value.epoch === epoch) {
      scoped.set(key, value);
    }
  }
  return scoped;
}

function selectedFrom(entry, dimensions) {
  return {
    sourceId: entry.sourceId,
    rank: entry.rank,
    key: entry.key,
    resourceId: entry.resource?.resource_id ?? null,
    version: entry.resource?.version ?? null,
    url: entry.resource?.url ?? null,
    terminal: entry.terminal ?? null,
    geometry: entry.resource?.geometry ?? null,
    dimensions,
  };
}

// Fresh machine for one normalized request.
export function createLoadState(request, { known = null, provisional = null } = {}) {
  const order = canonicalOrder(request);
  const epoch = request?.epoch ?? null;
  return {
    subjectId: request?.subjectId ?? null,
    epoch,
    order,
    cursor: 0,
    phase: order.length ? LOAD_PHASE.loading : LOAD_PHASE.exhausted,
    selected: null,
    reachedFaults: [],
    exhausted: order.length === 0,
    known: epochScoped(known, epoch),
    provisional: epochScoped(provisional, epoch),
  };
}

// Replace the state's provisional store from a fresh caller-supplied map,
// keeping only the current epoch. Used when a waiting provisional source
// changes without re-issuing the resolution.
export function withProvisional(state, provisional) {
  return { ...state, provisional: epochScoped(provisional, state.epoch) };
}

// Record one durable observed outcome for a resource key.
export function withKnown(state, key, outcome) {
  const known = new Map(state.known);
  known.set(key, { epoch: state.epoch, ...outcome });
  return { ...state, known };
}

// Advance to the next resolution step. Returns `{ state, action }` where the
// action is one of:
//   { type: "load", key, sourceId, rank, resource }  — the caller loads it
//   { type: "wait", key, sourceId, rank }            — a provisional source is
//                                                      still loading
//   { type: "reuse", key, sourceId, rank, selected } — already-resolved bytes
//   { type: "done" }                                 — exhausted
export function resolve(state) {
  let cursor = state.cursor;
  let reachedFaults = state.reachedFaults;
  const provisional = new Map(state.provisional);
  const known = state.known;
  while (cursor < state.order.length) {
    const entry = state.order[cursor];
    if (entry.kind === "fault") {
      reachedFaults = appendFault(reachedFaults, entry.sourceId, entry.rank, entry.reason);
      cursor += 1;
      continue;
    }
    const provisionalOutcome = provisional.get(entry.key);
    if (provisionalOutcome?.phase === LOAD_PHASE.loading) {
      return {
        state: { ...state, cursor, reachedFaults, provisional, phase: LOAD_PHASE.loading, selected: null },
        action: { type: "wait", key: entry.key, sourceId: entry.sourceId, rank: entry.rank },
      };
    }
    if (provisionalOutcome?.phase === "failed") {
      provisional.delete(entry.key);
      reachedFaults = appendFault(
        reachedFaults,
        entry.sourceId,
        entry.rank,
        provisionalOutcome.reason || IMAGE_LOAD_FAILED,
      );
      cursor += 1;
      continue;
    }
    if (provisionalOutcome?.phase === LOAD_PHASE.success) {
      provisional.delete(entry.key);
      const selected = selectedFrom(entry, provisionalOutcome.dimensions ?? null);
      return {
        state: { ...state, cursor, reachedFaults, provisional, phase: LOAD_PHASE.success, selected },
        action: { type: "reuse", key: entry.key, sourceId: entry.sourceId, rank: entry.rank, selected },
      };
    }
    const knownOutcome = known.get(entry.key);
    if (knownOutcome?.phase === LOAD_PHASE.success) {
      const selected = selectedFrom(entry, knownOutcome.dimensions ?? null);
      return {
        state: { ...state, cursor, reachedFaults, provisional, phase: LOAD_PHASE.success, selected },
        action: { type: "reuse", key: entry.key, sourceId: entry.sourceId, rank: entry.rank, selected },
      };
    }
    if (knownOutcome?.phase === "failed") {
      reachedFaults = appendFault(
        reachedFaults,
        entry.sourceId,
        entry.rank,
        knownOutcome.reason || IMAGE_LOAD_FAILED,
      );
      cursor += 1;
      continue;
    }
    return {
      state: { ...state, cursor, reachedFaults, provisional, phase: LOAD_PHASE.loading },
      action: { type: "load", key: entry.key, sourceId: entry.sourceId, rank: entry.rank, resource: entry.resource },
    };
  }
  return {
    state: {
      ...state,
      cursor,
      reachedFaults,
      provisional,
      phase: LOAD_PHASE.exhausted,
      selected: null,
      exhausted: true,
    },
    action: { type: "done" },
  };
}

// A successful load for the entry at the cursor. A stale epoch or a key that
// no longer matches the in-flight entry is ignored.
export function observeSuccess(state, { epoch, key, dimensions }) {
  if (state.epoch !== epoch) {
    return state;
  }
  const entry = state.order[state.cursor];
  if (!entry || entry.kind !== "image" || entry.key !== key) {
    return state;
  }
  return {
    ...state,
    cursor: state.cursor + 1,
    phase: LOAD_PHASE.success,
    selected: selectedFrom(entry, dimensions ?? null),
  };
}

// A failed load/decode for the entry at the cursor: recorded as a reached
// fault and stepped past. A stale epoch or mismatched key is ignored.
export function observeFailure(state, { epoch, key, reason }) {
  if (state.epoch !== epoch) {
    return state;
  }
  const entry = state.order[state.cursor];
  if (!entry || entry.kind !== "image" || entry.key !== key) {
    return state;
  }
  return {
    ...state,
    cursor: state.cursor + 1,
    reachedFaults: appendFault(state.reachedFaults, entry.sourceId, entry.rank, reason || IMAGE_LOAD_FAILED),
  };
}

// The ordered resolution facts that define *which* attempt order applies. Byte
// geometry is deliberately excluded: a geometry-only revision keeps the same
// facts and therefore never restarts resolution.
export function resolutionFacts(request) {
  return canonicalOrder(request).map((entry) => (
    entry.kind === "fault"
      ? ["fault", entry.sourceId, entry.rank, entry.reason]
      : ["image", entry.sourceId, entry.rank, entry.key, entry.terminal]
  ));
}

// The ordered resource keys that define *which bytes* the resolution needs.
export function resourceKeys(request) {
  return canonicalOrder(request).map((entry) => (entry.kind === "image" ? entry.key : null));
}
