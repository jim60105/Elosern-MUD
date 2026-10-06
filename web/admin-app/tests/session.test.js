import { describe, expect, it } from "vitest";
import { createSessionState } from "../lib/session.js";

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("session state", () => {
  it("shares one in-flight request between callers", async () => {
    const calls = [];
    const api = { get: (path) => (calls.push(path), Promise.resolve({ account_name: "op" })) };
    const session = createSessionState(api);
    await Promise.all([session.load(), session.load()]);
    expect(calls).toEqual(["/session"]);
    expect(session.state.status).toBe("ready");
  });

  it("ignores a stale response that settles after a forced reload", async () => {
    const first = deferred();
    const second = deferred();
    const queue = [first, second];
    const session = createSessionState({ get: () => queue.shift().promise });
    const stale = session.load();
    const fresh = session.load({ force: true });
    second.resolve({ account_name: "new" });
    await fresh;
    first.reject(new Error("old failure"));
    await stale;
    expect(session.state.status).toBe("ready");
    expect(session.state.data).toEqual({ account_name: "new" });
    expect(session.state.error).toBeNull();
  });
});
