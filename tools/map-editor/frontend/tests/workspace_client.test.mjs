import { test } from "node:test";
import assert from "node:assert/strict";

import { CONNECTED, DISCONNECTED, createWorkspaceClient, needsRefetch } from "../src/lib/workspace_client.js";

class FakeEventSource {
  constructor(url) {
    this.url = url;
    this.listeners = {};
    FakeEventSource.last = this;
  }
  addEventListener(type, listener) {
    (this.listeners[type] ??= []).push(listener);
  }
  emit(type, data) {
    for (const listener of this.listeners[type] ?? []) listener({ type, data: JSON.stringify(data) });
  }
  close() {
    this.closed = true;
  }
}

function harness(responses) {
  const requests = [];
  const states = [];
  const fetchImpl = async (url) => {
    requests.push(url);
    const body = responses.shift();
    return { ok: true, json: async () => body };
  };
  const client = createWorkspaceClient({ fetchImpl, EventSourceImpl: FakeEventSource, onChange: (s) => states.push(s) });
  client.start();
  return { client, requests, states, source: FakeEventSource.last };
}

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const snapshot = (session, revision) => ({ session_generation: session, snapshot_revision: revision, checked_at: null });

test("a refetch is needed for another session or revision only", () => {
  assert.equal(needsRefetch(null, snapshot("a", 1)), true);
  assert.equal(needsRefetch(snapshot("a", 1), snapshot("a", 1)), false);
  assert.equal(needsRefetch(snapshot("a", 1), snapshot("a", 2)), true);
  assert.equal(needsRefetch(snapshot("a", 1), snapshot("b", 1)), true);
});

test("the first status fetches the complete workspace and replaces state", async () => {
  const { requests, states, source } = harness([{ ...snapshot("a", 1), world: { marker: 1 } }]);
  source.emit("status", snapshot("a", 1));
  await tick();
  assert.deepEqual(requests, ["/api/workspace"]);
  assert.equal(states.at(-1).connection, CONNECTED);
  assert.deepEqual(states.at(-1).workspace.world, { marker: 1 });
});

test("an invalidate refetches and the reply replaces, never merges", async () => {
  const { requests, states, source } = harness([
    { ...snapshot("a", 1), world: { kept: true, other: 1 } },
    { ...snapshot("a", 2), world: { other: 2 } },
  ]);
  source.emit("status", snapshot("a", 1));
  await tick();
  source.emit("invalidate", snapshot("a", 2));
  await tick();
  assert.equal(requests.length, 2);
  assert.deepEqual(states.at(-1).workspace.world, { other: 2 });
});

test("a disconnect keeps the last snapshot and a reconnect status refetches", async () => {
  const { requests, states, source } = harness([snapshot("a", 1), snapshot("b", 1)]);
  source.emit("status", snapshot("a", 1));
  await tick();
  source.onerror();
  assert.equal(states.at(-1).connection, DISCONNECTED);
  assert.equal(states.at(-1).workspace.session_generation, "a");
  // Restarted service: the reconnect's first status names a new session.
  source.emit("status", snapshot("b", 1));
  await tick();
  assert.equal(requests.length, 2);
  assert.equal(states.at(-1).connection, CONNECTED);
  assert.equal(states.at(-1).workspace.session_generation, "b");
});

test("a reconnect to the same unchanged snapshot does not refetch", async () => {
  const { requests, source } = harness([snapshot("a", 1)]);
  source.emit("status", snapshot("a", 1));
  await tick();
  source.onerror();
  source.emit("status", snapshot("a", 1));
  await tick();
  assert.equal(requests.length, 1);
});

test("an older response never overwrites a newer one", async () => {
  const resolvers = [];
  const states = [];
  const fetchImpl = () => new Promise((resolve) => resolvers.push(resolve));
  const client = createWorkspaceClient({ fetchImpl, EventSourceImpl: FakeEventSource, onChange: (s) => states.push(s) });
  client.start();
  const source = FakeEventSource.last;
  source.emit("status", snapshot("a", 1));
  source.emit("invalidate", snapshot("a", 2));
  resolvers[1]({ ok: true, json: async () => snapshot("a", 2) });
  await tick();
  resolvers[0]({ ok: true, json: async () => snapshot("a", 1) });
  await tick();
  assert.equal(states.at(-1).workspace.snapshot_revision, 2);
});
