// Mechanism tests of the explicit partition controls: the chip's state and
// action for every artifact/job combination, the input revision, the derived
// district outlines and the command client's generate/cancel requests.

import { test } from "node:test";
import assert from "node:assert/strict";

import { createCommandClient } from "../src/lib/command_client.js";
import { continentScene, sceneFor } from "../src/lib/map_scene.js";
import { persistenceBanner } from "../src/lib/persistence.js";
import { partitionChip, partitionRevision } from "../src/lib/status.js";

const A = "a".repeat(64);
const B = "b".repeat(64);

function workspace(status, job = "idle", extra = {}) {
  const artifact = {
    current: { status: "current", current: true, game_ready: true, input_signature: A, expected_signature: A },
    stale: { status: "stale", current: false, game_ready: false, input_signature: A, expected_signature: B },
    unavailable: { status: "unavailable", current: false, game_ready: false },
  }[status];
  return { partition_status: { ...artifact, ...extra }, partition_job: { state: job, problems: [] } };
}

test("the chip regenerates whenever the output is not current and cancels while generating", () => {
  const cases = [
    [workspace("current"), "current", null],
    [workspace("stale"), "stale", "regenerate"],
    [workspace("unavailable"), "unavailable", "regenerate"],
    [workspace("stale", "generating"), "generating", "cancel"],
    [workspace("current", "publishing"), "generating", "cancel"],
    [workspace("stale", "cancelled"), "cancelled", "regenerate"],
    [workspace("stale", "failed"), "failed", "regenerate"],
    [workspace("stale", "succeeded"), "stale", "regenerate"],
    // A failed or cancelled job over a current artifact leaves it current.
    [workspace("current", "failed"), "current", null],
    [workspace("current", "cancelled"), "current", null],
    // An uncertain publication withholds readiness: the chip offers a rerun.
    [workspace("current", "failed", { game_ready: false }), "failed", "regenerate"],
  ];
  for (const [state, expected, action] of cases) {
    const chip = partitionChip(state);
    assert.equal(chip.state, expected, JSON.stringify(state));
    assert.equal(chip.action, action, JSON.stringify(state));
    assert.ok(chip.glyph && chip.text);
  }
  assert.equal(partitionChip(null).action, null);
});

test("the revision names the output's inputs and marks older output", () => {
  assert.deepEqual(partitionRevision(workspace("stale")), { output: "aaaaaaaa", current: "bbbbbbbb", older: true });
  assert.equal(partitionRevision(workspace("current")).older, false);
  assert.equal(partitionRevision(workspace("unavailable")), null);
});

function world() {
  return {
    continent: {
      frame_cells: 40,
      cell_size_km: 1,
      mainland_boundary_km: [[0, 0], [40, 0], [40, 40], [0, 40]],
      forest_edge_m: [],
      waterways: [],
      border_river_key: null,
      harbor_sites: [],
      regions: [],
      terrain_preview: { status: "unavailable" },
    },
    locations: [],
    districts: [{ id: "d1", district_name_zh: "一區" }],
    settlements: [],
    interiors: [],
  };
}

const outlines = { d1: [[0, 0, 4000, 0, 4000, 3000]], d2: [[5000, 5000, 6000, 5000, 6000, 6000]] };

test("district outlines are derived, non-selectable rings on the partition layer", () => {
  const scene = continentScene(world(), [], { outlines, older: false });
  const rings = scene.shapes.filter((shape) => shape.id.startsWith("district:"));
  assert.equal(rings.length, 2);
  const first = rings.find((shape) => shape.id === "district:d1:0");
  assert.deepEqual(first.points, [{ x: 0, y: 0 }, { x: 4000, y: 0 }, { x: 4000, y: 3000 }]);
  assert.equal(first.district, "d1");
  assert.ok(rings.every((shape) => shape.derived && !shape.selectable && shape.ref === null && shape.layer === "partition"));
  assert.ok(rings.every((shape) => !shape.older));
  assert.equal(continentScene(world(), []).shapes.filter((shape) => shape.id.startsWith("district:")).length, 0);
});

test("outlines of older inputs keep a persistent older-input mark", () => {
  const scene = sceneFor(world(), "continent", null, [], { partition: { outlines, older: true } });
  const rings = scene.shapes.filter((shape) => shape.id.startsWith("district:"));
  assert.ok(rings.every((shape) => shape.older && shape.role.split(" ").includes("district--older")));
  assert.notEqual(rings[0].label, continentScene(world(), [], { outlines, older: false }).shapes.find((s) => s.id === rings[0].id).label);
});

function service(responses, base = { session_generation: "s1", snapshot_revision: 4 }) {
  let current = { ...base, world: { layouts: [] }, history: {} };
  const posts = [];
  const fetchImpl = async (url, options = {}) => {
    if (url === "/api/session") return { ok: true, json: async () => ({ token: "t", session_generation: "s1" }) };
    posts.push({ url, body: JSON.parse(options.body) });
    const next = responses.shift() ?? { status: 200, body: { changed: true } };
    return { ok: next.status < 300, status: next.status, json: async () => next.body };
  };
  let refetches = 0;
  const client = createCommandClient({
    fetchImpl,
    getWorkspace: () => current,
    refetch: async () => {
      refetches += 1;
      current = { ...current, snapshot_revision: current.snapshot_revision + 1 };
    },
    segment: "seg",
  });
  return { client, posts, refetches: () => refetches };
}

test("generate waits for queued commands and names the snapshot they left", async () => {
  const { client, posts } = service([]);
  const command = client.submit(() => ({ name: "move_interior_layout", documentId: "d", expected: "absent", arguments: {} }));
  const generate = client.partition("generate");
  await Promise.all([command, generate]);
  assert.deepEqual(posts.map((post) => post.url), ["/api/commands/move_interior_layout", "/api/partition/generate"]);
  assert.deepEqual(posts[1].body, { session_generation: "s1", snapshot_revision: 5 });
});

test("cancel sends only the session and a finished job is not a failure", async () => {
  const { client, posts, refetches } = service([
    { status: 409, body: { error: { code: "job_not_running", message: "done", job: { state: "succeeded" } } } },
  ]);
  await client.partition("cancel");
  assert.deepEqual(posts[0], { url: "/api/partition/cancel", body: { session_generation: "s1" } });
  assert.equal(client.state().failure, null);
  assert.equal(refetches(), 1);
});

test("a refused generate is reported in the banner slot", async () => {
  const { client } = service([{ status: 409, body: { error: { code: "job_running", message: "busy" } } }]);
  await client.partition("generate");
  const failure = client.state().failure;
  assert.equal(failure.code, "job_running");
  assert.equal(failure.command, "partition_generate");
  assert.equal(persistenceBanner({}, failure).action, "reload");
});

test("a command refused during generation gets its own banner", () => {
  const generating = persistenceBanner({}, { code: "write_paused", command: "move_control_point", message: "m", details: { reason: "partition_generating" } });
  const paused = persistenceBanner({}, { code: "write_paused", command: "move_control_point", message: "m", details: { reason: "stale_preview" } });
  assert.equal(generating.key, "partition-generating");
  assert.notEqual(paused.key, generating.key);
});
