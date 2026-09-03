// webclient-action-feedback (add-action-feedback-toasts): the store owns a
// bounded, client-local toast queue. Entries carry {id, title, sub?, tone}
// with tone ∈ {info, crit}; the queue caps at four with FIFO eviction; every
// entry self-dismisses after ~5200 ms from its own push; push/dismiss are the
// only writers and touch nothing else — not the reducer snapshot, not
// persistence, not the narrative feed. The failure trigger: a recognized
// non-success `creation.concept` result pushes exactly one crit toast
// carrying the server message verbatim (or the one stable fallback), deduped
// by the same fingerprint the narrative line uses, and a success result
// pushes nothing at all (the form layer owns the success confirmation).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import { CREATION_PANEL_SAMPLE } from "../../stories/fixtures.js";
import * as fx from "./protocol_fixtures.js";

const FALLBACK = "動作未生效，請重試或返回上層。";

describe("action-feedback toast queue", () => {
  let store;
  let sender;

  function openSession(panels = {}, fields = {}) {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [fx.snapshot({ panels, ...fields })], {});
    expect(result.accepted).toBe(true);
  }

  // A committed revision >= the result's declared gate lets a success commit
  // cleanly (the reducer refuses results that declare ahead of the committed
  // revision — the same protocol rule the legacy tests document).
  function openSessionAtRevision2(panels = {}) {
    openSession(panels, { revision: 2 });
  }

  function errLines() {
    return store.narrative.filter((line) => line.kind === "err").map((line) => line.text);
  }

  function dispatchConcept() {
    const requestId = store.dispatchAction("creation.concept", { concept: "貓人少女" });
    expect(requestId).toBe("session:1");
    return requestId;
  }

  function deliverConceptResult(fields) {
    store.receive(1, "ui_action_result", [fx.actionResult(fields)], {});
  }

  function toasts() {
    return store.view.toasts.map(({ id, title, sub, tone }) => ({ id, title, sub, tone }));
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    // No 5200 ms timer crosses a case: the store's scope-dispose teardown
    // clears every pending entry timer and drops the queue, and any fake
    // clock is dropped with the case.
    store.$dispose();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("exposes the queue on the view slice with the frozen entry shape", () => {
    openSession();
    expect(store.view.toasts).toEqual([]);
    const id = store.pushToast({ title: "概念提案已套用到自訂表單", sub: "貓人見習者", tone: "info" });
    expect(typeof id).toBe("number");
    expect(toasts()).toEqual([
      { id, title: "概念提案已套用到自訂表單", sub: "貓人見習者", tone: "info" },
    ]);
    // A blank subtitle is absent, not carried as an empty field.
    store.pushToast({ title: "已離開商店", sub: "   ", tone: "info" });
    expect("sub" in store.view.toasts[1]).toBe(false);
    expect(store.view.toasts[1].id).toBeGreaterThan(id); // monotonic ids
  });

  it("rejects malformed entries (not coerced) with a warning", () => {
    openSession();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(store.pushToast({ title: "  ", tone: "info" })).toBe(null);
    expect(store.pushToast({ title: "標題", tone: "warn" })).toBe(null);
    expect(store.pushToast({ tone: "crit" })).toBe(null);
    expect(store.pushToast()).toBe(null);
    expect(store.view.toasts).toEqual([]);
    expect(warn).toHaveBeenCalledTimes(4);
  });

  it("caps the queue at four with FIFO eviction", () => {
    openSession();
    const ids = [1, 2, 3, 4, 5].map((n) => store.pushToast({ title: `t${n}`, tone: "info" }));
    expect(store.view.toasts.map((toast) => toast.id)).toEqual([ids[1], ids[2], ids[3], ids[4]]);
    expect(store.view.toasts.map((toast) => toast.title)).toEqual(["t2", "t3", "t4", "t5"]);
  });

  it("self-dismisses an entry after its 5200 ms lifetime and a click dismissal cancels its timer", () => {
    vi.useFakeTimers();
    openSession();
    const only = store.pushToast({ title: "t1", tone: "info" });
    vi.advanceTimersByTime(5199);
    expect(store.view.toasts.map((toast) => toast.id)).toEqual([only]);
    vi.advanceTimersByTime(1); // the entry hits its lifetime
    expect(store.view.toasts).toEqual([]);
    // Click dismiss removes early and kills the pending timer: advancing the
    // whole lifetime afterwards leaves an empty, inert queue.
    const clicked = store.pushToast({ title: "t2", tone: "crit" });
    expect(store.dismissToast(clicked)).toBe(true);
    expect(store.view.toasts).toEqual([]);
    expect(store.dismissToast(clicked)).toBe(false); // unknown id is a no-op
    vi.advanceTimersByTime(10000);
    expect(store.view.toasts).toEqual([]);
  });

  it("starts each entry's own lifetime at its push", () => {
    vi.useFakeTimers();
    openSession();
    const first = store.pushToast({ title: "t1", tone: "info" });
    vi.advanceTimersByTime(5199);
    expect(store.view.toasts.map((toast) => toast.id)).toEqual([first]);
    // Staggered on purpose: the second entry's lifetime starts now, so the
    // boundary below exercises the FIRST entry's expiry only.
    const second = store.pushToast({ title: "t2", tone: "crit" });
    vi.advanceTimersByTime(1); // first expires at its own 5200 ms mark
    expect(store.view.toasts.map((toast) => toast.id)).toEqual([second]);
    // The second was pushed at t=5199 and lives until t=10399; the store's
    // per-entry lifetime clock is its own.
    vi.advanceTimersByTime(5199); // t=10399: the second entry hits its own mark
    expect(store.view.toasts).toEqual([]);
  });

  it("surfaces exactly one crit toast for a recognized failed concept dispatch, verbatim", () => {
    openSession({ creation: CREATION_PANEL_SAMPLE });
    dispatchConcept();
    deliverConceptResult({
      outcome: "rejected",
      code: "concept_unavailable",
      message: "概念服務目前無法使用，請稍後再試。",
      presentation_revision: 1,
    });
    expect(toasts()).toEqual([
      { id: 1, title: "概念服務目前無法使用，請稍後再試。", tone: "crit" },
    ]);
    // Additive: the overlay is the presenting surface, so the narrative feed
    // suppression is unchanged (no new err line) and the overlay result
    // region keeps its own line.
    expect(errLines()).toEqual([]);
    expect(store.view.lastActionResult.message).toBe("概念服務目前無法使用，請稍後再試。");
    // Re-delivery and re-observation stay deduped by the shared fingerprint.
    deliverConceptResult({
      outcome: "rejected",
      code: "concept_unavailable",
      message: "概念服務目前無法使用，請稍後再試。",
      presentation_revision: 1,
    });
    store.refreshView();
    expect(toasts()).toHaveLength(1);
  });

  it("fires the crit toast while no creation panel is mounted (action-scoped, not surface-scoped)", () => {
    openSession();
    dispatchConcept();
    deliverConceptResult({
      outcome: "error",
      code: "error",
      message: "處理失敗，請稍後再試。",
      presentation_revision: 1,
      // The protocol requires error results to carry the transport's
      // correlation id (protocol.js ui_action_result validator).
      correlation_id: "0123456789abcdef0123456789abcdef",
    });
    expect(toasts()).toEqual([{ id: 1, title: "處理失敗，請稍後再試。", tone: "crit" }]);
  });

  it("speaks the one stable fallback line for a message-less concept failure", () => {
    openSession({ creation: CREATION_PANEL_SAMPLE });
    dispatchConcept();
    deliverConceptResult({
      outcome: "rejected",
      code: "concept_unavailable",
      message: "   ",
      presentation_revision: 1,
    });
    expect(toasts()).toEqual([{ id: 1, title: FALLBACK, tone: "crit" }]);
  });

  it("matches the feed's non-success outcome set: a stale concept result also criticises", () => {
    openSession({ creation: CREATION_PANEL_SAMPLE });
    dispatchConcept();
    deliverConceptResult({
      outcome: "stale",
      code: "stale",
      message: "界面已過期，請稍後再試。",
    });
    expect(toasts()).toEqual([{ id: 1, title: "界面已過期，請稍後再試。", tone: "crit" }]);
    // The lock holds until the recovery revision commits; the re-observation
    // on commit re-runs the recognition branch and the fingerprint keeps the
    // crit at exactly one (the dedup unit is shared with the feed line).
    store.receive(1, "ui_update", [fx.update({ revision: 2, panels: { creation: CREATION_PANEL_SAMPLE } })], {});
    expect(toasts()).toHaveLength(1);
  });

  it("pushes nothing for a successful concept result, overlay mounted or not", () => {
    openSessionAtRevision2({ creation: CREATION_PANEL_SAMPLE });
    dispatchConcept();
    deliverConceptResult({ outcome: "success", code: "concept_applied", presentation_revision: 1 });
    expect(store.view.toasts).toEqual([]);
  });

  it("keeps every other action failure on the narrative channel only", () => {
    openSession();
    const requestId = store.dispatchAction("explore.wait", { daypart: "dusk" });
    expect(requestId).toBe("session:1");
    store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          outcome: "rejected",
          code: "stale_location",
          message: "你的位置已經改變，請重新操作。",
          presentation_revision: 1,
        }),
      ],
      {},
    );
    expect(errLines()).toEqual(["你的位置已經改變，請重新操作。"]);
    expect(store.view.toasts).toEqual([]);
  });

  it("touches nothing else: no reducer commit, no persistence, no feed line", () => {
    openSession({ creation: CREATION_PANEL_SAMPLE });
    const revisionBefore = store.view.revision;
    const linesBefore = store.narrative.length;
    const sentBefore = sender.sent.actions.length;
    const writes = vi.spyOn(Storage.prototype, "setItem");
    const id = store.pushToast({ title: "概念服務目前無法使用", tone: "crit" });
    store.dismissToast(id);
    expect(writes).not.toHaveBeenCalled();
    expect(store.view.revision).toBe(revisionBefore);
    expect(store.narrative.length).toBe(linesBefore);
    expect(sender.sent.actions.length).toBe(sentBefore);
    // The queue is view-only: a committed update republish keeps the pushed
    // entries and the very same live array reference (client-local, never
    // committed, never rebuilt away).
    const before = store.pushToast({ title: "t", tone: "info" });
    store.receive(1, "ui_update", [fx.update({ revision: 2, panels: { creation: CREATION_PANEL_SAMPLE } })], {});
    expect(store.view.toasts).toHaveLength(1);
    expect(store.view.toasts[0].id).toBe(before);
  });

  it("clears every pending timer and the queue when the store disposes", () => {
    vi.useFakeTimers();
    openSession();
    store.pushToast({ title: "待清除", tone: "crit" });
    const pendingBefore = vi.getTimerCount();
    expect(pendingBefore).toBeGreaterThan(0);
    store.$dispose();
    // Exactly the entry's own timer was cleared — nothing can fire back
    // into a disposed store.
    expect(vi.getTimerCount()).toBe(pendingBefore - 1);
    expect(store.view.toasts).toEqual([]);
    vi.advanceTimersByTime(6000);
    expect(store.view.toasts).toEqual([]);
  });
});
