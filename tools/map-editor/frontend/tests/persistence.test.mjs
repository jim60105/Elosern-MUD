import { test } from "node:test";
import assert from "node:assert/strict";

import { createCommandClient } from "../src/lib/command_client.js";
import {
  ABSENT,
  fromScene,
  layoutDocumentId,
  layoutFingerprint,
  moveCommand,
  nudgeDelta,
  storedPosition,
  toScene,
} from "../src/lib/layout_edit.js";
import { interiorPositions } from "../src/lib/map_scene.js";
import { DRAFT, FAILED, SAVED, SAVING, UNCERTAIN, parseIntegerDraft, persistenceBanner, saveState } from "../src/lib/persistence.js";
import { selectionOwner } from "../src/lib/selection_owner.js";

const interior = {
  id: "hall",
  rooms: [
    { id: "a", layout_position: null },
    { id: "b", layout_position: [5, -2] },
    { id: "c", layout_position: null },
    { id: "d", layout_position: null },
  ],
};

test("stored layout positions and scene points convert in one place", () => {
  assert.deepEqual(storedPosition(interior, "b"), [5, -2]);
  // List fallback in stored coordinates (rows grow down the screen).
  assert.deepEqual(storedPosition(interior, "d"), [0, 1]);
  assert.equal(storedPosition(interior, "missing"), null);
  assert.deepEqual(toScene([0, 1]), { x: 0, y: -1 });
  assert.deepEqual(fromScene({ x: 0.4, y: 0.4 }), [0, 0]);
  assert.ok(!Object.is(fromScene({ x: -0.2, y: 0.2 })[1], -0));
  for (const room of interior.rooms) {
    assert.deepEqual(fromScene(interiorPositions(interior).get(room.id)), storedPosition(interior, room.id));
  }
  assert.deepEqual(nudgeDelta("ArrowUp"), [0, -1]);
  assert.equal(nudgeDelta("a"), null);
});

test("a move names its owning layout and the absent sentinel before the first save", () => {
  const world = { layouts: [{ id: "other", fingerprint: "f".repeat(64) }] };
  assert.equal(layoutFingerprint(world, "hall"), ABSENT);
  assert.equal(layoutFingerprint(world, "other"), "f".repeat(64));
  assert.deepEqual(moveCommand(world, "hall", "a", [1, 2]), {
    name: "move_interior_layout",
    documentId: layoutDocumentId("hall"),
    expected: ABSENT,
    arguments: { interior_id: "hall", room_id: "a", x: 1, y: 2 },
  });
});

test("a selection spanning owners is unavailable for mutation", () => {
  assert.equal(selectionOwner(["interior_room:hall:a", "interior_room:hall:b"]).owner, layoutDocumentId("hall"));
  assert.equal(selectionOwner(["interior_room:hall:a", "interior_room:cellar:b"]).reason, "cross_document");
  assert.equal(selectionOwner(["interior_room:hall:a", "settlement_node:m:a"]).reason, "not_editable");
  assert.equal(selectionOwner([]).reason, "empty");
});

test("only complete integers leave the draft state", () => {
  assert.deepEqual(parseIntegerDraft(" -12 "), { ok: true, value: -12 });
  for (const text of ["", "-", "1o", "1.5", "1e3", "99999999999999999999"]) {
    assert.equal(parseIntegerDraft(text).ok, false, text);
  }
});

test("the service's pause outranks local save states", () => {
  const paused = { write_pause: { paused: true, reason: "uncertain_durability" }, pending_intent: { command: "undo", document_id: "x" } };
  assert.equal(saveState({ workspace: paused }), UNCERTAIN);
  assert.equal(saveState({ workspace: {}, failure: { code: "save_failed" }, inFlight: 1 }), FAILED);
  assert.equal(saveState({ workspace: {}, inFlight: 1, drafts: 1 }), SAVING);
  assert.equal(saveState({ workspace: {}, drafts: 2 }), DRAFT);
  assert.equal(saveState({ workspace: {} }), SAVED);
  assert.equal(persistenceBanner(paused, null).action, "reload");
  assert.equal(persistenceBanner({}, { code: "stale_document", command: "undo", message: "m" }).action, "reload");
  assert.equal(persistenceBanner({}, null), null);
});

function service(responses) {
  let workspace = { session_generation: "s1", snapshot_revision: 1, world: { layouts: [] }, history: { segment: null, undo: null, redo: null } };
  const posts = [];
  const fetchImpl = async (url, options = {}) => {
    if (url === "/api/session") return { ok: true, json: async () => ({ token: "t", session_generation: workspace.session_generation }) };
    const body = JSON.parse(options.body);
    posts.push({ url, body, token: options.headers["X-Map-Editor-Token"] });
    const next = responses.shift() ?? { status: 200, body: { changed: true, document_id: body.document_id } };
    return { ok: next.status < 300, status: next.status, json: async () => next.body };
  };
  const refetches = [];
  const client = createCommandClient({
    fetchImpl,
    getWorkspace: () => workspace,
    refetch: async () => {
      refetches.push(workspace.snapshot_revision);
      workspace = { ...workspace, snapshot_revision: workspace.snapshot_revision + 1, ...(responses.nextWorkspace ?? {}) };
    },
    segment: "seg",
  });
  return { client, posts, refetches, setWorkspace: (next) => (workspace = { ...workspace, ...next }) };
}

const move = (x) => (workspace) => ({ ...moveCommand(workspace.world, "hall", "a", [x, 0]) });

test("commands run one at a time, each built against the snapshot the previous one left", async () => {
  const { client, posts } = service([]);
  await Promise.all([client.submit(move(1)), client.submit(move(2))]);
  assert.deepEqual(posts.map((post) => post.body.snapshot_revision), [1, 2]);
  assert.deepEqual(posts.map((post) => post.body.arguments.x), [1, 2]);
  assert.ok(posts.every((post) => post.token === "t" && post.body.segment === "seg"));
  assert.equal(client.state().inFlight, 0);
  assert.equal(client.state().failure, null);
});

test("a failure is reported once and the queued remainder is dropped, never retried", async () => {
  const { client, posts } = service([{ status: 500, body: { error: { code: "save_failed", message: "disk full" } } }]);
  const first = client.submit(move(1));
  const second = client.submit(move(2));
  await Promise.all([first, second]);
  assert.equal(posts.length, 1);
  assert.equal(client.state().failure.code, "save_failed");
  await client.flush();
  assert.equal(posts.length, 1);
  // A later explicit operation is admitted again.
  await client.submit(move(3));
  assert.equal(posts.length, 2);
});

test("undo and redo send the head of this page's own segment only", async () => {
  const { client, posts, setWorkspace } = service([]);
  setWorkspace({ history: { segment: "another-tab", undo: { document_id: "d", expected_document_fingerprint: "e" }, redo: null } });
  await client.undo();
  assert.equal(posts.length, 0);
  setWorkspace({ history: { segment: "seg", undo: { document_id: "d", expected_document_fingerprint: "e" }, redo: null } });
  await client.undo();
  assert.equal(posts[0].url, "/api/commands/undo");
  assert.equal(posts[0].body.document_id, "d");
  assert.equal(posts[0].body.expected_document_fingerprint, "e");
  assert.deepEqual(posts[0].body.arguments, {});
  await client.redo();
  assert.equal(posts.length, 1);
});

test("a refetch problem never turns an acknowledged command into a failure", async () => {
  const posts = [];
  const workspace = { session_generation: "s1", snapshot_revision: 1, world: { layouts: [] }, history: {} };
  const client = createCommandClient({
    fetchImpl: async (url, options = {}) => {
      if (url === "/api/session") return { ok: true, json: async () => ({ token: "t", session_generation: "s1" }) };
      posts.push(url);
      return { ok: true, status: 200, json: async () => ({ changed: true, document_id: "d" }) };
    },
    getWorkspace: () => workspace,
    refetch: async () => {
      throw new Error("offline");
    },
    segment: "seg",
  });
  const payload = await client.submit(move(1));
  assert.equal(payload.changed, true);
  assert.equal(client.state().failure, null);
  assert.equal(client.state().inFlight, 0);
  assert.equal(posts.length, 1);
});

test("a no-op build sends nothing and an explicit reread clears the failure", async () => {
  const { client, posts } = service([{ status: 409, body: { error: { code: "stale_document", message: "changed" } } }]);
  await client.submit(() => null);
  assert.equal(posts.length, 0);
  await client.submit(move(1));
  assert.equal(client.state().failure.code, "stale_document");
  await client.reload();
  assert.equal(posts.at(-1).url, "/api/reload");
  assert.equal(client.state().failure, null);
});
