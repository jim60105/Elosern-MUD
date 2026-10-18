/*
 * lineage panel: JS validator mirror boundary tests.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_FIREARROW, T_FIRE_LABEL, T_SKILL_LABEL } = require("./protocol_support.js");


function validLineageNode(key, overrides) {
  return Object.assign(
    {
      skill_key: key,
      display_name_zh: T_SKILL_LABEL,
      owned: true,
      usable: true,
      ready: false,
      level: 1,
      xp_into_level: 23,
      xp_to_next_level: 27,
      capped: false,
      prereq_text_zh: "",
      depth: 0,
    },
    overrides || {}
  );
}

function validLineageGraph(root, nodeCount, overrides) {
  const count = nodeCount === undefined ? 2 : nodeCount;
  const nodes = count >= 1 ? [validLineageNode(root)] : [];
  for (let index = 1; index < count; index += 1) {
    nodes.push(validLineageNode(`${root}_n${index}`, { depth: index }));
  }
  const edges = [];
  for (let index = 1; index < count; index += 1) {
    edges.push({
      from_key: nodes[index - 1].skill_key,
      to_key: nodes[index].skill_key,
      min_level: 1,
    });
  }
  return Object.assign(
    {
      graph_id: root,
      group_label_zh: T_FIRE_LABEL,
      root_keys: count >= 1 ? [root] : [],
      owned_count: count,
      total_count: count,
      consumed: false,
      nodes: nodes,
      edges: edges,
    },
    overrides || {}
  );
}

function validLineagePanel(graphs, completed, total) {
  const list = graphs === undefined ? [validLineageGraph(T_FIREARROW)] : graphs;
  return {
    schema_version: 2,
    available: true,
    kind: "lineage",
    completed_count: completed === undefined ? 0 : completed,
    total_count: total === undefined ? list.length : total,
    graphs: list,
  };
}

test("lineage validates the minimal available payload and pins its caps", () => {
  assert.equal(Protocol.LINEAGE_MAX_GRAPHS, 16);
  assert.equal(Protocol.LINEAGE_MAX_NODES_PER_GRAPH, 32);
  assert.equal(Protocol.LINEAGE_MAX_EDGES_PER_GRAPH, 64);
  assert.equal(Protocol.LINEAGE_MAX_TEXT, 128);
  assert.equal(Protocol.PANEL_ALLOWLIST.lineage, 2);
  const normalized = Protocol.validatePanel(
    "lineage",
    Protocol.PANEL_ALLOWLIST.lineage,
    validLineagePanel()
  );
  assert.equal(normalized.kind, "lineage");
  assert.equal(normalized.graphs[0].graph_id, T_FIREARROW);
  assert.deepEqual(normalized.graphs[0].root_keys, [T_FIREARROW]);
});

test("lineage rejects a wrong kind or schema_version", () => {
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { kind: "character" }))
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { schema_version: 1 }))
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { schema_version: 3 }))
  );
  assert.throws(() =>
    Protocol.validateLineagePanel({ ...validLineagePanel(), extra: true })
  );
});

test("lineage rejects completed_count above total_count", () => {
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel(undefined, 2, 1)));
});

test("lineage available form rejects a false or non-boolean discriminator", () => {
  // Rubber-duck R2-2: the exported validator must mirror Python's
  // validate_lineage, which requires available === true in this form.
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { available: false }))
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { available: "true" }))
  );
});

test("lineage caps graph, node and edge counts at the mirrored bounds", () => {
  const atCap = [];
  for (let index = 0; index < Protocol.LINEAGE_MAX_GRAPHS; index += 1) {
    atCap.push(validLineageGraph(`root_${index}`, 1));
  }
  assert.doesNotThrow(() => Protocol.validateLineagePanel(validLineagePanel(atCap)));
  atCap.push(validLineageGraph("root_over", 1));
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel(atCap)));

  assert.doesNotThrow(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([
        validLineageGraph("root_a", Protocol.LINEAGE_MAX_NODES_PER_GRAPH),
      ])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([
        validLineageGraph("root_a", Protocol.LINEAGE_MAX_NODES_PER_GRAPH + 1),
      ])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(validLineagePanel([validLineageGraph("root_a", 0)]))
  );

  const keys = ["root_a"];
  for (let index = 1; index < Protocol.LINEAGE_MAX_NODES_PER_GRAPH; index += 1) {
    keys.push(`node_${index}`);
  }
  const nodes = keys.map((key) => validLineageNode(key));
  const edges = [];
  for (const offset of [1, 2]) {
    for (let index = 0; index < keys.length; index += 1) {
      edges.push({
        from_key: keys[index],
        to_key: keys[(index + offset) % keys.length],
        min_level: 1,
      });
    }
  }
  assert.equal(edges.length, Protocol.LINEAGE_MAX_EDGES_PER_GRAPH);
  const atEdgeCap = validLineageGraph("root_a", 1, {
    nodes: nodes,
    edges: edges,
    total_count: nodes.length,
    owned_count: nodes.length,
  });
  assert.doesNotThrow(() =>
    Protocol.validateLineagePanel(validLineagePanel([atEdgeCap]))
  );
  const overEdgeCap = validLineageGraph("root_a", 1, {
    nodes: nodes,
    edges: edges.concat([
      { from_key: "node_1", to_key: "root_a", min_level: 1 },
    ]),
    total_count: nodes.length,
    owned_count: nodes.length,
  });
  assert.throws(() =>
    Protocol.validateLineagePanel(validLineagePanel([overEdgeCap]))
  );
});

test("lineage bounds text lengths", () => {
  const tooLong = "測".repeat(Protocol.LINEAGE_MAX_TEXT + 1);
  assert.throws(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([
        validLineageGraph("root_a", 1, {
          nodes: [validLineageNode("root_a", { display_name_zh: tooLong })],
        }),
      ])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([
        validLineageGraph("root_a", 1, {
          nodes: [validLineageNode("root_a", { prereq_text_zh: tooLong })],
        }),
      ])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([validLineageGraph("root_a", 1, { group_label_zh: tooLong })])
    )
  );
});

test("lineage graphs keep their declared head and closed edges", () => {
  const graph = validLineageGraph("root_a", 2);
  graph.root_keys = ["root_a_n1"];
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel([graph])));
  const dangling = validLineageGraph("root_a", 2);
  dangling.edges = [{ from_key: "root_a", to_key: "absent", min_level: 1 }];
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel([dangling])));
  const selfEdge = validLineageGraph("root_a", 2);
  selfEdge.edges = [{ from_key: "root_a", to_key: "root_a", min_level: 1 }];
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel([selfEdge])));
});

test("lineage byte budget fails closed on the theoretical worst case", () => {
  // All ceilings at once serialize past the 65,536-byte envelope; the
  // validator enforces serialized size (the presenter truncates instead).
  const graphs = [];
  for (let index = 0; index < Protocol.LINEAGE_MAX_GRAPHS; index += 1) {
    const root = `root_${index}`;
    const nodes = [];
    for (let nodeIndex = 0; nodeIndex < Protocol.LINEAGE_MAX_NODES_PER_GRAPH; nodeIndex += 1) {
      nodes.push(
        validLineageNode(nodeIndex === 0 ? root : `n${index}_${nodeIndex}`, {
          display_name_zh: "測".repeat(Protocol.LINEAGE_MAX_TEXT),
          depth: nodeIndex,
        })
      );
    }
    graphs.push(
      validLineageGraph(root, 1, {
        nodes: nodes,
        total_count: nodes.length,
        owned_count: nodes.length,
      })
    );
  }
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel(graphs)));
});

test("lineage unavailable form validates through the common discriminator", () => {
  const unavailable = {
    schema_version: 2,
    available: false,
    reason: { code: "lineage_unavailable", message: "技能系譜目前無法顯示" },
  };
  assert.deepEqual(
    Protocol.validatePanel("lineage", Protocol.PANEL_ALLOWLIST.lineage, unavailable),
    unavailable
  );
});

