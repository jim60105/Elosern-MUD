import { test } from "node:test";
import assert from "node:assert/strict";

import { ADOPT, HOLD_DRAFT, HOLD_RESTART, changedDocuments, followDecision, preserveSelection } from "../src/lib/following.js";
import { workspaceBanner } from "../src/lib/banner.js";
import { createCommandClient } from "../src/lib/command_client.js";
import { CONNECTED, DISCONNECTED } from "../src/lib/workspace_client.js";

const snap = (session, revision, sequence = 0, extra = {}) => ({
  session_generation: session,
  snapshot_revision: revision,
  preview_state: "current",
  external_change: { sequence, at: null, documents: sequence ? ["content/maps/a.yaml"] : [] },
  ...extra,
});

test("own results, status changes and external changes without drafts are adopted", () => {
  assert.equal(followDecision({ displayed: null, incoming: snap("a", 1) }), ADOPT);
  assert.equal(followDecision({ displayed: snap("a", 1), incoming: snap("a", 2), drafts: 2 }), ADOPT);
  assert.equal(followDecision({ displayed: snap("a", 1), incoming: snap("a", 2, 1), drafts: 0 }), ADOPT);
});

test("an external change is held while a draft is open", () => {
  assert.equal(followDecision({ displayed: snap("a", 1), incoming: snap("a", 2, 1), drafts: 1 }), HOLD_DRAFT);
  assert.deepEqual(changedDocuments(snap("a", 1), snap("a", 2, 1)), ["content/maps/a.yaml"]);
  assert.deepEqual(changedDocuments(snap("a", 1), snap("a", 2)), []);
});

test("another service session is always held for an explicit reread", () => {
  for (const drafts of [0, 3]) {
    assert.equal(followDecision({ displayed: snap("a", 4), incoming: snap("b", 1), drafts }), HOLD_RESTART);
  }
});

test("a selection survives by identity and a removed one is reported", () => {
  assert.deepEqual(preserveSelection(["x", "y"], (ref) => ref === "x"), { kept: ["x"], removed: ["y"] });
  assert.deepEqual(preserveSelection(["x"], () => true), { kept: ["x"], removed: [] });
  assert.deepEqual(preserveSelection([], () => false), { kept: [], removed: [] });
});

test("banner priority: connection, persistent failure, held draft, rejection, preview", () => {
  const stale = snap("a", 1, 0, { preview_state: "stale", candidate_diagnostics: [] });
  const rejected = { code: "stale_snapshot", command: "move_interior_layout", message: "m" };
  const failed = { code: "save_failed", command: "move_interior_layout", message: "m" };
  const pending = snap("a", 2, 1);
  const key = (args) => workspaceBanner({ workspace: stale, connection: CONNECTED, ...args })?.key;
  assert.equal(key({ connection: DISCONNECTED, failure: failed, hold: HOLD_DRAFT }), "disconnected");
  assert.equal(key({ hold: HOLD_RESTART, failure: failed }), "restarted");
  assert.equal(key({ hold: HOLD_DRAFT, pending, failure: failed, drafts: 1 }), "save-failed");
  assert.equal(key({ hold: HOLD_DRAFT, pending, failure: rejected, drafts: 1 }), "external-draft");
  assert.equal(key({ failure: rejected }), "save-rejected");
  assert.equal(key({}), "stale");
  const banner = workspaceBanner({ workspace: stale, connection: CONNECTED, hold: HOLD_DRAFT, pending, drafts: 1 });
  assert.equal(banner.action, "adopt");
  assert.deepEqual(banner.documents, ["content/maps/a.yaml"]);
  assert.equal(workspaceBanner({ workspace: stale, connection: CONNECTED, hold: HOLD_RESTART }).action, "reconnect");
  assert.equal(workspaceBanner({ workspace: stale, connection: DISCONNECTED }).action, "reconnect");
});

function client(responses, workspace = snap("a", 1, 0, { world: { layouts: [] }, history: {} })) {
  const posts = [];
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  const commands = createCommandClient({
    fetchImpl: async (url, options = {}) => {
      if (url === "/api/session") return { ok: true, json: async () => ({ token: "t", session_generation: "a" }) };
      posts.push(url);
      await gate;
      const next = responses.shift() ?? { status: 200, body: { changed: true, document_id: "d" } };
      return { ok: next.status < 300, status: next.status, json: async () => next.body };
    },
    getWorkspace: () => workspace,
    refetch: async () => {},
    segment: "seg",
  });
  return { commands, posts, release };
}

const build = () => ({ name: "move_interior_layout", documentId: "d", expected: "absent", arguments: {} });

test("a lost connection abandons queued commands; nothing is replayed", async () => {
  const { commands, posts, release } = client([]);
  const first = commands.submit(build);
  const second = commands.submit(build);
  await new Promise((resolve) => setTimeout(resolve, 0));
  commands.abandon();
  release();
  await Promise.all([first, second]);
  assert.equal(posts.length, 1);
  await commands.flush();
  assert.equal(posts.length, 1);
});

test("a rejection ends only with a snapshot newer than the one it observed", async () => {
  const { commands, release } = client([
    { status: 409, body: { error: { code: "stale_snapshot", message: "m", snapshot_revision: 5 } } },
  ]);
  release();
  await commands.submit(build);
  assert.equal(commands.state().failure.code, "stale_snapshot");
  commands.clearRejection(snap("a", 5));
  assert.equal(commands.state().failure.code, "stale_snapshot");
  commands.clearRejection(snap("a", 6));
  assert.equal(commands.state().failure, null);
});

test("a fresh read of another session ends a rejection", async () => {
  const { commands, release } = client([{ status: 503, body: { error: { code: "network_error", message: "m" } } }]);
  release();
  await commands.submit(build);
  commands.clearRejection(snap("a", 1));
  assert.ok(commands.state().failure);
  commands.clearRejection(snap("b", 1));
  assert.equal(commands.state().failure, null);
});

test("save failures are never cleared by a newer snapshot", async () => {
  const { commands, release } = client([{ status: 500, body: { error: { code: "save_failed", message: "m" } } }]);
  release();
  await commands.submit(build);
  commands.clearRejection(snap("b", 99));
  assert.equal(commands.state().failure.code, "save_failed");
});
