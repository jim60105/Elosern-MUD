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

// ---------------------------------------------------------------------------
// Wave 2: radial placement, data-derived variant, edge direction markers.
// ---------------------------------------------------------------------------

const { RADIAL_GEOMETRY, variantForLayer, remoteDirection, edgeMarkersFor } = LocalMap;

// Renderer-true footprint boxes from design D1: marker x±9, y±9 and label
// 58x23 spanning y in [+3, +26] under the node origin. A pair overlaps when
// both axis overlaps are strict; >=1-unit separation is the contract.
const FOOTPRINTS = [
  { name: "marker/marker", dx: 9, dy: 9 },
  { name: "marker/label", dx: 29, dy: 17.5 },
  { name: "label/label", dx: 58, dy: 23 },
];

function radialFor(counts) {
  // Build a payload whose ring membership matches `counts`: the current node
  // plus ring members chained from the previous ring (ring r member j links
  // to ring r-1 member floor(j/2), keeping chains deterministic).
  const inView = [{ id: "current", visibility: "current", x: 0, y: 0, label: "current" }];
  const edges = [];
  for (let r = 1; r <= counts.length; r += 1) {
    for (let j = 0; j < counts[r - 1]; j += 1) {
      const id = `r${r}m${j}`;
      inView.push({ id, visibility: "visible_visited", x: 0, y: 0, label: id });
      const source = r === 1 ? "current" : `r${r - 1}m${Math.floor(j / 2)}`;
      edges.push({ source, destination: id, label: "e", known: true, traversable: true });
    }
  }
  return LocalMap.layoutRadial(inView, edges);
}

function footprintsViolating(layout) {
  const pts = layout.nodes.map((n) => ({ id: n.id, x: n.x, y: n.y }));
  const bad = [];
  for (let i = 0; i < pts.length; i += 1) {
    for (let j = i + 1; j < pts.length; j += 1) {
      const ox = Math.abs(pts[i].x - pts[j].x);
      const oy = Math.abs(pts[i].y - pts[j].y);
      for (const fp of FOOTPRINTS) {
        if (ox < fp.dx - 1e-9 && oy < fp.dy - 1e-9) {
          bad.push(`${pts[i].id}~${pts[j].id} ${fp.name} (${ox.toFixed(2)},${oy.toFixed(2)})`);
        }
      }
    }
  }
  return bad;
}

test("radial places rings by BFS hop distance over undirected edges", () => {
  const inView = [
    { id: "c", visibility: "current", x: 0, y: 0, label: "c" },
    { id: "a", visibility: "visible_visited", x: 1, y: 0, label: "a" },
    { id: "b", visibility: "visible_visited", x: 2, y: 0, label: "b" },
  ];
  const edges = [
    { source: "a", destination: "c", known: true, traversable: true },
    { source: "a", destination: "b", known: true, traversable: false },
  ];
  const layout = LocalMap.layoutRadial(inView, edges);
  const ring = Object.fromEntries(layout.nodes.map((n) => [n.id, n.ring]));
  assert.deepEqual(ring, { c: 0, a: 1, b: 2 });
  // Non-traversable topology still rings; reversed serialization does not
  // change membership.
  const reversed = LocalMap.layoutRadial(inView, [
    { source: "c", destination: "a", known: true, traversable: true },
    { source: "b", destination: "a", known: true, traversable: false },
  ]);
  assert.deepEqual(
    Object.fromEntries(reversed.nodes.map((n) => [n.id, n.ring])),
    ring
  );
  // A one-member ring is odd → the slot straddles up at 180 degrees: the
  // member sits on the downward axis at R0.
  const centre = layout.width / 2;
  const a = layout.nodes.find((n) => n.id === "a");
  assert.ok(Math.abs(a.radius - RADIAL_GEOMETRY.R0) < 1e-9);
  assert.ok(Math.abs(a.x - centre) < 1e-9 && a.y > centre);
});

test("radial layout is byte-identical across runs", () => {
  const counts = [5, 9, 2];
  assert.equal(JSON.stringify(radialFor(counts)), JSON.stringify(radialFor(counts)));
});

test("radial puts unreachable in-view nodes on the outermost ring", () => {
  const inView = [
    { id: "c", visibility: "current", x: 0, y: 0, label: "c" },
    { id: "a", visibility: "visible_visited", x: 1, y: 0, label: "a" },
    { id: "z1", visibility: "visible_unvisited", x: 5, y: 5, label: "z1" },
    { id: "z2", visibility: "visible_unvisited", x: 9, y: 1, label: "z2" },
  ];
  const edges = [{ source: "c", destination: "a", known: true, traversable: true }];
  const layout = LocalMap.layoutRadial(inView, edges);
  const ring = Object.fromEntries(layout.nodes.map((n) => [n.id, n.ring]));
  assert.deepEqual(ring, { c: 0, a: 1, z1: 1, z2: 1 });
  // Payload order preserved inside the fallback: z1 then z2 follow a.
  const slots = layout.nodes.filter((n) => n.ring === 1).map((n) => `${n.id}:${n.slot}`);
  assert.deepEqual(slots, ["a:0", "z1:1", "z2:2"]);
  // With nothing discovered at all, the fallback ring is ring 1.
  const edgeless = LocalMap.layoutRadial(
    [
      { id: "c", visibility: "current", x: 0, y: 0, label: "c" },
      { id: "x", visibility: "visible_visited", x: 3, y: 0, label: "x" },
    ],
    []
  );
  assert.deepEqual(
    Object.fromEntries(edgeless.nodes.map((n) => [n.id, n.ring])),
    { c: 0, x: 1 }
  );
});

test("radial gives current-only payloads a centre point and padded square", () => {
  for (const edges of [undefined, []]) {
    const layout = LocalMap.layoutRadial(
      [{ id: "c", visibility: "current", x: 7, y: -3, label: "c" }],
      edges
    );
    assert.equal(layout.nodes.length, 1);
    assert.equal(layout.nodes[0].ring, 0);
    assert.equal(layout.width, layout.height);
    assert.ok(layout.width > 0);
    assert.equal(layout.nodes[0].x, layout.width / 2);
    assert.equal(layout.nodes[0].y, layout.height / 2);
  }
});

test("radial keeps cycle and parallel-edge members on one ring", () => {
  const cycle = LocalMap.layoutRadial(
    [
      { id: "a", visibility: "current", x: 0, y: 0, label: "a" },
      { id: "b", visibility: "visible_visited", x: 1, y: 0, label: "b" },
      { id: "cc", visibility: "visible_visited", x: 0, y: 1, label: "cc" },
    ],
    [
      { source: "a", destination: "b", known: true, traversable: true },
      { source: "b", destination: "cc", known: true, traversable: true },
      { source: "cc", destination: "a", known: true, traversable: true },
    ]
  );
  assert.deepEqual(
    Object.fromEntries(cycle.nodes.map((n) => [n.id, n.ring])),
    { a: 0, b: 1, cc: 1 }
  );
  const parallel = LocalMap.layoutRadial(
    [
      { id: "a", visibility: "current", x: 0, y: 0, label: "a" },
      { id: "b", visibility: "visible_visited", x: 1, y: 0, label: "b" },
    ],
    [
      { source: "a", destination: "b", label: "left", known: true, traversable: true },
      { source: "a", destination: "b", label: "right", known: true, traversable: true },
    ]
  );
  assert.deepEqual(
    Object.fromEntries(parallel.nodes.map((n) => [n.id, n.ring])),
    { a: 0, b: 1 }
  );
});

test("variantForLayer resolves coordinate layers to lattice and the rest to graph", () => {
  assert.equal(variantForLayer("grid"), "lattice");
  assert.equal(variantForLayer("wilderness"), "lattice");
  for (const layer of ["interior", "instance", "town", "shop", "vehicle", "city", null, undefined, ""]) {
    assert.equal(variantForLayer(layer), "graph");
  }
  // reducePanel carries the resolver result verbatim.
  assert.equal(LocalMap.reducePanel(panel()).layoutVariant, "lattice");
  assert.equal(
    LocalMap.reducePanel(panel({ layer: "interior" })).layoutVariant,
    "graph"
  );
});

test("remoteDirection derives octants from raw deltas, +y north", () => {
  const cases = [
    [{ x: 0, y: 5 }, 0], // due north
    [{ x: 5, y: 0 }, 2], // due east
    [{ x: 0, y: -5 }, 4], // due south
    [{ x: -5, y: 0 }, 6], // due west
    [{ x: 4, y: 3 }, 1], // north-east
    [{ x: 4, y: -3 }, 3], // south-east
    [{ x: -4, y: -3 }, 5], // south-west
    [{ x: -4, y: 3 }, 7], // north-west
    [{ x: 4, y: 4 }, 1], // exact 45-degree boundary falls clockwise (NE)
    [{ x: -4, y: 4 }, 7],
    [{ x: 100, y: 1 }, 2], // shallow east stays E, not NE
    [{ x: 1, y: 100 }, 0],
    [{ x: -100, y: 1 }, 6],
    [{ x: 1, y: -100 }, 4],
    [{ x: -4, y: -1 }, 6], // shallow west-of-south reads W, not SW
    [{ x: -1, y: 4 }, 0], // 14 degrees west of north stays within N
    [{ x: 3, y: -4 }, 3],
    [{ x: -3, y: 4 }, 7],
  ];
  // The cases list raw deltas; the remote is offset from a non-zero origin
  // so the helper must derive the delta, not trust absolute coordinates.
  const origin = { x: -2, y: -7 };
  for (const [delta, octant] of cases) {
    const remote = { x: origin.x + delta.x, y: origin.y + delta.y };
    const dir = remoteDirection(origin, remote);
    assert.equal(dir.octant, octant, `octant for delta (${delta.x},${delta.y})`);
    assert.equal(dir.dx, delta.x);
    assert.equal(dir.dy, delta.y);
    assert.ok(dir.theta >= 0 && dir.theta < 360);
  }
});

function markerFixture(remembered) {
  // Grid payload at (5,5) with an in-view extent of x 3..7, y 3..7.
  const nodes = [];
  for (let x = 3; x <= 7; x += 1) {
    for (let y = 3; y <= 7; y += 1) {
      if (x === 5 && y === 5) {
        continue;
      }
      nodes.push({
        id: `grid:c:${x}:${y}`,
        label: `cell ${x},${y}`,
        x,
        y,
        visibility: "visible_visited",
      });
    }
  }
  nodes.push({ id: "grid:c:5:5", label: "南門", x: 5, y: 5, visibility: "current", current: true });
  const rem = (remembered || []).map((r, i) => ({
    id: `grid:c:${r.x}:${r.y}#r${i}`,
    label: r.label || `rem ${i}`,
    x: r.x,
    y: r.y,
    visibility: "remembered",
    landmark: !!r.landmark,
  }));
  return { nodes, remembered: rem };
}

function islandGeometry(overrides) {
  return Object.assign(
    { canvasWidth: 90, canvasHeight: 58, current: { x: 50, y: 30 }, markerHalf: 9 },
    overrides || {}
  );
}

test("edge markers only claim remembered nodes strictly off the extent", () => {
  const fixture = markerFixture([
    { x: 8, y: 10, label: "舊街區" }, // (+3,+5) -> NE, leaves through the top edge
    { x: 2, y: 5, label: "西關" }, // (-3, 0) -> W
    { x: 5, y: 12, label: "北隘口" }, // (0,+7) -> N
    { x: 4, y: 4, label: "in-view remembered" }, // inside the extent
    { x: 5, y: 5, label: "coincident" }, // zero-delta
  ]);
  const result = edgeMarkersFor(fixture.nodes, fixture.remembered, islandGeometry());
  assert.deepEqual(
    result.markers.map((m) => m.name).sort(),
    ["北隘口", "舊街區", "西關"]
  );
  const ne = result.markers.find((m) => m.name === "舊街區");
  assert.equal(ne.octant, 1);
  assert.equal(ne.dx, 3);
  assert.equal(ne.dy, 5);
  assert.equal(ne.side, "top");
  // In-view remembered and zero-delta never mark; the list entry is canonical.
  assert.ok(!result.markers.some((m) => m.name === "in-view remembered"));
  assert.ok(!result.markers.some((m) => m.name === "coincident"));
  // D3b: the canvas-side L1 tip sits exactly one unit outside the rect
  // (canvas origin at gutter,gutter).
  const reach = Math.SQRT2 * 9;
  assert.ok(ne.y < result.gutter, "top-side centre inside the gutter band");
  assert.ok(Math.abs(result.gutter - (ne.y + reach) - 1) < 1e-9, "tip hugs the rect");
});

test("edge markers stay silent without coordinates, extent, or candidates", () => {
  const fixture = markerFixture([{ x: 9, y: 8 }]);
  const geo = islandGeometry();
  // No remembered nodes at all.
  assert.equal(edgeMarkersFor(fixture.nodes, [], geo).markers.length, 0);
  // Coordinate-free payload: a direction claim would fabricate a place.
  const coordless = fixture.nodes.map((n) => Object.assign({}, n, { x: undefined, y: undefined }));
  assert.equal(edgeMarkersFor(coordless, fixture.remembered, geo).markers.length, 0);
  // Missing explicit geometry.
  assert.equal(edgeMarkersFor(fixture.nodes, fixture.remembered, null).markers.length, 0);
  assert.equal(
    edgeMarkersFor(fixture.nodes, fixture.remembered, { canvasWidth: 90, canvasHeight: 58 })
      .markers.length,
    0
  );
  // Everything remembered is inside the extent.
  const inside = markerFixture([{ x: 4, y: 4 }, { x: 5, y: 5 }]);
  assert.equal(edgeMarkersFor(inside.nodes, inside.remembered, geo).markers.length, 0);
});

test("edge markers never assume compressed ranks and stay deterministic", () => {
  // Sparse payload forcing the lattice rank-compression fallback: raw deltas
  // must still decide octants/edges — (100,1) is due east, never 45 degrees.
  const nodes = [
    { id: "c", label: "c", x: 0, y: 0, visibility: "current", current: true },
    { id: "far", label: "far", x: 100, y: 1, visibility: "visible_visited" },
  ];
  const compressed = LocalMap.layoutNodes(nodes);
  assert.equal(
    compressed.nodes.find((n) => n.id === "far").col,
    1,
    "rank compression would place x=100 one column from x=0"
  );
  const remembered = [
    // Strictly outside the in-view bbox (x 0..100, y 0..1); a remembered
    // node sharing the in-view cell is extent-interior and never marks.
    { id: "e1", label: "東關", x: 150, y: 1, visibility: "remembered" },
    { id: "e2", label: "南關", x: 0, y: -50, visibility: "remembered" },
  ];
  const geo = islandGeometry({ current: { x: 45, y: 29 } });
  const first = edgeMarkersFor(nodes, remembered, geo);
  const e1 = first.markers.find((m) => m.id === "e1");
  const e2 = first.markers.find((m) => m.id === "e2");
  assert.equal(e1.octant, 2); // due east from RAW delta, not the rank (1,1)
  assert.equal(e1.side, "right");
  assert.equal(e2.octant, 4);
  assert.equal(e2.side, "bottom");
  assert.equal(JSON.stringify(edgeMarkersFor(nodes, remembered, geo)), JSON.stringify(first));
});

test("edge marker packing clears every legal input at both surfaces", () => {
  // Mirrors design D3b: the rotate(45) diamond is an L1 ball of reach
  // sqrt(2) * markerHalf. Invariants at the shipped surface geometries:
  // (1) marker pairs stay L1-disjoint, (2) no L1 tip enters the canvas rect,
  // (3) marker + outward name box stay inside the outer rect.
  const surfaces = [
    { name: "island", cw: 90, ch: 58, mh: 9, nw: 0, nh: 0 },
    { name: "overlay", cw: 848, ch: 252, mh: 9 * 4.83, nw: 72, nh: 16 },
  ];
  for (const s of surfaces) {
    const reach = Math.SQRT2 * s.mh;
    const pad = s.nw || s.nh ? Math.max(s.nw, s.nh) + 2 : 0;
    const check = (result, label) => {
      const g = result.gutter;
      for (let i = 0; i < result.markers.length; i += 1) {
        for (let j = i + 1; j < result.markers.length; j += 1) {
          const a = result.markers[i];
          const b = result.markers[j];
          const l1 = Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
          assert.ok(
            l1 > 2 * reach - 1e-9,
            `${label}: ${a.id}~${b.id} L1=${l1.toFixed(2)} <= ${(2 * reach).toFixed(2)}`
          );
        }
      }
      for (const m of result.markers) {
        for (const [px, py] of [
          [m.x + reach, m.y], [m.x - reach, m.y], [m.x, m.y + reach], [m.x, m.y - reach],
        ]) {
          assert.ok(
            !(px >= g && px <= g + s.cw && py >= g && py <= g + s.ch),
            `${label}: ${m.id} tip (${px.toFixed(1)},${py.toFixed(1)}) enters canvas`
          );
        }
        assert.ok(
          m.x >= pad && m.x <= result.width - pad
            && m.y >= pad && m.y <= result.height - pad,
          `${label}: ${m.id} leaves the outer rect`
        );
      }
    };
    // Worst case: all 64 remembered nodes crowd a single edge, each surface.
    for (const edge of ["top", "bottom", "left", "right"]) {
      const current = { x: s.cw / 2, y: s.ch / 2 };
      const nodes = [{ id: "c", label: "c", x: current.x, y: current.y, visibility: "current" }];
      const remembered = [];
      for (let k = 0; k < 64; k += 1) {
        let dx;
        let dy;
        if (edge === "top") { dx = -30 + 0.9 * k; dy = 60; }
        else if (edge === "bottom") { dx = -30 + 0.9 * k; dy = -60; }
        else if (edge === "left") { dx = -60; dy = -30 + 0.9 * k; }
        else { dx = 60; dy = -30 + 0.9 * k; }
        remembered.push({ id: `r${k}`, label: `n${k}`, x: current.x + dx, y: current.y + dy });
      }
      check(
        edgeMarkersFor(nodes, remembered, {
          canvasWidth: s.cw, canvasHeight: s.ch, current,
          markerHalf: s.mh, nameWidth: s.nw, nameHeight: s.nh,
        }),
        `${s.name}/${edge} crowded`
      );
    }
    // Adjacent-edge corner pairs: extreme corner bearings must stay disjoint.
    const cur = { x: s.cw / 2, y: s.ch / 2 };
    const nodes = [{ id: "c", label: "c", x: cur.x, y: cur.y, visibility: "current" }];
    const corner = edgeMarkersFor(
      nodes,
      [
        // Rays straddling the top-left corner: one slightly steeper than the
        // corner (leaves through the top edge), one shallower (left edge).
        { id: "a", label: "a", x: cur.x - s.cw / 2, y: cur.y + s.ch / 2 + 1 },
        { id: "b", label: "b", x: cur.x - s.cw / 2 - 1, y: cur.y + s.ch / 2 },
      ],
      {
        canvasWidth: s.cw, canvasHeight: s.ch, current: cur,
        markerHalf: s.mh, nameWidth: s.nw, nameHeight: s.nh,
      }
    );
    check(corner, `${s.name} corner pair`);
    assert.deepEqual(corner.markers.map((m) => m.side).sort(), ["left", "top"]);
    // Deterministic pseudo-random stress across the payload bound.
    let seed = 12345;
    const rnd = () => {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return seed / 0x7fffffff;
    };
    for (let t = 0; t < 250; t += 1) {
      const origin = { x: 10 + rnd() * (s.cw - 20), y: 10 + rnd() * (s.ch - 20) };
      const count = 1 + Math.floor(rnd() * 64);
      const many = [{ id: "c", label: "c", x: origin.x, y: origin.y, visibility: "current" }];
      const rem = [];
      for (let i = 0; i < count; i += 1) {
        const angle = rnd() * Math.PI * 2;
        const dist = 60 + rnd() * 3940;
        rem.push({
          id: `r${i}`, label: `n${i}`,
          x: origin.x + dist * Math.cos(angle),
          y: origin.y + dist * Math.sin(angle),
        });
      }
      check(
        edgeMarkersFor(many, rem, {
          canvasWidth: s.cw, canvasHeight: s.ch, current: origin,
          markerHalf: s.mh, nameWidth: s.nw, nameHeight: s.nh,
        }),
        `${s.name} random #${t}`
      );
    }
  }
});

test("radial geometry contract survives every shape the 64-node payload yields", () => {
  // Pins the D1 recurrence directly (the contract the model implements).
  assert.equal(RADIAL_GEOMETRY.ARC, 67);
  assert.equal(RADIAL_GEOMETRY.R0, 72);
  assert.equal(RADIAL_GEOMETRY.G, 72);
  assert.equal(RADIAL_GEOMETRY.LABEL_BOTTOM, 26);
  assert.equal(RADIAL_GEOMETRY.PAD, 24);

  // (a) single ring, every legal member count m = 2..63: adjacent-slot chord
  // meets ARC and no footprint pair overlaps.
  for (let m = 2; m <= 63; m += 1) {
    const layout = radialFor([m]);
    const ring = layout.nodes.filter((n) => n.ring === 1);
    assert.equal(ring.length, m);
    for (let i = 1; i < m; i += 1) {
      const distance = Math.hypot(ring[i].x - ring[i - 1].x, ring[i].y - ring[i - 1].y);
      assert.ok(
        distance >= 67 - 1e-6,
        `m=${m} slot ${i - 1}~${i} chord ${distance.toFixed(3)} < ARC`
      );
    }
    assert.deepEqual(footprintsViolating(layout), [], `m=${m} footprint overlap`);
  }

  // (b) exhaustive adjacent ring-pair compositions (both rings exist), swept
  // through every relative-rotation the slotting produces.
  for (let m1 = 1; m1 <= 30; m1 += 1) {
    for (let m2 = 1; m2 <= 30; m2 += 1) {
      if (m1 + m2 > 63) {
        continue;
      }
      assert.deepEqual(
        footprintsViolating(radialFor([m1, m2])),
        [],
        `ring pair (${m1},${m2}) footprint overlap`
      );
    }
  }

  // (c) multi-ring compositions. Full enumeration of every composition of 63
  // into <=8 parts is ~1.4e8 layouts (infeasible); instead sweep EVERY
  // composition of totals 1..13 into <=8 parts exhaustively (7,098 layouts —
  // the dense regime where rings nearly touch), plus 40,000 deterministic
  // pseudo-random large compositions (totals 14..63, 2..8 rings), where the
  // G = 72 radial growth makes overlap structurally impossible.
  let swept = 0;
  const compositionsAt = (remaining, rings, prefix) => {
    if (remaining === 0) {
      if (prefix.length > 0) {
        swept += 1;
        assert.deepEqual(
          footprintsViolating(radialFor(prefix)),
          [],
          `composition ${prefix.join("+")} footprint overlap`
        );
      }
      return;
    }
    if (rings === 0) {
      return;
    }
    for (let m = 1; m <= remaining; m += 1) {
      compositionsAt(remaining - m, rings - 1, prefix.concat([m]));
    }
  };
  for (let total = 1; total <= 13; total += 1) {
    compositionsAt(total, 8, []);
  }
  assert.equal(swept, 7098, `small-composition sweep count ${swept}`);
  let seed = 999;
  const rnd = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  for (let t = 0; t < 40000; t += 1) {
    const total = 14 + Math.floor(rnd() * 50);
    const rings = 2 + Math.floor(rnd() * 7);
    const parts = new Array(rings).fill(1);
    for (let left = total - rings; left > 0; left -= 1) {
      parts[Math.floor(rnd() * rings)] += 1;
    }
    const composition = parts.filter((p) => p > 0);
    assert.deepEqual(
      footprintsViolating(radialFor(composition)),
      [],
      `random composition ${composition.join("+")} footprint overlap`
    );
  }

  // (d) adversarial stress shapes: the 63-ring hop-chain and the dense ring.
  const chain = radialFor(new Array(63).fill(1));
  assert.deepEqual(footprintsViolating(chain), []);
  assert.ok(chain.width > 9000 && chain.width < 9300, `chain side ${chain.width}`);
  const dense = radialFor([63]);
  assert.deepEqual(footprintsViolating(dense), []);
});

test("radial canvas size follows the D1 recurrence", () => {
  const layout = radialFor([8, 12]);
  const arcMin = (m) => 67 / (2 * Math.sin(Math.PI / m));
  const r1 = Math.max(RADIAL_GEOMETRY.R0, arcMin(8));
  const r2 = Math.max(r1 + RADIAL_GEOMETRY.G, arcMin(12));
  const expected = 2 * (r2 + RADIAL_GEOMETRY.LABEL_BOTTOM + RADIAL_GEOMETRY.PAD);
  assert.ok(Math.abs(layout.width - expected) < 1e-9);
  assert.ok(Math.abs(layout.height - expected) < 1e-9);
  for (const n of layout.nodes.filter((x) => x.ring === 2)) {
    assert.ok(Math.abs(n.radius - r2) < 1e-9);
  }
});
