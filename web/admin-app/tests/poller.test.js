import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPoller, POLL_INTERVAL_MS } from "../lib/poller.js";

function fakeDocument(state = "visible") {
  const listeners = new Set();
  return {
    visibilityState: state,
    addEventListener: (type, fn) => type === "visibilitychange" && listeners.add(fn),
    removeEventListener: (type, fn) => type === "visibilitychange" && listeners.delete(fn),
    set(next) {
      this.visibilityState = next;
      for (const fn of [...listeners]) fn();
    },
    listeners,
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("poller", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("polls on start and every interval after each load settles", async () => {
    const doc = fakeDocument();
    const load = vi.fn(async () => ({ n: load.mock.calls.length }));
    const onData = vi.fn();
    const poller = createPoller({ load, onData, doc });
    poller.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(load).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS - 1);
    expect(load).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(load).toHaveBeenCalledTimes(2);
    expect(onData).toHaveBeenLastCalledWith({ n: 2 });
    poller.stop();
  });

  it("never overlaps requests while a slow load is in flight", async () => {
    const doc = fakeDocument();
    const slow = deferred();
    const load = vi.fn(() => slow.promise);
    const poller = createPoller({ load, doc });
    poller.start();
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 4);
    poller.refresh();
    poller.refresh();
    expect(load).toHaveBeenCalledTimes(1);
    slow.resolve({});
    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    expect(load).toHaveBeenCalledTimes(2);
    poller.stop();
  });

  it("pauses while hidden and resumes with one immediate poll and one timer", async () => {
    const doc = fakeDocument();
    const load = vi.fn(async () => ({}));
    const poller = createPoller({ load, doc });
    poller.start();
    await vi.advanceTimersByTimeAsync(0);
    doc.set("hidden");
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 5);
    expect(load).toHaveBeenCalledTimes(1);
    doc.set("visible");
    doc.set("hidden");
    doc.set("visible");
    await vi.advanceTimersByTimeAsync(0);
    expect(load).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    expect(load).toHaveBeenCalledTimes(3);
    poller.stop();
  });

  it("does not load when started hidden", async () => {
    const doc = fakeDocument("hidden");
    const load = vi.fn(async () => ({}));
    const poller = createPoller({ load, doc });
    poller.start();
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3);
    expect(load).not.toHaveBeenCalled();
    doc.set("visible");
    await vi.advanceTimersByTimeAsync(0);
    expect(load).toHaveBeenCalledTimes(1);
    poller.stop();
  });

  it("stop clears the timer, the listener, and late publications", async () => {
    const doc = fakeDocument();
    const late = deferred();
    const load = vi.fn(() => late.promise);
    const onData = vi.fn();
    const poller = createPoller({ load, onData, doc });
    poller.start();
    poller.stop();
    late.resolve({ stale: true });
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3);
    expect(onData).not.toHaveBeenCalled();
    expect(doc.listeners.size).toBe(0);
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("reports failures, keeps polling, and stops on authorization loss", async () => {
    const doc = fakeDocument();
    const load = vi
      .fn()
      .mockRejectedValueOnce(Object.assign(new Error("down"), { code: "network_error" }))
      .mockRejectedValueOnce(Object.assign(new Error("401"), { code: "unauthenticated" }));
    const onError = vi.fn();
    const poller = createPoller({ load, onError, doc });
    poller.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(onError).toHaveBeenCalledTimes(1);
    expect(poller.running).toBe(true);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    expect(onError).toHaveBeenCalledTimes(2);
    expect(poller.running).toBe(false);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3);
    expect(load).toHaveBeenCalledTimes(2);
  });
});
