/*
 * local_map panel schema (design D10a): discriminator, bounds, movement descriptors, byte budgets.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { snapshot, unavailableStatusPanel, validStatusPanel } = require("./protocol_support.js");


function validLocalMapNode(overrides) {
  return Object.assign(
    {
      id: "grid:capital_altoria:2:0",
      label: "南門",
      x: 2,
      y: 0,
      visibility: "current",
      current: true,
      anchor: false,
      landmark: false,
      action: null,
    },
    overrides || {}
  );
}

function validLocalMapEdge(overrides) {
  return Object.assign(
    {
      source: "grid:capital_altoria:2:0",
      destination: "grid:capital_altoria:2:1",
      label: "n",
      known: true,
      traversable: true,
    },
    overrides || {}
  );
}

function validLocalMapPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      layer: "grid",
      current_node: "grid:capital_altoria:2:0",
      title: "南門街道圖",
      nodes: [
        validLocalMapNode(),
        validLocalMapNode({
          id: "grid:capital_altoria:2:1",
          label: "南大道",
          x: 2,
          y: 1,
          visibility: "visible_visited",
          current: false,
          action: {
            kind: "move",
            exit_ref: "42",
            destination: "grid:capital_altoria:2:1",
          },
        }),
      ],
      edges: [validLocalMapEdge()],
      legend: ["你目前所在的位置", "尚未探索的相鄰位置"],
    },
    overrides || {}
  );
}

test("validates the local_map panel available/unavailable discriminator", () => {
  assert.deepEqual(
    Protocol.validatePanel("local_map", Protocol.PANEL_ALLOWLIST.local_map, unavailableStatusPanel()),
    unavailableStatusPanel()
  );
  assert.doesNotThrow(() => Protocol.validateLocalMapPanel(validLocalMapPanel()));
  assert.throws(() => Protocol.validateLocalMapPanel(validLocalMapPanel({ extra: 1 })));
  assert.throws(() =>
    Protocol.validateLocalMapPanel(validLocalMapPanel({ layer: "dungeon" }))
  );
  // A grid current node must carry the grid prefix.
  assert.throws(() =>
    Protocol.validateLocalMapPanel(
      validLocalMapPanel({ layer: "grid", current_node: "room:5" })
    )
  );
});

test("enforces local_map D10a bounds", () => {
  const longLabel = validLocalMapPanel({
    nodes: [
      validLocalMapNode(),
      validLocalMapNode({
        id: "grid:capital_altoria:2:1",
        label: "字".repeat(Protocol.LOCAL_MAP_MAX_STRING + 1),
        visibility: "visible_visited",
        current: false,
      }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(longLabel));

  const tooMany = validLocalMapPanel();
  tooMany.nodes = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES + 1; i++) {
    tooMany.nodes.push(
      validLocalMapNode({
        id: "room:" + i,
        label: "x",
        x: i,
        y: 0,
        visibility: "remembered",
        current: i === 0,
      })
    );
  }
  assert.throws(() => Protocol.validateLocalMapPanel(tooMany));

  const coord = validLocalMapPanel({
    nodes: [
      validLocalMapNode(),
      validLocalMapNode({ id: "room:2", label: "x", x: 1025, y: 0, visibility: "visible_unvisited", current: false }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(coord));
});

test("rejects malformed movement descriptors and unknown node ids", () => {
  const badKind = validLocalMapPanel({
    nodes: [
      validLocalMapNode(),
      validLocalMapNode({
        id: "room:2",
        label: "x",
        x: 1,
        y: 0,
        visibility: "visible_unvisited",
        current: false,
        action: { kind: "teleport", exit_ref: "1", destination: "room:2" },
      }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(badKind));

  const badRef = validLocalMapPanel({
    nodes: [
      validLocalMapNode(),
      validLocalMapNode({
        id: "room:2",
        label: "x",
        x: 1,
        y: 0,
        visibility: "visible_unvisited",
        current: false,
        action: { kind: "move", exit_ref: "字".repeat(10), destination: "room:2" },
      }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(badRef));

  const unknownEdge = validLocalMapPanel({
    edges: [validLocalMapEdge({ destination: "room:999" })],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(unknownEdge));
});

test("a local_map snapshot with an invalid panel is rejected atomically", () => {
  const bad = snapshot({
    panels: {
      status: validStatusPanel(),
      local_map: validLocalMapPanel({ available: "yes" }),
    },
  });
  const store = Protocol.createStore();
  assert.equal(store.receive(1, "ui_snapshot", [bad], {}).accepted, false);
  assert.equal(store.getState().phase, "idle");
});

test("a structurally maximal realistic local_map payload fits the envelope", () => {
  // The structural maxima the schema allows -- 64 nodes, 128 edges, 16
  // legend entries -- with realistic bounded content must serialize under the
  // 65,536-byte envelope (D10a conformance, mirrored from the Python suite).
  const nodeIds = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES; i++) {
    nodeIds.push("grid:capital_altoria:" + (i % 8) + ":" + Math.floor(i / 8));
  }
  const nodes = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES; i++) {
    nodes.push(
      validLocalMapNode({
        id: nodeIds[i],
        label: "南門街道".repeat(4),
        x: i % 2 === 0 ? -1024 : 1024,
        y: i % 2 === 0 ? 1024 : -1024,
        visibility: i === 0 ? "current" : "remembered",
        current: i === 0,
        action:
          i === 0
            ? null
            : { kind: "move", exit_ref: "e" + i, destination: nodeIds[i] },
      })
    );
  }
  const edges = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_EDGES; i++) {
    edges.push({
      source: nodeIds[i % Protocol.LOCAL_MAP_MAX_NODES],
      destination: nodeIds[(i + 1) % Protocol.LOCAL_MAP_MAX_NODES],
      label: "n",
      known: true,
      traversable: true,
    });
  }
  const legend = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_LEGEND; i++) {
    legend.push(i % 2 === 0 ? "你目前所在的位置" : "尚未探索的相鄰位置");
  }
  const panel = validLocalMapPanel({
    current_node: nodeIds[0],
    title: "聖潔王都街道圖",
    nodes: nodes,
    edges: edges,
    legend: legend,
  });
  const normalized = Protocol.validateLocalMapPanel(panel);
  assert.ok(
    Protocol.jsonByteSize(normalized) <= Protocol.MAX_CANONICAL_JSON_BYTES,
    "a structurally maximal realistic payload must fit the 65,536-byte envelope"
  );
});

test("local_map byte budget fails closed on the theoretical worst case", () => {
  // A payload with max-length CJK strings on every node and edge at once
  // serializes far beyond the 65,536-byte envelope; the validator must reject
  // it (D10a conformance is enforced on serialized size, not just per-field
  // bounds).
  const nodeIds = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES; i++) {
    nodeIds.push("grid:capital_altoria:" + (i % 8) + ":" + Math.floor(i / 8));
  }
  const label = "字".repeat(Protocol.LOCAL_MAP_MAX_STRING);
  const nodes = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES; i++) {
    nodes.push(
      validLocalMapNode({
        id: nodeIds[i],
        label: label,
        x: 1024,
        y: -1024,
        visibility: i === 0 ? "current" : "remembered",
        current: i === 0,
        action: i === 0 ? null : { kind: "move", exit_ref: "e".repeat(Protocol.LOCAL_MAP_MAX_EXIT_REF), destination: nodeIds[i] },
      })
    );
  }
  const edges = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_EDGES; i++) {
    edges.push({ source: nodeIds[i % Protocol.LOCAL_MAP_MAX_NODES], destination: nodeIds[(i + 1) % Protocol.LOCAL_MAP_MAX_NODES], label: label, known: true, traversable: true });
  }
  const legend = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_LEGEND; i++) {
    legend.push(label);
  }
  assert.throws(() =>
    Protocol.validateLocalMapPanel(
      validLocalMapPanel({
        current_node: nodeIds[0],
        title: "字".repeat(Protocol.LOCAL_MAP_MAX_TITLE),
        nodes: nodes,
        edges: edges,
        legend: legend,
      })
    )
  );
});

