// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The shared derived-shape helper (see `localMapModelFor` below) converts
// local_map fixtures exactly like `stores/elosern.js` builds
// `view.localMapModel` in production.
import LocalMapModel from "../../lib/local_map.js";

// ---------------------------------------------------------------------------
// B4 (webclient-vue-05-showcase-world): world + services family fixtures.
// Mirror the bounded OOB panel payloads — local_map v1, art v1, and
// services v2 — so the offline showcase asserts truthfulness: the lattice
// states, the art placeholder contract, the services-backed shop/quest/
// lore/inventory surfaces, and the equipped-only inventory (no full bag,
// no party panel — both deferred, roadmap §7). No live server, LLM, or
// imagegen data; every value is a fixed literal.
// ---------------------------------------------------------------------------

// The `local_map` v1 lattice: exactly one current node; adjacent nodes
// marked unvisited/visited, a remembered far node, edges with traversable
// states, the legend explaining every visibility state, and an actionable
// adjacent node whose `action` carries the OOB move intent.
export const LOCAL_MAP_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:2",
  title: "霧骨渡口",
  nodes: [
    {
      id: "grid:altoria:1:2",
      label: "霧骨渡口",
      x: 1,
      y: 2,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
    {
      id: "grid:altoria:2:2",
      label: "南門",
      x: 2,
      y: 2,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_altoria_1_2_e", destination: "grid:altoria:2:2" },
    },
    {
      id: "grid:altoria:0:2",
      label: "碼頭",
      x: 0,
      y: 2,
      visibility: "visible_visited",
      current: false,
      anchor: true,
      landmark: false,
      action: null,
    },
    {
      id: "grid:altoria:5:5",
      label: "舊街區",
      x: 5,
      y: 5,
      visibility: "remembered",
      current: false,
      anchor: false,
      landmark: true,
      action: null,
    },
  ],
  edges: [
    { source: "grid:altoria:1:2", destination: "grid:altoria:2:2", label: "南門", known: true, traversable: true },
    { source: "grid:altoria:1:2", destination: "grid:altoria:0:2", label: "碼頭", known: true, traversable: false },
    { source: "grid:altoria:1:2", destination: "grid:altoria:5:5", label: "遠方路網", known: false, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
    "曾經到過、但不在附近的遠方位置",
  ],
};

// The reduced lattice state: current node plus a single unvisited adjacent
// node (no action, one legend line) — the minimal truthful map.
export const LOCAL_MAP_MINIMAL_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:2",
  title: "霧骨渡口",
  nodes: [
    {
      id: "grid:altoria:1:2",
      label: "霧骨渡口",
      x: 1,
      y: 2,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
    {
      id: "grid:altoria:1:1",
      label: "北岸",
      x: 1,
      y: 1,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: null,
    },
  ],
  edges: [
    { source: "grid:altoria:1:2", destination: "grid:altoria:1:1", label: "北岸", known: false, traversable: true },
  ],
  legend: ["你目前所在的位置"],
};

// The registry-owned unavailable form for the map (a broken presenter, or
// a layer the player has not explored yet).
export const LOCAL_MAP_UNAVAILABLE_SAMPLE = {
  schema_version: 1,
  available: false,
  reason: { code: "map_unavailable", message: "區域地圖目前無法顯示" },
};

// The single shared story binding for every local_map component story (wave 0,
// webclient-map-00-story-fidelity design D1): the EXACT store-side conversion
// — byte-identical to `stores/elosern.js`'s `localMapModel` construction
// (`{ ...reducePanel(panel), available: panel.available !== false, reason:
// panel.reason }`). Stories of LocalMap / MapOverlay / MapLattice consume this
// helper's output, never a raw payload: the components' live prop is the
// reducer-derived model, and story args must reproduce that exact shape. The
// helper performs the store conversion and nothing else — it never mutates,
// duplicates, or synthesizes fixture data.
export function localMapModelFor(fixture) {
  return {
    ...LocalMapModel.reducePanel(fixture),
    available: fixture.available !== false,
    reason: fixture.reason,
  };
}

// The maximal-height, minimal-width lattice (task 3.5): exactly 64 in-view
// nodes — one node per row across 64 rows, alternating the two columns
// (x = y % 2) — a schema-valid worst-case tall map sitting exactly at the
// model's 64-node bound. The renderer must scale the canvas down to fit
// the island's bounded height instead of forcing the island to scroll a
// required surface out of view. Every 16th row carries a 6-CJK label so the
// truncation path (LABEL_MAX chars + ellipsis) is exercised.
const TALL_LATTICE_ROWS = 64;
const TALL_LATTICE_NODES = Array.from({ length: TALL_LATTICE_ROWS }, (_, y) => {
  const x = y % 2;
  const isCurrent = y === 32;
  return {
    id: `grid:altoria:${x}:${y}`,
    label: y % 16 === 0 ? "霧骨渡口碼頭" : `渡口${y % 8}`,
    x,
    y,
    visibility: isCurrent ? "current" : "visible_unvisited",
    current: isCurrent,
    anchor: isCurrent,
    landmark: isCurrent,
    action: null,
  };
});

export const LOCAL_MAP_TALL_LATTICE_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:0:32",
  title: "霧骨渡口",
  nodes: TALL_LATTICE_NODES,
  edges: [
    { source: "grid:altoria:0:32", destination: "grid:altoria:1:33", label: "北岸", known: true, traversable: true },
    { source: "grid:altoria:0:32", destination: "grid:altoria:1:31", label: "南門", known: true, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// The tall-lattice + long-remembered-list combination (rubber-duck blocking
// issue): 48 in-view nodes (2 cols × 48 rows) + 16 remembered far nodes =
// 64 nodes total, hitting the model's MAX_NODES bound. The island's
// dynamically measured canvas height cap must reserve space for the
// remembered list so the anchor never scrolls.
const TALL_REMEMBERED_INVIEW_NODES = Array.from({ length: 48 }, (_, y) => {
  const x = y % 2;
  const isCurrent = y === 24;
  return {
    id: `grid:altoria:${x}:${y}`,
    label: y % 16 === 0 ? "霧骨渡口碼頭" : `渡口${y % 8}`,
    x,
    y,
    visibility: isCurrent ? "current" : "visible_unvisited",
    current: isCurrent,
    anchor: isCurrent,
    landmark: isCurrent,
    action: null,
  };
});

const TALL_REMEMBERED_FAR_NODES = Array.from({ length: 16 }, (_, i) => ({
  id: `grid:altoria:${5 + i % 6}:${100 + i}`,
  label: "遠方路網",
  x: 5 + i % 6,
  y: 100 + i,
  visibility: "remembered",
  current: false,
  anchor: false,
  landmark: true,
  action: null,
}));

export const LOCAL_MAP_TALL_REMEMBERED_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:0:24",
  title: "霧骨渡口",
  nodes: [...TALL_REMEMBERED_INVIEW_NODES, ...TALL_REMEMBERED_FAR_NODES],
  edges: [
    { source: "grid:altoria:0:24", destination: "grid:altoria:1:25", label: "北岸", known: true, traversable: true },
    { source: "grid:altoria:0:24", destination: "grid:altoria:1:23", label: "南門", known: true, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// The dedicated geometry-stress fixture (rubber-duck critique): horizontally
// and vertically adjacent nodes, the current 26×26 rect and the stroked
// `visible_unvisited` circle (visual half-extent 13px including stroke), 4-
// CJK labels (truncated at LABEL_MAX with an ellipsis when longer), and two
// adjacent connector edges. It pins the pre-scale non-intersection invariant
// at the renderer's own pitch constants.
export const LOCAL_MAP_GEOMETRY_STRESS_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:1",
  title: "霧骨渡口",
  nodes: [
    {
      id: "grid:altoria:1:1",
      label: "霧骨渡口",
      x: 1,
      y: 1,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
    {
      id: "grid:altoria:2:1",
      label: "南門街道市場",
      x: 2,
      y: 1,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_altoria_1_1_e", destination: "grid:altoria:2:1" },
    },
    {
      id: "grid:altoria:1:2",
      label: "碼頭廣場舊街",
      x: 1,
      y: 2,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: null,
    },
    {
      id: "grid:altoria:0:1",
      label: "旅館公會",
      x: 0,
      y: 1,
      visibility: "visible_visited",
      current: false,
      anchor: true,
      landmark: false,
      action: null,
    },
  ],
  edges: [
    { source: "grid:altoria:1:1", destination: "grid:altoria:2:1", label: "南門", known: true, traversable: true },
    { source: "grid:altoria:1:1", destination: "grid:altoria:1:2", label: "碼頭", known: true, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// The single-node room (delta spec scenario "A single-node room states
// orientation without any collision risk"): exactly one current node, no
// neighbors to collide with — the pitch/sizing change must produce no
// regression for the single-node case.
export const LOCAL_MAP_SINGLE_NODE_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:1",
  title: "霧骨渡口",
  nodes: [
    {
      id: "grid:altoria:1:1",
      label: "霧骨渡口",
      x: 1,
      y: 1,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
  ],
  edges: [],
  legend: ["你目前所在的位置"],
};

// The wilderness layer: coordinate-bearing nodes (the renderer-axis
// orientation legend 北↑ applies).
export const LOCAL_MAP_WILDERNESS_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "wilderness",
  current_node: "wild:plains:3:1",
  title: "灰鬮荒原",
  nodes: [
    {
      id: "wild:plains:3:1",
      label: "灰鬮荒原",
      x: 3,
      y: 1,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
    {
      id: "wild:plains:4:1",
      label: "獵人小徑",
      x: 4,
      y: 1,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_plains_3_1_e", destination: "wild:plains:4:1" },
    },
    {
      id: "wild:plains:2:2",
      label: "舊營地",
      x: 2,
      y: 2,
      visibility: "visible_visited",
      current: false,
      anchor: false,
      landmark: true,
      action: null,
    },
    {
      id: "wild:plains:7:5",
      label: "遠處山徑",
      x: 7,
      y: 5,
      visibility: "remembered",
      current: false,
      anchor: false,
      landmark: true,
      action: null,
    },
  ],
  edges: [
    { source: "wild:plains:3:1", destination: "wild:plains:4:1", label: "獵人小徑", known: true, traversable: true },
    { source: "wild:plains:3:1", destination: "wild:plains:2:2", label: "舊營地", known: true, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// The instance layer: the presenter's layout-index coordinates (a
// coordinate-free graph — the orientation legend is omitted).
export const LOCAL_MAP_INSTANCE_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "instance",
  current_node: "room:101",
  title: "洞窟",
  nodes: [
    {
      id: "room:101",
      label: "洞窟入口",
      x: 0,
      y: 0,
      visibility: "current",
      current: true,
      anchor: false,
      landmark: false,
      action: null,
    },
    {
      id: "room:102",
      label: "南門",
      x: 0,
      y: 1,
      visibility: "visible_visited",
      current: false,
      anchor: false,
      landmark: false,
      action: null,
    },
    {
      id: "room:103",
      label: "未探索",
      x: 1,
      y: 0,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_cave_exit", destination: "room:103" },
    },
  ],
  edges: [
    { source: "room:101", destination: "room:102", label: "回程", known: true, traversable: true },
    { source: "room:101", destination: "room:103", label: "進洞窟", known: false, traversable: true },
  ],
  legend: ["你目前所在的位置", "尚未探索的相鄰位置"],
};

// The interior layer: the same layout-index coordinate shape as instance
// (coordinate-free graph — the orientation legend is omitted).
export const LOCAL_MAP_INTERIOR_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "interior",
  current_node: "room:201",
  title: "公會大廳",
  nodes: [
    {
      id: "room:201",
      label: "公會大廳",
      x: 0,
      y: 0,
      visibility: "current",
      current: true,
      anchor: false,
      landmark: false,
      action: null,
    },
    {
      id: "room:202",
      label: "訓練場",
      x: 1,
      y: 0,
      visibility: "visible_visited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_hall_training", destination: "room:202" },
    },
  ],
  edges: [
    { source: "room:201", destination: "room:202", label: "訓練場", known: true, traversable: true },
  ],
  legend: ["你目前所在的位置"],
};