/*
 * DOM-independent tests for the local-map render model (task 4.2).
 *
 * Runs with Node 24's built-in test runner and node:assert. Covers state
 * distinction without color alone, focus targets for remembered remote nodes,
 * and bounded rendering.
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
  const remembered = model.nodes.find((n) => n.id === "grid:capital_altoria:0:3");

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

test("remembered remote nodes carry no travel action and are focus targets", () => {
  const model = LocalMap.reducePanel(panel());
  const remembered = model.nodes.find((n) => n.visibility === "remembered");
  assert.equal(remembered.action, null);
  const target = model.focusTargets.find((t) => t.nodeId === remembered.id);
  assert.ok(target);
  assert.equal(target.label, "市場街");
  assert.equal(target.hasTravelAction, false);
  const adjacent = model.nodes.find((n) => n.id === "grid:capital_altoria:2:1");
  assert.ok(adjacent.action);
  assert.equal(adjacent.action.kind, "move");
});

test("bounded rendering clamps coordinates and caps focus targets", () => {
  const manyNodes = [];
  const maxNodes = 64;
  for (let i = 0; i < maxNodes; i++) {
    manyNodes.push(
      node({
        id: "room:" + i,
        label: "room " + i,
        x: i * 1000,
        y: -i * 1000,
        visibility: i === 0 ? "current" : "remembered",
        current: i === 0,
      })
    );
  }
  const model = LocalMap.reducePanel(
    panel({ nodes: manyNodes, edges: [] })
  );
  assert.ok(model.nodes.length <= LocalMap.MAX_LAYOUT_X * 2 + 1);
  assert.ok(model.focusTargets.length <= LocalMap.MAX_FOCUS_TARGETS);
  model.nodes.forEach((n) => {
    assert.ok(n.x >= -LocalMap.MAX_LAYOUT_X && n.x <= LocalMap.MAX_LAYOUT_X);
    assert.ok(n.y >= -LocalMap.MAX_LAYOUT_Y && n.y <= LocalMap.MAX_LAYOUT_Y);
  });
});

test("an empty or missing panel reduces to an inert model", () => {
  const empty = LocalMap.reducePanel(null);
  assert.equal(empty.nodes.length, 0);
  assert.equal(empty.edges.length, 0);
  assert.equal(empty.focusTargets.length, 0);
});
