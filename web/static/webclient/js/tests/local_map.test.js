/*
 * DOM-independent tests for the local-map render model (task 8.3).
 *
 * Runs with Node 24's built-in test runner and node:assert. Covers state
 * distinction without color alone, focus targets for remembered remote nodes,
 * the bounded integer lattice (with remembered nodes outside the canvas), and
 * the rank-compression fallback for geometrically sparse payloads.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const LocalMap = require("../elosern/local_map.js");

function node(overrides) {
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

function panel(overrides) {
  return Object.assign(
    {
      layer: "grid",
      current_node: "grid:capital_altoria:2:0",
      title: "南門街道圖",
      nodes: [
        node(),
        node({
          id: "grid:capital_altoria:2:1",
          label: "南大道",
          x: 2,
          y: 1,
          visibility: "visible_visited",
          current: false,
          action: { kind: "move", exit_ref: "42", destination: "grid:capital_altoria:2:1" },
        }),
        node({
          id: "grid:capital_altoria:0:3",
          label: "市場街",
          x: 0,
          y: 3,
          visibility: "remembered",
          current: false,
          action: null,
        }),
      ],
      edges: [
        {
          source: "grid:capital_altoria:2:0",
          destination: "grid:capital_altoria:2:1",
          label: "n",
          known: true,
          traversable: true,
        },
      ],
      legend: ["你目前所在的位置", "尚未探索的相鄰位置"],
    },
    overrides || {}
  );
}

test("distinguishes current, visible, and remembered states without color alone", () => {
  const model = LocalMap.reducePanel(panel());
  const current = model.nodes.find((n) => n.id === "grid:capital_altoria:2:0");
  const visible = model.nodes.find((n) => n.id === "grid:capital_altoria:2:1");
  const remembered = model.remembered.find((n) => n.id === "grid:capital_altoria:0:3");

  assert.equal(current.shape, "circle");
  assert.equal(current.border, "double");
  assert.notEqual(visible.shape, current.shape);
  assert.notEqual(visible.border, current.border);
  assert.equal(remembered.shape, "diamond");
  assert.equal(remembered.border, "dashed");
  // The label prefix provides a non-color text distinction.
  assert.notEqual(current.labelPrefix, visible.labelPrefix);
  assert.notEqual(visible.labelPrefix, remembered.labelPrefix);
  assert.equal(model.legend.length, 2);
});

test("in-view nodes occupy distinct lattice cells preserving relative order", () => {
  const model = LocalMap.reducePanel(panel());
  const current = model.nodes.find((n) => n.id === "grid:capital_altoria:2:0");
  const visible = model.nodes.find((n) => n.id === "grid:capital_altoria:2:1");
  assert.equal(current.col, 0);
  assert.equal(current.row, 0);
  assert.equal(visible.col, 0);
  assert.equal(visible.row, 1);
  assert.equal(model.cols, 1);
  assert.equal(model.rows, 2);
  // Distinct coordinates map to distinct cells.
  const cells = new Set(model.nodes.map((n) => n.col + ":" + n.row));
  assert.equal(cells.size, model.nodes.length);
});

test("remembered nodes never appear in nodes and never influence the lattice", () => {
  const model = LocalMap.reducePanel(panel());
  assert.equal(
    model.nodes.some((n) => n.visibility === "remembered"),
    false
  );
  assert.equal(model.remembered.length, 1);
  assert.equal(model.remembered[0].id, "grid:capital_altoria:0:3");
  // The lattice is computed only from the in-view nodes.
  assert.equal(model.cols, 1);
  assert.equal(model.rows, 2);
});

test("a distant remembered node leaves the local spacing intact", () => {
  const model = LocalMap.reducePanel(
    panel({
      nodes: [
        node(),
        node({
          id: "grid:capital_altoria:2:1",
          label: "南大道",
          x: 2,
          y: 1,
          visibility: "visible_visited",
          current: false,
        }),
        node({
          id: "grid:capital_altoria:50:40",
          label: "遙遠市場",
          x: 50,
          y: 40,
          visibility: "remembered",
          current: false,
          action: null,
        }),
      ],
    })
  );
  const current = model.nodes.find((n) => n.id === "grid:capital_altoria:2:0");
  const visible = model.nodes.find((n) => n.id === "grid:capital_altoria:2:1");
  assert.equal(current.col, 0);
  assert.equal(visible.row, 1);
  assert.equal(model.rows, 2);
  assert.equal(model.cols, 1);
  // The distant remembered node is in the list, not on the canvas.
  assert.equal(model.remembered.length, 1);
});

test("a geometrically sparse payload falls back to rank compression", () => {
  const nodes = [];
  for (let i = 0; i < 20; i += 1) {
    nodes.push(
      node({
        id: "room:" + i,
        label: "room " + i,
        x: i * 100,
        y: i * -100,
        visibility: i === 0 ? "current" : "visible_visited",
        current: i === 0,
      })
    );
  }
  const model = LocalMap.reducePanel(panel({ nodes: nodes, edges: [] }));
  assert.ok(model.cols <= LocalMap.MAX_LATTICE);
  assert.ok(model.rows <= LocalMap.MAX_LATTICE);
  assert.equal(model.nodes.length, 20);
  // Every node still renders exactly once, with rank-compressed coordinates.
  const cells = new Set(model.nodes.map((n) => n.col + ":" + n.row));
  assert.equal(cells.size, 20);
  // Relative order is preserved: larger x => larger col, smaller y => row.
  const first = model.nodes.find((n) => n.id === "room:0");
  const last = model.nodes.find((n) => n.id === "room:19");
  assert.ok(last.col > first.col);
  assert.ok(last.row < first.row);
});

test("a single-node payload yields a 1x1 lattice", () => {
  const model = LocalMap.reducePanel(
    panel({ nodes: [node()], edges: [] })
  );
  assert.equal(model.cols, 1);
  assert.equal(model.rows, 1);
  assert.equal(model.nodes[0].col, 0);
  assert.equal(model.nodes[0].row, 0);
});

test("remembered remote nodes carry no travel action and are focus targets", () => {
  const model = LocalMap.reducePanel(panel());
  const remembered = model.remembered[0];
  assert.equal(remembered.action, null);
  const target = model.focusTargets.find((t) => t.nodeId === remembered.id);
  assert.ok(target);
  assert.equal(target.label, "市場街");
  assert.equal(target.hasTravelAction, false);
  const adjacent = model.nodes.find((n) => n.id === "grid:capital_altoria:2:1");
  assert.ok(adjacent.action);
  assert.equal(adjacent.action.kind, "move");
});

test("focus targets are bounded", () => {
  const manyNodes = [];
  for (let i = 0; i < 64; i += 1) {
    manyNodes.push(
      node({
        id: "room:" + i,
        label: "room " + i,
        x: i,
        y: i,
        visibility: i === 0 ? "current" : "remembered",
        current: i === 0,
      })
    );
  }
  const model = LocalMap.reducePanel(
    panel({ nodes: manyNodes, edges: [] })
  );
  // The remembered list is bounded by the payload's node cap; the focus
  // targets derived from it are capped further.
  assert.ok(model.remembered.length <= LocalMap.MAX_NODES);
  assert.ok(model.focusTargets.length <= LocalMap.MAX_FOCUS_TARGETS);
});

test("an empty or missing panel reduces to an inert model", () => {
  const empty = LocalMap.reducePanel(null);
  assert.equal(empty.nodes.length, 0);
  assert.equal(empty.edges.length, 0);
  assert.equal(empty.remembered.length, 0);
  assert.equal(empty.focusTargets.length, 0);
  assert.equal(empty.cols, 0);
  assert.equal(empty.rows, 0);
});

// exitLabelFor (complete-ui-command-echo D3): unique traversable edge label,
// node-label fallback, parallel-edge ambiguity, and hard silence.
test("exitLabelFor returns the unique traversable edge label", () => {
  const model = LocalMap.reducePanel({
    current_node: "n1",
    nodes: [
      { id: "n1", label: "廣場", x: 0, y: 0, visibility: "in_view" },
      { id: "n2", label: "北門", x: 1, y: 0, visibility: "in_view" },
    ],
    edges: [
      { source: "n1", destination: "n2", label: "通往北門的石階", known: true, traversable: true },
    ],
    legend: [],
  });
  assert.equal(LocalMap.exitLabelFor(model, "n1", "n2"), "通往北門的石階");
});

test("exitLabelFor degrades parallel-edge ambiguity to the node label", () => {
  const model = LocalMap.reducePanel({
    current_node: "n1",
    nodes: [
      { id: "n1", label: "廣場", x: 0, y: 0, visibility: "in_view" },
      { id: "n2", label: "北門", x: 1, y: 0, visibility: "in_view" },
    ],
    edges: [
      { source: "n1", destination: "n2", label: "左階", known: true, traversable: true },
      { source: "n1", destination: "n2", label: "右階", known: true, traversable: true },
    ],
    legend: [],
  });
  assert.equal(LocalMap.exitLabelFor(model, "n1", "n2"), "北門");
});

test("exitLabelFor ignores non-traversable edges and stays silent without data", () => {
  const model = LocalMap.reducePanel({
    current_node: "n1",
    nodes: [
      { id: "n1", label: "廣場", x: 0, y: 0, visibility: "in_view" },
      { id: "n2", label: "北門", x: 1, y: 0, visibility: "in_view" },
    ],
    edges: [
      { source: "n1", destination: "n2", label: "封閉的門", known: true, traversable: false },
    ],
    legend: [],
  });
  assert.equal(LocalMap.exitLabelFor(model, "n1", "n2"), "北門");
  assert.equal(LocalMap.exitLabelFor(model, "n1", "n9"), null);
  assert.equal(LocalMap.exitLabelFor(null, "n1", "n2"), null);
  assert.equal(LocalMap.exitLabelFor(model, null, "n2"), null);
});
