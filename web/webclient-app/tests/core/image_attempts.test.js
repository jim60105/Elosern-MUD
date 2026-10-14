// Synthetic mechanism tests for the shared ordered-attempt reducer
// (change unified-image-loading-core). Inputs and expected outcomes are
// independent of the production face editor: the request here is the
// normalized internal load request, never a panel wire shape.
import { describe, expect, it } from "vitest";
import {
  IMAGE_LOAD_FAILED,
  LOAD_PHASE,
  canonicalOrder,
  createLoadState,
  observeFailure,
  observeSuccess,
  resolutionFacts,
  resolve,
  resourceKey,
} from "../../lib/image-attempts.js";

const resource = (id, version, url = `/art/${id}.webp`) => ({
  resource_id: id,
  version,
  url,
  origin: "runtime",
  geometry: { face_rect: null, image_size: null },
});
const image = (sourceId, rank, res) => ({ type: "image", source_id: sourceId, rank, resource: res });
const fault = (sourceId, rank, reason) => ({ type: "fault", source_id: sourceId, rank, reason });

const A = resource("a", "v1");
const B = resource("b", "v1");
const C = resource("c", "v1");

// Drive the machine with a per-key outcome map. Returns the resting point:
// `success` (with the selected resource), `wait`, or `exhausted`.
function drive(state, outcomes) {
  let current = state;
  for (let guard = 0; guard < 32; guard++) {
    const step = resolve(current);
    current = step.state;
    if (step.action.type === "reuse" || step.action.type === "wait" || step.action.type === "done") {
      return { state: current, action: step.action, selected: step.state.selected };
    }
    const outcome = outcomes[step.action.key];
    if (!outcome || outcome.phase === LOAD_PHASE.loading) {
      return { state: current, action: step.action };
    }
    if (outcome.phase === LOAD_PHASE.success) {
      const settled = observeSuccess(current, {
        epoch: current.epoch,
        key: step.action.key,
        dimensions: outcome.dimensions,
      });
      return { state: settled, action: step.action, selected: settled.selected };
    }
    current = observeFailure(current, {
      epoch: current.epoch,
      key: step.action.key,
      reason: outcome.reason ?? IMAGE_LOAD_FAILED,
    });
  }
  throw new Error("resolution did not converge");
}

const request = (attempts, extras = {}) => ({ subjectId: "subject", epoch: 1, attempts, terminal: null, ...extras });

describe("canonical attempt order", () => {
  it("orders by rank, never by array index", () => {
    const order = canonicalOrder(request([image("low", 40, C), image("high", 10, A), image("mid", 20, B)]));
    expect(order.map((entry) => entry.sourceId)).toEqual(["high", "mid", "low"]);
  });

  it("deduplicates a duplicate resource after ranking, keeping the highest priority", () => {
    // Two entries name the same bytes; the rank-10 occurrence must win, and the
    // fault that sits between them must never be reached because the healthy
    // rank-10 candidate is attempted first.
    const order = canonicalOrder(request([image("dup-low", 30, A), fault("f", 20, "source_unavailable"), image("dup-high", 10, A)]));
    expect(order).toHaveLength(2);
    expect(order[0]).toMatchObject({ kind: "image", sourceId: "dup-high", rank: 10 });
    expect(order[1]).toMatchObject({ kind: "fault", sourceId: "f", rank: 20 });
    const settled = drive(createLoadState(request([image("dup-low", 30, A), fault("f", 20, "source_unavailable"), image("dup-high", 10, A)])), {
      [resourceKey(A)]: { phase: "success", dimensions: { width: 8, height: 8 } },
    });
    expect(settled.selected.sourceId).toBe("dup-high");
    expect(settled.state.reachedFaults).toEqual([]);
  });

  it("does not append a terminal whose resource key already appears in the attempts", () => {
    const order = canonicalOrder(request(
      [image("attempt", 10, A)],
      { terminal: { kind: "alpha_mask", source_id: "terminal", rank: 100, resource: A } },
    ));
    expect(order).toHaveLength(1);
    expect(order[0]).toMatchObject({ sourceId: "attempt", rank: 10, terminal: null });
  });

  it("appends a distinct permitted terminal at its rank", () => {
    const order = canonicalOrder(request(
      [image("attempt", 10, A)],
      { terminal: { kind: "alpha_mask", source_id: "terminal", rank: 100, resource: B } },
    ));
    expect(order.map((entry) => entry.sourceId)).toEqual(["attempt", "terminal"]);
  });

  it("keeps geometry out of the resolution facts", () => {
    const first = { resource_id: "a", version: "v1", url: "/art/a.webp", geometry: { face_rect: { x: 0, y: 0, w: 1, h: 1 } } };
    const second = { ...first, geometry: { face_rect: { x: 0.1, y: 0.1, w: 0.5, h: 0.5 } } };
    expect(resolutionFacts(request([image("a", 10, first)]))).toEqual(resolutionFacts(request([image("a", 10, second)])));
  });
});

describe("ordered resolution", () => {
  it("hides a lower fault when a higher-priority image succeeds", () => {
    const settled = drive(createLoadState(request([image("high", 10, A), fault("low", 20, "generation_failed")])), {
      [resourceKey(A)]: { phase: "success", dimensions: { width: 4, height: 5 } },
    });
    expect(settled.selected).toMatchObject({ sourceId: "high", dimensions: { width: 4, height: 5 } });
    expect(settled.state.phase).toBe(LOAD_PHASE.success);
    expect(settled.state.reachedFaults).toEqual([]);
  });

  it("retains an earlier reached fault under a lower success", () => {
    const settled = drive(createLoadState(request([image("high", 10, A), fault("mid", 15, "source_unavailable"), image("low", 20, B)])), {
      [resourceKey(A)]: { phase: "failed", reason: "image_load_failed" },
      [resourceKey(B)]: { phase: "success", dimensions: { width: 2, height: 3 } },
    });
    expect(settled.selected.sourceId).toBe("low");
    expect(settled.state.reachedFaults).toEqual([
      { sourceId: "high", rank: 10, reason: "image_load_failed" },
      { sourceId: "mid", rank: 15, reason: "source_unavailable" },
    ]);
  });

  it("deduplicates reached faults by source and reason", () => {
    const settled = drive(createLoadState(request([fault("a", 10, "metadata_invalid"), fault("a", 20, "metadata_invalid"), fault("a", 30, "source_unavailable")])), {});
    expect(settled.action.type).toBe("done");
    expect(settled.state.reachedFaults).toEqual([
      { sourceId: "a", rank: 10, reason: "metadata_invalid" },
      { sourceId: "a", rank: 30, reason: "source_unavailable" },
    ]);
  });

  it("exhausts safely and terminates once when every source fails", () => {
    const settled = drive(createLoadState(request([image("a", 10, A), image("b", 20, B), image("c", 30, C)])), {
      [resourceKey(A)]: { phase: "failed", reason: "image_load_failed" },
      [resourceKey(B)]: { phase: "failed", reason: "image_decode_failed" },
      [resourceKey(C)]: { phase: "failed", reason: "image_load_failed" },
    });
    expect(settled.action.type).toBe("done");
    expect(settled.state.phase).toBe(LOAD_PHASE.exhausted);
    expect(settled.state.exhausted).toBe(true);
    expect(settled.state.selected).toBeNull();
    expect(settled.state.reachedFaults.map((entry) => entry.sourceId)).toEqual(["a", "b", "c"]);
    // Resolving the exhausted machine again is idempotent, not recursive.
    const again = resolve(settled.state);
    expect(again.action.type).toBe("done");
  });

  it("ignores a callback from a superseded epoch or a mismatched key", () => {
    const state = createLoadState(request([image("a", 10, A)]));
    expect(observeSuccess(state, { epoch: 99, key: resourceKey(A), dimensions: { width: 1, height: 1 } })).toBe(state);
    expect(observeFailure(state, { epoch: 1, key: "not-a@key", reason: "image_load_failed" })).toBe(state);
  });
});

describe("provisional outcomes", () => {
  it("waits on a delayed healthy preferred source and keeps a lower provisional failure latent", () => {
    const provisional = new Map([
      [resourceKey(B), { epoch: 1, phase: "failed", reason: "image_load_failed" }],
      [resourceKey(A), { epoch: 1, phase: "loading" }],
    ]);
    const settling = drive(createLoadState(request([image("preferred", 10, A), image("fallback", 20, B)]), { provisional }), {});
    expect(settling.action).toMatchObject({ type: "wait", sourceId: "preferred" });
    expect(settling.state.reachedFaults).toEqual([]);
  });

  it("records a provisional failure once its source is reached, then reuses the fallback", () => {
    const provisional = new Map([
      [resourceKey(A), { epoch: 1, phase: "failed", reason: "image_load_failed" }],
      [resourceKey(B), { epoch: 1, phase: "success", dimensions: { width: 6, height: 6 } }],
    ]);
    const settled = drive(createLoadState(request([image("preferred", 10, A), image("fallback", 20, B)]), { provisional }), {});
    expect(settled.action.type).toBe("reuse");
    expect(settled.selected).toMatchObject({ sourceId: "fallback", dimensions: { width: 6, height: 6 } });
    expect(settled.state.reachedFaults).toEqual([{ sourceId: "preferred", rank: 10, reason: "image_load_failed" }]);
  });

  it("reuses a reached provisional success only once", () => {
    const provisional = new Map([[resourceKey(A), { epoch: 1, phase: "success", dimensions: { width: 9, height: 9 } }]]);
    const state = createLoadState(request([image("a", 10, A)]), { provisional });
    const first = resolve(state);
    expect(first.action.type).toBe("reuse");
    expect(first.state.provisional.size).toBe(0);
    const second = resolve(first.state);
    // The handoff is spent; the machine no longer claims a cached success.
    expect(second.action.type).toBe("load");
  });

  it("ignores a provisional outcome from a superseded epoch", () => {
    const provisional = new Map([[resourceKey(A), { epoch: 2, phase: "success", dimensions: { width: 1, height: 1 } }]]);
    const step = resolve(createLoadState(request([image("a", 10, A)]), { provisional }));
    expect(step.action.type).toBe("load");
  });

  it("reuses a durable known success without consuming it", () => {
    const known = new Map([[resourceKey(A), { epoch: 1, phase: "success", dimensions: { width: 7, height: 7 } }]]);
    const first = resolve(createLoadState(request([image("a", 10, A)]), { known }));
    const second = resolve(createLoadState(request([image("a", 10, A)]), { known }));
    expect(first.action.type).toBe("reuse");
    expect(second.action.type).toBe("reuse");
    expect(second.state.selected.dimensions).toEqual({ width: 7, height: 7 });
  });

  it("keeps a same-resource terminal deduplicated against a provisional success", () => {
    const provisional = new Map([[resourceKey(A), { epoch: 1, phase: "success", dimensions: { width: 3, height: 3 } }]]);
    const state = createLoadState(
      request([image("a", 10, A)], { terminal: { kind: "alpha_mask", source_id: "terminal", rank: 100, resource: A } }),
      { provisional },
    );
    expect(state.order).toHaveLength(1);
    const step = resolve(state);
    expect(step.action.type).toBe("reuse");
    expect(step.state.reachedFaults).toEqual([]);
  });
});
