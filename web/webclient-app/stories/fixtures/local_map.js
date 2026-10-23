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
// adjacent node whose `action` carries the OOB move intent. Every node
// carries the required `gateway` field: null, except the 南門 gate room,
// whose `{leads_to}` names the wilderness region its gate opens onto.
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
      gateway: null,
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
      gateway: { leads_to: "西部丘陵與谷地" },
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
    gateway: null,
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
    gateway: null,
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
  gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
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
      gateway: null,
      action: { kind: "move", exit_ref: "e_hall_training", destination: "room:202" },
    },
  ],
  edges: [
    { source: "room:201", destination: "room:202", label: "訓練場", known: true, traversable: true },
  ],
  legend: ["你目前所在的位置"],
};
// An ordinary town neighbourhood (webclient-map-legibility): a full
// three-by-three grid of distinct two- and four-glyph room names around the
// current square, connectors on all four sides, and no remembered gateway —
// the named fixture on which the island's node labels read at its 12px step
// (scale 1, pitch 59).
const ORDINARY_ROOMS = [
  [0, 2, "鐘樓", "visible_visited"],
  [1, 2, "北岸大道", "visible_unvisited"],
  [2, 2, "神殿", "visible_unvisited"],
  [0, 1, "西市", "visible_visited"],
  [1, 1, "石板廣場", "current"],
  [2, 1, "東門", "visible_unvisited"],
  [0, 0, "染坊", "visible_unvisited"],
  [1, 0, "西風酒館", "visible_visited"],
  [2, 0, "馬廄", "visible_unvisited"],
];

export const LOCAL_MAP_ORDINARY_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:1",
  title: "石板廣場街道圖",
  nodes: ORDINARY_ROOMS.map(([x, y, label, visibility]) => {
    const adjacent = Math.abs(x - 1) + Math.abs(y - 1) === 1;
    return {
      id: `grid:altoria:${x}:${y}`,
      label,
      x,
      y,
      visibility,
      current: visibility === "current",
      anchor: visibility === "current",
      landmark: label === "神殿",
      gateway: null,
      action: adjacent
        ? { kind: "move", exit_ref: `e_altoria_1_1_${x}_${y}`, destination: `grid:altoria:${x}:${y}` }
        : null,
    };
  }),
  edges: ORDINARY_ROOMS.filter(([x, y]) => Math.abs(x - 1) + Math.abs(y - 1) === 1).map(([x, y, label]) => ({
    source: "grid:altoria:1:1",
    destination: `grid:altoria:${x}:${y}`,
    label,
    known: true,
    traversable: true,
  })),
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// exploration-exit-compass: a synthesized `local_map` v1 panel around one
// current node, for the exit-compass stories. `neighbours` are
// `[id, label, x, y]` tuples; every value is a fixed literal.
export function localMapAround({ layer, current, neighbours = [] }) {
  const [currentId, currentLabel, cx, cy] = current;
  const node = ([id, label, x, y], isCurrent) => ({
    id,
    label,
    x,
    y,
    visibility: isCurrent ? "current" : "visible_unvisited",
    current: isCurrent,
    anchor: isCurrent,
    landmark: false,
    gateway: null,
    action: null,
  });
  return {
    schema_version: 1,
    available: true,
    layer,
    current_node: currentId,
    title: currentLabel,
    nodes: [node([currentId, currentLabel, cx, cy], true), ...neighbours.map((n) => node(n, false))],
    edges: neighbours.map(([id, label]) => ({
      source: currentId,
      destination: id,
      label,
      known: true,
      traversable: true,
    })),
    legend: [],
  };
}

// ---------------------------------------------------------------------------
// Metric island fixtures (render-auto-scaled-minimap-island; approved design
// docs/superpowers/specs/2026-10-22-minimap-auto-scale-design.md §8). The
// unit-coordinate samples above stay for the overlay and the coordinate-free
// stories; these reproduce what the settlement payloads actually carry since
// the metric cutover: integer-metre street coordinates and one-kilometre
// wilderness cells, so the island's automatic projection is exercised on the
// distances that used to push every exit off the canvas.
//
// The corpora are the authored coordinate tables of the world-map-scale design
// (docs/superpowers/specs/2026-10-21-world-map-scale-design.md §8 Altoria, 21
// nodes; §9 Ciaran, 10 nodes) with their authored roads (one entry per
// undirected road, the octant the first endpoint's exit faces). They are story
// data, not a request to reveal unseen nodes: each story renders a bounded
// payload view built the way the grid presenter builds one
// (web/webclient/presentation/local_map/grid.py): the current node, every node
// within two road hops, one star edge from the current node to each of them —
// the authored octant on a one-hop edge, an empty label on a two-hop one — and
// a move action on the one-hop nodes only.
// ---------------------------------------------------------------------------

const OPPOSITE_OCTANT = { n: "s", ne: "sw", e: "w", se: "nw", s: "n", sw: "ne", w: "e", nw: "se" };

// [key, label, x, y, anchor]
export const ALTORIA_METRIC_CORPUS = Object.freeze({
  map: "capital_altoria",
  nodes: [
    ["south_gate", "南門", 3050, 150, false],
    ["quay", "碼頭埠", 1250, 760, false],
    ["riverbank_road", "河岸道", 2150, 920, false],
    ["south_avenue", "南大道", 3140, 1050, false],
    ["inn_lane", "客棧巷", 3970, 1120, false],
    ["bath_forecourt", "浴場前", 4830, 970, false],
    ["old_wall_ruins", "舊城牆遺跡", 2350, 1900, false],
    ["north_avenue", "大道北段", 3350, 1980, false],
    ["craft_alley", "工匠巷", 1300, 2600, false],
    ["market_street", "市場街", 2420, 2700, false],
    ["central_plaza", "中央廣場", 3500, 2850, true],
    ["guild_forecourt", "公會前", 4380, 3000, false],
    ["east_market", "東市", 5380, 2850, false],
    ["east_gate", "東門", 6500, 3010, false],
    ["training_ground", "校場外", 2300, 3820, false],
    ["holy_steps", "聖階", 3480, 3700, false],
    ["great_temple", "大神殿前", 4560, 3920, false],
    ["noble_quarter", "貴族區前", 3500, 4850, false],
    ["upper_gate", "上城門", 4690, 5010, false],
    ["academy", "學院前", 5650, 5200, false],
    ["palace_forecourt", "王宮前庭", 4500, 6350, false],
  ],
  roads: [
    ["south_gate", "south_avenue", "n"],
    ["south_avenue", "north_avenue", "n"],
    ["north_avenue", "central_plaza", "n"],
    ["south_avenue", "riverbank_road", "w"],
    ["south_avenue", "inn_lane", "e"],
    ["riverbank_road", "quay", "w"],
    ["riverbank_road", "old_wall_ruins", "n"],
    ["old_wall_ruins", "market_street", "n"],
    ["old_wall_ruins", "north_avenue", "e"],
    ["inn_lane", "bath_forecourt", "e"],
    ["market_street", "craft_alley", "w"],
    ["craft_alley", "training_ground", "ne"],
    ["market_street", "central_plaza", "e"],
    ["central_plaza", "holy_steps", "n"],
    ["central_plaza", "guild_forecourt", "e"],
    ["holy_steps", "training_ground", "w"],
    ["holy_steps", "noble_quarter", "n"],
    ["holy_steps", "great_temple", "e"],
    ["guild_forecourt", "great_temple", "n"],
    ["guild_forecourt", "east_market", "e"],
    ["great_temple", "upper_gate", "n"],
    ["great_temple", "east_market", "se"],
    ["noble_quarter", "upper_gate", "e"],
    ["upper_gate", "palace_forecourt", "n"],
    ["upper_gate", "academy", "e"],
    ["east_market", "east_gate", "e"],
  ],
});

export const CIARAN_METRIC_CORPUS = Object.freeze({
  map: "village_ciaran",
  nodes: [
    ["hidden_path", "隱密小徑", 35, 270, false],
    ["village_plaza", "村中廣場", 220, 305, true],
    ["stream_path", "溪畔小徑", 245, 135, false],
    ["stream_bend", "溪畔下游", 430, 85, false],
    ["training_clearing", "練刀場", 405, 335, false],
    ["herb_garden", "藥草園", 590, 300, false],
    ["old_tree_north", "村北古樹下", 200, 465, false],
    ["elder_tree", "長老古樹下", 165, 650, false],
    ["weaving_slope", "織房坡", 390, 495, false],
    ["silver_leaf_slope", "銀葉坡", 440, 665, false],
  ],
  roads: [
    ["hidden_path", "village_plaza", "e"],
    ["stream_path", "village_plaza", "n"],
    ["stream_path", "stream_bend", "e"],
    ["village_plaza", "old_tree_north", "n"],
    ["village_plaza", "training_clearing", "e"],
    ["old_tree_north", "elder_tree", "n"],
    ["old_tree_north", "weaving_slope", "e"],
    ["elder_tree", "silver_leaf_slope", "e"],
    ["training_clearing", "herb_garden", "e"],
  ],
});

const METRIC_LEGEND = Object.freeze([
  "你目前所在的位置",
  "尚未探索的相鄰位置",
  "已經探索過的相鄰位置",
]);

// A bounded payload view of one corpus around `current`: every node within
// `hops` road hops, visited keys drawn as visited, one-hop nodes actionable.
// `gateways` maps a key to its `gateway` metadata; `extraNodes`/`extraEdges`
// append presenter-authored nodes (a gate's cross-layer target).
export function metricViewAround(corpus, current, options = {}) {
  const { hops = 2, visited = [], gateways = {}, extraNodes = [], extraEdges = [] } = options;
  const byKey = new Map(corpus.nodes.map((row) => [row[0], row]));
  const idOf = (key) => {
    const [, , x, y] = byKey.get(key);
    return `grid:${corpus.map}:${x}:${y}`;
  };
  const links = new Map();
  for (const [a, b, dir] of corpus.roads) {
    if (!links.has(a)) links.set(a, []);
    if (!links.has(b)) links.set(b, []);
    links.get(a).push([b, dir]);
    links.get(b).push([a, OPPOSITE_OCTANT[dir]]);
  }
  const depth = new Map([[current, 0]]);
  let frontier = [current];
  for (let step = 1; step <= hops; step += 1) {
    const next = [];
    for (const key of frontier) {
      for (const [other] of links.get(key) || []) {
        if (!depth.has(other)) {
          depth.set(other, step);
          next.push(other);
        }
      }
    }
    frontier = next;
  }
  const oneHop = new Map((links.get(current) || []).map(([other, dir]) => [other, dir]));
  const currentId = idOf(current);
  const nodes = [];
  const edges = [];
  for (const [key, label, x, y, anchor] of corpus.nodes) {
    if (!depth.has(key)) continue;
    const id = idOf(key);
    const isCurrent = key === current;
    const isExit = oneHop.has(key);
    nodes.push({
      id,
      label,
      x,
      y,
      visibility: isCurrent ? "current" : visited.includes(key) ? "visible_visited" : "visible_unvisited",
      current: isCurrent,
      anchor,
      landmark: anchor,
      gateway: gateways[key] ?? null,
      action: isExit ? { kind: "move", exit_ref: `e_${current}_${key}`, destination: id } : null,
    });
    if (!isCurrent) {
      edges.push({
        source: currentId,
        destination: id,
        label: isExit ? oneHop.get(key) : "",
        known: visited.includes(key),
        traversable: isExit,
      });
    }
  }
  // The current node leads the node list, as the presenter emits it.
  nodes.sort((a, b) => Number(b.current) - Number(a.current));
  const title = byKey.get(current)[1];
  return {
    schema_version: 1,
    available: true,
    layer: "grid",
    current_node: currentId,
    title: `${title}街道圖`,
    nodes: [...nodes, ...extraNodes],
    edges: [...edges, ...extraEdges],
    legend: [...METRIC_LEGEND],
  };
}

// Altoria's central plaza: four exits about 850–1,090 m away (design §3.6
// worked example, level 1500), a ring of two-hop streets, and the south
// gate the player once stood on, remembered as a gateway named for the
// region it opens onto (an edge-direction marker on the island's rim).
export const LOCAL_MAP_ALTORIA_PLAZA_SAMPLE = metricViewAround(ALTORIA_METRIC_CORPUS, "central_plaza", {
  visited: ["north_avenue", "south_avenue", "market_street"],
  extraNodes: [
    {
      id: "grid:capital_altoria:3050:150",
      label: "西部丘陵與谷地",
      x: 3050,
      y: 150,
      visibility: "remembered",
      current: false,
      anchor: false,
      landmark: true,
      gateway: { leads_to: "西部丘陵與谷地" },
      action: null,
    },
  ],
});

// Ciaran's village plaza: a ten-node hamlet whose exits are 150–200 m apart.
export const LOCAL_MAP_CIARAN_PLAZA_SAMPLE = metricViewAround(CIARAN_METRIC_CORPUS, "village_plaza", {
  visited: ["hidden_path"],
});

// Altoria's south gate (the city side of the gateway pair): one street exit
// 900 m north, two-hop streets around it, and the registered gate's
// cross-layer wilderness target at its renderer-local slot — one lattice
// divisor (70 m) south of the gate, the presenter's `_free_slot`. The island
// never draws that target as a node; its exit-stub descriptor waits for the
// gateway presentation (label-minimap-exits-and-gateways).
const SOUTH_GATE_WILD_TARGET = "wild:elosern:860:1076";
export const LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE = metricViewAround(ALTORIA_METRIC_CORPUS, "south_gate", {
  visited: ["south_avenue"],
  gateways: { south_gate: { leads_to: "西部丘陵與谷地" } },
  extraNodes: [
    {
      id: SOUTH_GATE_WILD_TARGET,
      label: "西部丘陵與谷地",
      x: 3050,
      y: 80,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      gateway: null,
      action: { kind: "move", exit_ref: "e_south_gate_wild", destination: SOUTH_GATE_WILD_TARGET },
    },
  ],
  extraEdges: [
    {
      source: "grid:capital_altoria:3050:150",
      destination: SOUTH_GATE_WILD_TARGET,
      label: "s",
      known: false,
      traversable: true,
    },
  ],
});

// A wilderness 3x3 neighbourhood: eight one-kilometre neighbours (1 km and
// 1.414 km, design §3.6: level 2000, radii 50 and 70.7). Cells sharing the
// current cell's region name keep the shared-name label suppression.
const WILD_DIRECTIONS = [
  ["n", 0, 1],
  ["ne", 1, 1],
  ["e", 1, 0],
  ["se", 1, -1],
  ["s", 0, -1],
  ["sw", -1, -1],
  ["w", -1, 0],
  ["nw", -1, 1],
];
const WILD_CENTRE = [858, 1071];
const WILD_REGION = "西部丘陵與谷地";
const WILD_NEIGHBOUR_REGION = { ne: "中央山脈", e: "中央山脈", se: "中央山脈" };
export const LOCAL_MAP_WILDERNESS_METRIC_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "wilderness",
  current_node: `wild:elosern:${WILD_CENTRE[0]}:${WILD_CENTRE[1]}`,
  title: WILD_REGION,
  nodes: [
    {
      id: `wild:elosern:${WILD_CENTRE[0]}:${WILD_CENTRE[1]}`,
      label: WILD_REGION,
      x: WILD_CENTRE[0],
      y: WILD_CENTRE[1],
      visibility: "current",
      current: true,
      anchor: false,
      landmark: false,
      gateway: null,
      action: null,
    },
    ...WILD_DIRECTIONS.map(([dir, dx, dy]) => {
      const x = WILD_CENTRE[0] + dx;
      const y = WILD_CENTRE[1] + dy;
      const id = `wild:elosern:${x}:${y}`;
      return {
        id,
        label: WILD_NEIGHBOUR_REGION[dir] ?? WILD_REGION,
        x,
        y,
        visibility: dir === "s" || dir === "sw" ? "visible_visited" : "visible_unvisited",
        current: false,
        anchor: false,
        landmark: false,
        gateway: null,
        action: { kind: "move", exit_ref: `e_wild_${dir}`, destination: id },
      };
    }),
  ],
  edges: WILD_DIRECTIONS.map(([dir, dx, dy]) => ({
    source: `wild:elosern:${WILD_CENTRE[0]}:${WILD_CENTRE[1]}`,
    destination: `wild:elosern:${WILD_CENTRE[0] + dx}:${WILD_CENTRE[1] + dy}`,
    label: dir,
    known: dir === "s" || dir === "sw",
    traversable: true,
  })),
  legend: [...METRIC_LEGEND, "每格約一公里"],
};

// An extreme distance ratio: a doorstep exit 80 m east beside a 1.2 km road
// north-west (design §3.6: compressed mode), plus a blocked exit and two
// two-hop places at either end of the range.
export const LOCAL_MAP_EXTREME_RATIO_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:frontier_post:2000:2000",
  title: "邊境驛站街道圖",
  nodes: [
    ["grid:frontier_post:2000:2000", "邊境驛站", 2000, 2000, "current", null],
    ["grid:frontier_post:2080:2000", "馬廄", 2080, 2000, "visible_visited", "e"],
    ["grid:frontier_post:1150:2850", "瞭望塔", 1150, 2850, "visible_unvisited", "nw"],
    ["grid:frontier_post:2000:1700", "舊哨所", 2000, 1700, "visible_unvisited", "s"],
    ["grid:frontier_post:2120:2010", "鐵匠鋪", 2120, 2010, "visible_unvisited", ""],
    ["grid:frontier_post:600:3400", "北嶺關", 600, 3400, "visible_unvisited", ""],
  ].map(([id, label, x, y, visibility, exit]) => ({
    id,
    label,
    x,
    y,
    visibility,
    current: visibility === "current",
    anchor: visibility === "current",
    landmark: visibility === "current",
    gateway: null,
    // 舊哨所's road is barred (a locked exit is still an exit).
    action: exit && id !== "grid:frontier_post:2000:1700" ? { kind: "move", exit_ref: `e_post_${exit}`, destination: id } : null,
  })),
  edges: [
    ["grid:frontier_post:2080:2000", "e", true],
    ["grid:frontier_post:1150:2850", "nw", true],
    ["grid:frontier_post:2000:1700", "s", false],
    ["grid:frontier_post:2120:2010", "", false],
    ["grid:frontier_post:600:3400", "", false],
  ].map(([destination, label, traversable]) => ({
    source: "grid:frontier_post:2000:2000",
    destination,
    label,
    known: destination === "grid:frontier_post:2080:2000",
    traversable,
  })),
  legend: [...METRIC_LEGEND],
};

// The central plaza with three remembered gateways on three rim sides, one
// with the presenter's disambiguated long form: every name is drawn whole on
// the island (beside its diamond or wrapped onto an inward row), never
// shortened.
const rememberedGate = (x, y, label, leadsTo) => ({
  id: `grid:capital_altoria:${x}:${y}`,
  label,
  x,
  y,
  visibility: "remembered",
  current: false,
  anchor: false,
  landmark: true,
  gateway: { leads_to: leadsTo },
  action: null,
});
export const LOCAL_MAP_ALTORIA_PLAZA_GATES_SAMPLE = metricViewAround(ALTORIA_METRIC_CORPUS, "central_plaza", {
  visited: ["north_avenue", "south_avenue", "market_street"],
  extraNodes: [
    rememberedGate(3050, 150, "西部丘陵與谷地（南門）", "西部丘陵與谷地"),
    rememberedGate(6500, 3010, "東部大平原", "東部大平原"),
    rememberedGate(4500, 6350, "西部丘陵與谷地（北門）", "西部丘陵與谷地"),
  ],
});
