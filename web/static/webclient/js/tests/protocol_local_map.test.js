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
      gateway: null,
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
    Protocol.validatePanel("local_map", Protocol.PANEL_ALLOWLIST.local_map, unavailableStatusPanel({ schema_version: 1 })),
    unavailableStatusPanel({ schema_version: 1 })
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
      validLocalMapNode({
        id: "room:2",
        label: "x",
        x: Protocol.LOCAL_MAP_COORD_MAX + 1,
        y: 0,
        visibility: "visible_unvisited",
        current: false,
      }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(coord));
});

test("accepts the metric settlement and wilderness frames, rejects invented geometry", () => {
  // project-metric-local-maps: the real protocol envelope carries integer
  // metres for a settlement and the 0..2699 wilderness frame. The shared
  // bound must equal the server validator's (-10_000_000..10_000_000).
  assert.equal(Protocol.LOCAL_MAP_COORD_MIN, -10000000);
  assert.equal(Protocol.LOCAL_MAP_COORD_MAX, 10000000);
  const settlement = validLocalMapPanel({
    current_node: "grid:capital_altoria:6500:6350",
    nodes: [
      validLocalMapNode({ id: "grid:capital_altoria:6500:6350", x: 6500, y: 6350 }),
      validLocalMapNode({
        id: "grid:altoria:6500:6351",
        label: "北門",
        x: 6500,
        y: 6351,
        visibility: "visible_visited",
        current: false,
        action: { kind: "move", exit_ref: "n", destination: "grid:altoria:6500:6351" },
      }),
    ],
    edges: [
      validLocalMapEdge({
        source: "grid:capital_altoria:6500:6350",
        destination: "grid:altoria:6500:6351",
      }),
    ],
  });
  assert.doesNotThrow(() => Protocol.validateLocalMapPanel(settlement));

  const wilderness = validLocalMapPanel({
    layer: "wilderness",
    current_node: "wild:2699:2699",
    nodes: [
      validLocalMapNode({ id: "wild:2699:2699", x: 2699, y: 2699 }),
      validLocalMapNode({
        id: "wild:2698:2699",
        label: "林地",
        x: 2698,
        y: 2699,
        visibility: "visible_unvisited",
        current: false,
        action: { kind: "move", exit_ref: "w", destination: "wild:2698:2699" },
      }),
    ],
    edges: [
      validLocalMapEdge({ source: "wild:2699:2699", destination: "wild:2698:2699" }),
    ],
  });
  assert.doesNotThrow(() => Protocol.validateLocalMapPanel(wilderness));

  // Malformed coordinates stay rejected: a fraction, a non-finite value, a
  // numeric string, and the envelope just past each bound.
  for (const bad of [
    { x: 100.5 },
    { x: Infinity },
    { y: NaN },
    { x: "100" },
    { x: -10000001 },
    { y: 10000001 },
  ]) {
    const node = validLocalMapNode(Object.assign({ x: 100, y: 0, current: true }, bad));
    assert.throws(
      () => Protocol.validateLocalMapPanel(validLocalMapPanel({ nodes: [node] })),
      JSON.stringify(bad)
    );
  }
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

test("requires exact gateway metadata: null or a bounded non-empty leads_to", () => {
  const LOCAL_MAP_MAX_STRING = Protocol.LOCAL_MAP_MAX_STRING;
  const panelWith = (gateway) =>
    validLocalMapPanel({ nodes: [validLocalMapNode({ gateway: gateway })], edges: [] });

  // Accepted forms normalize unchanged.
  for (const gateway of [null, { leads_to: "北境" }, { leads_to: "字".repeat(LOCAL_MAP_MAX_STRING) }]) {
    const normalized = Protocol.validateLocalMapPanel(panelWith(gateway));
    assert.deepEqual(normalized.nodes[0].gateway, gateway);
  }

  // Omission and an aliased key are rejected: no default, no alias.
  const omitted = validLocalMapNode();
  delete omitted.gateway;
  assert.throws(
    () => Protocol.validateLocalMapPanel(validLocalMapPanel({ nodes: [omitted], edges: [] })),
    /gateway/
  );
  const aliased = validLocalMapNode();
  delete aliased.gateway;
  aliased.gateway_leads_to = null;
  assert.throws(
    () => Protocol.validateLocalMapPanel(validLocalMapPanel({ nodes: [aliased], edges: [] })),
    /gateway/
  );

  for (const malformed of [
    undefined,
    "北境",
    0,
    false,
    [],
    [{ leads_to: "北境" }],
    {},
    { leads_to: "北境", label: "北境" },
    { to: "北境" },
    { leads_to: "" },
    { leads_to: "   " },
    { leads_to: null },
    { leads_to: 5 },
    { leads_to: ["北境"] },
    { leads_to: "字".repeat(LOCAL_MAP_MAX_STRING + 1) },
  ]) {
    assert.throws(
      () => Protocol.validateLocalMapPanel(panelWith(malformed)),
      /gateway|leads_to/,
      JSON.stringify(malformed)
    );
  }
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
        x: i % 2 === 0 ? Protocol.LOCAL_MAP_COORD_MIN : Protocol.LOCAL_MAP_COORD_MAX,
        y: i % 2 === 0 ? Protocol.LOCAL_MAP_COORD_MAX : Protocol.LOCAL_MAP_COORD_MIN,
        visibility: i === 0 ? "current" : "remembered",
        current: i === 0,
        // Realistic gateway metadata on every eighth node.
        gateway: i % 8 === 0 ? { leads_to: "測試遠方荒原" } : null,
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
        x: Protocol.LOCAL_MAP_COORD_MAX,
        y: Protocol.LOCAL_MAP_COORD_MIN,
        visibility: i === 0 ? "current" : "remembered",
        current: i === 0,
        gateway: { leads_to: label },
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

