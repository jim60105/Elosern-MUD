// webclient-action-result-feedback: a recognized non-success ui_action_result
// (outcome rejected / stale / error, matching request id + epoch while a
// mutation is in flight) speaks exactly once through the narrative feed as one
// `err` line carrying the server-authored message verbatim, unless the creation
// overlay is the presenting surface. Successful results append nothing; a
// message-less non-success falls back to the one stable local line; the
// lock/uncertain/revision semantics are pinned unchanged alongside the append.

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import { CREATION_PANEL_SAMPLE } from "../../stories/fixtures.js";
import * as fx from "./protocol_fixtures.js";

const FALLBACK = "動作未生效，請重試或返回上層。";

describe("action-result narrative feedback", () => {
  let store;
  let sender;

  function openSession(panels = {}) {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [fx.snapshot({ panels })], {});
    expect(result.accepted).toBe(true);
  }

  function errLines() {
    return store.narrative.filter((line) => line.kind === "err").map((line) => line.text);
  }

  function dispatchWait() {
    const requestId = store.dispatchAction("explore.wait", { daypart: "dusk" });
    expect(requestId).toBe("session:1");
    return requestId;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  it("appends one verbatim err line for a recognized rejected result", () => {
    openSession();
    dispatchWait();
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
    // The rejected result with a revision-1 gate releases the lock (the
    // committed revision already reaches it) — unchanged lock semantics.
    expect(store.view.dispatch.inFlight).toBe(null);
  });

  it("appends one err line for a stale result while the lock still waits for the recovery revision", () => {
    openSession();
    dispatchWait();
    store.receive(
      1,
      "ui_action_result",
      [fx.actionResult({ outcome: "stale", code: "stale", message: "畫面狀態已更新，請重新操作" })],
      {},
    );
    expect(errLines()).toEqual(["畫面狀態已更新，請重新操作"]);
    // The stale lock rule is unchanged: held until the recovery revision commits.
    expect(store.view.dispatch.inFlight).toEqual({
      requestId: "session:1",
      presentationRevision: 2,
    });
    expect(store.dispatchAction("explore.wait", { sleep: true })).toBe(null);
    store.receive(1, "ui_update", [fx.update({ revision: 2 })], {});
    expect(store.view.dispatch.inFlight).toBe(null);
    // The recovery commit re-runs handleActionResult; the stale line stays at one.
    expect(errLines()).toEqual(["畫面狀態已更新，請重新操作"]);
    // No automatic resubmission ever happened.
    expect(sender.sent.actions.length).toBe(1);
  });

  it("appends nothing again when the same result is re-delivered or re-observed", () => {
    openSession();
    dispatchWait();
    const result = fx.actionResult({
      outcome: "rejected",
      code: "no_exit",
      message: "這裡沒有這個出口。",
      presentation_revision: 1,
    });
    store.receive(1, "ui_action_result", [result], {});
    store.receive(1, "ui_action_result", [JSON.parse(JSON.stringify(result))], {});
    store.receive(1, "ui_update", [fx.update({ revision: 2 })], {});
    expect(errLines()).toEqual(["這裡沒有這個出口。"]);
  });

  it("appends once even when a foreign result is observed between two deliveries of the match", () => {
    // Duck finding 2: the old global "changed from previous" equality let a
    // foreign result erase the dedup memory, re-appending on re-delivery.
    // The stale match keeps the lock held, so the request stays in flight.
    openSession();
    dispatchWait();
    const mine = fx.actionResult({
      outcome: "stale",
      code: "stale",
      message: "畫面狀態已更新，請重新操作",
      presentation_revision: 2,
    });
    store.receive(1, "ui_action_result", [mine], {});
    store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          request_id: "session:9",
          outcome: "rejected",
          code: "no_exit",
          message: "_foreign_結果不可見_",
          presentation_revision: 0,
        }),
      ],
      {},
    );
    // The foreign result neither unlocks nor appends through my request.
    expect(store.view.dispatch.inFlight).toEqual({
      requestId: "session:1",
      presentationRevision: 2,
    });
    store.receive(1, "ui_action_result", [JSON.parse(JSON.stringify(mine))], {});
    store.receive(1, "ui_update", [fx.update({ revision: 2 })], {});
    expect(errLines()).toEqual(["畫面狀態已更新，請重新操作"]);
    expect(sender.sent.actions.length).toBe(1);
  });

  it("recognizes a result already sitting in the reducer once the matching dispatch goes in flight", () => {
    // Duck finding 3: a completed request's cached replay answers the fresh
    // same-id dispatch (the dispatcher replays on request-id collisions). The
    // pre-existing result is recognized exactly once by the new dispatch —
    // semantically this IS the response to it.
    openSession();
    store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          outcome: "rejected",
          code: "already_complete",
          message: "這個角色已經完成了。",
          presentation_revision: 0,
        }),
      ],
      {},
    );
    // No in-flight request: not recognized, nothing appended.
    expect(errLines()).toEqual([]);
    dispatchWait();
    expect(errLines()).toEqual(["這個角色已經完成了。"]);
    // The replayed answer resolves the dispatch (revision-0 gate releases).
    expect(store.view.dispatch.inFlight).toBe(null);
    store.receive(1, "ui_update", [fx.update({ revision: 2 })], {});
    expect(errLines()).toEqual(["這個角色已經完成了。"]);
  });

  it("appends no err line for a successful result", () => {
    openSession();
    dispatchWait();
    store.receive(1, "ui_action_result", [fx.actionResult()], {});
    store.receive(1, "ui_update", [fx.update({ revision: 2 })], {});
    expect(errLines()).toEqual([]);
  });

  it("suppresses the line while the creation overlay is the presenting surface", () => {
    openSession({ creation: CREATION_PANEL_SAMPLE });
    dispatchWait();
    store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          outcome: "rejected",
          code: "name_taken",
          message: "這個名字已經有人使用了。",
          presentation_revision: 1,
        }),
      ],
      {},
    );
    expect(errLines()).toEqual([]);
  });

  it("suppresses for a present creation panel and pins that an unavailable creation panel cannot commit", () => {
    // The suppression gate mirrors the overlay mount predicate (`panel &&
    // panel.available !== false`) for everything the reducer can actually
    // commit: the creation panel validator refuses a panel without
    // `available: true`, so the store gate and the AppClient mount gate can
    // never diverge on committable state (duck finding 1).
    store.beginTransport(1);
    store.setConnected(true);
    const rejected = store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ panels: { creation: { ...CREATION_PANEL_SAMPLE, available: false } } })],
      {},
    );
    expect(rejected.accepted).toBe(false);
    // With the unavailable creation panel refused, the same transport adopts
    // a plain exploration snapshot and the rejection now surfaces in the
    // narrative.
    expect(store.receive(1, "ui_snapshot", [fx.snapshot()], {}).accepted).toBe(true);
    dispatchWait();
    store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          outcome: "rejected",
          code: "name_taken",
          message: "這個名字已經有人使用了。",
          presentation_revision: 1,
        }),
      ],
      {},
    );
    expect(errLines()).toEqual(["這個名字已經有人使用了。"]);
  });

  it("shows the one stable fallback line when a recognized non-success carries no usable message", () => {
    openSession();
    dispatchWait();
    store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          outcome: "error",
          code: "internal_error",
          message: " ",
          // An `error` outcome requires the 32-hex correlation id.
          correlation_id: "0123456789abcdef0123456789abcdef",
          presentation_revision: 1,
        }),
      ],
      {},
    );
    expect(errLines()).toEqual([FALLBACK]);
  });

  it("appends one line for a no_puppet rejection without touching its release semantics", () => {
    openSession();
    dispatchWait();
    store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          outcome: "rejected",
          code: "no_puppet",
          message: "你已離開角色。",
          presentation_revision: 2,
        }),
      ],
      {},
    );
    expect(errLines()).toEqual(["你已離開角色。"]);
    // A no_puppet rejection still releases unconditionally and resolves the
    // mutation (uncertain re-flag precondition unchanged).
    expect(store.view.dispatch.inFlight).toBe(null);
    store.setConnected(false);
    expect(store.view.dispatch.uncertain).toBe(false);
  });

  // 505 real store dispatch/receive cycles under jsdom: locally ~0.4s, but the
  // CI shard runs jsdom workers beside four parallel Evennia processes and the
  // default 5000ms vitest deadline is a contention margin, not a contract.
  // The assertions below remain the contract; only the wall-clock allowance
  // is test-local.
  it("stays bounded under repeated distinct failures", { timeout: 30000 }, () => {
    openSession();
    for (let i = 1; i <= 505; i += 1) {
      const requestId = store.dispatchAction("explore.wait", { daypart: "dusk" });
      expect(requestId).toBe(`session:${i}`);
      store.receive(
        1,
        "ui_action_result",
        [
          fx.actionResult({
            request_id: `session:${i}`,
            outcome: "rejected",
            code: "busy",
            message: `另一項操作正在進行中（${i}）`,
            // No presentation gate: the lock releases on receipt so the next
            // dispatch is admitted immediately.
            presentation_revision: 0,
          }),
        ],
        {},
      );
    }
    expect(store.narrative.length).toBeLessThanOrEqual(500);
    const errs = errLines();
    expect(errs[errs.length - 1]).toBe("另一項操作正在進行中（505）");
    expect(errs).not.toContain("另一項操作正在進行中（1）");
  });

  // oob-result-data-slot: the mirrored validator's success-only `data` slot
  // must reach the requesting view intact, and a result whose slot is
  // illegal must be withheld wholesale (never surfaced with a dirty key).
  it("surfaces a legal success data slot to the requesting view", () => {
    openSession();
    dispatchWait();
    const accepted = store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          request_id: "session:1",
          presentation_revision: 0,
          data: { display_name: "加斯帕・斯諾" },
        }),
      ],
      {},
    );
    expect(accepted.accepted).toBe(true);
    expect(store.view.lastActionResult.data).toEqual({ display_name: "加斯帕・斯諾" });
    // A success result speaks no narrative line.
    expect(errLines()).toEqual([]);
  });

  it("withholds a result whose data slot is illegal", () => {
    openSession();
    dispatchWait();
    const rejected = store.receive(
      1,
      "ui_action_result",
      [
        {
          ...fx.actionResult({ request_id: "session:1", presentation_revision: 0 }),
          data: { actor: "char:1" },
        },
      ],
      {},
    );
    expect(rejected.accepted).toBe(false);
    expect(store.view.lastActionResult).toBe(null);
  });
});
