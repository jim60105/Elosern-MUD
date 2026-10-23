"use strict";

// Exact version-1 area_map / world_map logical schemas (OpenSpec change
// define-map-panel-protocol). Mirror of web/webclient/presentation/map_panels.py:
// every constant, vocabulary and rule below must stay equal to the server
// validator; a bidirectional Python/Node parity test pins them.
//
// The area ceilings are the values publish-area-map-panel measured and owns;
// the world ceilings are the values transport-world-map-panel measured and
// owns (docs/development/map-panel-protocol.md). Unrelated panels keep their
// own budgets.

var core = require("../core.js");

var codePoints = core.codePoints;
var isPlainObject = core.isPlainObject;
var validateIdentifier = core.validateIdentifier;
var validateMessage = core.validateMessage;
var validateCorrelationId = core.validateCorrelationId;

var MAX_SAFE_INTEGER = 9007199254740991;
var MAX_DEPTH = 12;
var MAX_FIELDS = 64;
var MAX_STRING_CODE_POINTS = 2048;

var AREA_MAP_SCHEMA_VERSION = 1;
var WORLD_MAP_SCHEMA_VERSION = 1;
var MAP_PANEL_SCHEMAS = { area_map: AREA_MAP_SCHEMA_VERSION, world_map: WORLD_MAP_SCHEMA_VERSION };

var MAP_MAX_LABEL = 256;
var MAP_MAX_TITLE = 128;
var MAP_MAX_NODE_ID = 128;
var MAP_MAX_EXIT_REF = 64;
var MAP_MAX_ID = 64;
var MAP_MAX_QUEST_ID = 64;
var MAP_COORD_MIN = -10000000;
var MAP_COORD_MAX = 10000000;
var MAP_MAX_LIST_ITEMS = 8192;
var MAP_PANEL_DEPTH = 2;

var AREA_MAX_NODES = 512;
var AREA_MAX_EDGES = 2048;
var AREA_MAX_QUEST_MARKERS = 32;
var AREA_MAX_BYTES = 393216;
var WILDERNESS_WINDOW = 15;
var WILDERNESS_MAX_NODES = WILDERNESS_WINDOW * WILDERNESS_WINDOW;
var AREA_MAX_CELL_KM = 1000;

var WORLD_MAX_BYTES = 1048576;
var WORLD_MAX_POLYGON_POINTS = 8192;
var WORLD_MAX_POLYLINE_POINTS = 4096;
var WORLD_MAX_BORDERS = 256;
var WORLD_MAX_NATIONS = 32;
var WORLD_MAX_DISTRICTS = 256;
var WORLD_MAX_OUTLINE_POLYGONS = 64;
var WORLD_MAX_TERRAIN_REGIONS = 64;
var WORLD_MAX_DISTRICT_POLYLINES = 256;
var WORLD_MAX_PLACES = 256;
var WORLD_MAX_DISTRICT_NATIONS = 8;
var WORLD_MAX_QUEST_MARKERS = 64;
var WORLD_APPROXIMATE_GRID_KM = 50;
var TRAIL_RESOLUTIONS = [1, 5];
var TRAIL_FRAME_CELLS = 2700;
var TRAIL_MAX_RUNS = 20000;

var MAP_MAX_BYTES = { area_map: AREA_MAX_BYTES, world_map: WORLD_MAX_BYTES };

var AREA_LAYERS = ["grid", "instance", "interior", "wilderness"];
var AREA_VISIBILITIES = ["current", "visited", "seen"];
var AREA_ACTION_KINDS = ["move"];
var AREA_FRAME_UNITS = { grid: "m", instance: "none", interior: "none", wilderness: "km" };
var WILDERNESS_MAP_ID = "elosern";
var PLACE_KINDS = ["capital", "settlement", "harbour", "hidden"];

var MAP_NODE_ID_RE =
  /^(?:grid:[A-Za-z0-9_.-]{1,64}:(?:0|[1-9][0-9]*):(?:0|[1-9][0-9]*)|wild:elosern:(?:0|[1-9][0-9]*):(?:0|[1-9][0-9]*)|room:[1-9][0-9]*)$/;
var GRID_MAP_ID_RE = /^[A-Za-z0-9_.-]{1,64}$/;
var ROOM_GRAPH_MAP_ID_RE = /^[A-Za-z0-9_.:-]{1,128}$/;
var MAP_ID_RE = /^[a-z0-9._]{1,64}$/;
// eslint-disable-next-line no-control-regex
var EXIT_REF_RE = /^[\x00-\x7f]{1,64}$/;

function fail(message) {
  throw new Error(message);
}

function has(object, key) {
  return Object.prototype.hasOwnProperty.call(object, key);
}

function exact(value, name, fields) {
  if (!isPlainObject(value)) {
    fail(name + " must be a JSON object");
  }
  var keys = Object.keys(value);
  if (keys.length !== fields.length || !fields.every(function (field) { return has(value, field); })) {
    fail(name + " fields mismatch");
  }
  return value;
}

function list(value, name, minimum, maximum) {
  if (!Array.isArray(value)) {
    fail(name + " must be a list");
  }
  if (value.length < minimum || value.length > maximum) {
    fail(name + " must hold " + minimum + ".." + maximum + " entries");
  }
  return value;
}

function bool(value, name) {
  if (typeof value !== "boolean") {
    fail(name + " must be a boolean");
  }
  return value;
}

function int(value, name, minimum, maximum) {
  if (typeof value !== "number" || !Number.isInteger(value)) {
    fail(name + " must be an integer");
  }
  if (value < minimum || value > maximum) {
    fail(name + " must be within " + minimum + ".." + maximum);
  }
  // -0 decodes from "-0"/"-0.0"; it is the integer 0 on both sides.
  return value === 0 ? 0 : value;
}

function number(value, name, minimum, maximum) {
  if (minimum === undefined) minimum = MAP_COORD_MIN;
  if (maximum === undefined) maximum = MAP_COORD_MAX;
  if (typeof value !== "number" || !isFinite(value)) {
    fail(name + " must be a finite number");
  }
  if (value < minimum || value > maximum) {
    fail(name + " must be within " + minimum + ".." + maximum);
  }
  return value;
}

function text(value, name, maximum) {
  if (typeof value !== "string") {
    fail(name + " must be a string");
  }
  if (codePoints(value) > maximum || !value.trim()) {
    fail(name + " must be 1.." + maximum + " non-blank code points");
  }
  return value;
}

function nodeId(value, name) {
  if (typeof value !== "string" || value.length > MAP_MAX_NODE_ID || !MAP_NODE_ID_RE.test(value)) {
    fail(name + " is not a canonical node ID");
  }
  return value;
}

function mapKey(value, name) {
  if (typeof value !== "string" || !MAP_ID_RE.test(value)) {
    fail(name + " must be a 1..64 lowercase identifier");
  }
  return value;
}

function unique(values, name) {
  if (new Set(values).size !== values.length) {
    fail(name + " must be unique");
  }
}

// Generic scalar/structure safety for a reassembled logical body: depth,
// field count, string length and safe integers stay generic; lists use the
// logical ceiling (exact collection bounds are enforced by the schema).
function checkMapSafety(value, depth) {
  if (depth > MAX_DEPTH) {
    fail("nesting exceeds maximum depth " + MAX_DEPTH);
  }
  if (Array.isArray(value)) {
    if (value.length > MAP_MAX_LIST_ITEMS) {
      fail("list exceeds maximum of " + MAP_MAX_LIST_ITEMS + " items");
    }
    for (var i = 0; i < value.length; i++) {
      checkMapSafety(value[i], depth + 1);
    }
  } else if (isPlainObject(value)) {
    var keys = Object.keys(value);
    if (keys.length > MAX_FIELDS) {
      fail("object exceeds maximum of " + MAX_FIELDS + " fields");
    }
    for (var j = 0; j < keys.length; j++) {
      if (codePoints(keys[j]) > MAX_STRING_CODE_POINTS) {
        fail("object key exceeds the maximum string length");
      }
      checkMapSafety(value[keys[j]], depth + 1);
    }
  } else if (typeof value === "number") {
    if (!isFinite(value)) {
      fail("non-finite numbers are forbidden");
    }
    if (Number.isInteger(value) && Math.abs(value) > MAX_SAFE_INTEGER) {
      fail("integer is outside the JavaScript-safe range");
    }
  } else if (typeof value === "string") {
    if (codePoints(value) > MAX_STRING_CODE_POINTS) {
      fail("string exceeds the maximum of " + MAX_STRING_CODE_POINTS + " code points");
    }
  } else if (value !== null && typeof value !== "boolean") {
    fail("unsupported JSON value type");
  }
}

function head(payload, panel, fields, version) {
  exact(payload, panel + " panel", fields);
  if (int(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER) !== version) {
    fail("unsupported " + panel + " schema_version");
  }
  if (payload.available !== true) {
    fail("available must be true for the " + panel + " form");
  }
}

// ---------------------------------------------------------------------------
// area_map.
// ---------------------------------------------------------------------------

var AREA_COMMON_FIELDS = [
  "schema_version",
  "available",
  "layer",
  "map_id",
  "frame",
  "current_node",
  "title",
  "nodes",
  "edges",
  "quest_markers",
];
var AREA_WILDERNESS_FIELDS = AREA_COMMON_FIELDS.concat(["district_name", "cell_km"]);

function areaGateway(value) {
  if (value === null) {
    return null;
  }
  exact(value, "gateway", ["leads_to"]);
  return { leads_to: text(value.leads_to, "gateway.leads_to", MAP_MAX_LABEL) };
}

function areaAction(value) {
  if (value === null) {
    return null;
  }
  exact(value, "action", ["kind", "exit_ref", "destination"]);
  if (AREA_ACTION_KINDS.indexOf(value.kind) === -1) {
    fail("action.kind is not a stable value");
  }
  if (typeof value.exit_ref !== "string" || !EXIT_REF_RE.test(value.exit_ref)) {
    fail("action.exit_ref must be 1.." + MAP_MAX_EXIT_REF + " ASCII characters");
  }
  return {
    kind: value.kind,
    exit_ref: value.exit_ref,
    destination: nodeId(value.destination, "action.destination"),
  };
}

function areaNode(value, layer) {
  var fields;
  if (layer === "grid") {
    fields = ["id", "label", "x", "y", "visibility", "gateway", "action"];
  } else if (layer === "wilderness") {
    fields = ["id", "label", "x", "y", "visibility", "visited", "gateway", "action"];
  } else {
    fields = ["id", "label", "visibility", "gateway", "action"];
  }
  exact(value, "node", fields);
  var node = { id: nodeId(value.id, "node.id"), label: text(value.label, "node.label", MAP_MAX_LABEL) };
  if (layer === "grid") {
    node.x = int(value.x, "node.x", MAP_COORD_MIN, MAP_COORD_MAX);
    node.y = int(value.y, "node.y", MAP_COORD_MIN, MAP_COORD_MAX);
  } else if (layer === "wilderness") {
    node.x = number(value.x, "node.x");
    node.y = number(value.y, "node.y");
  }
  if (AREA_VISIBILITIES.indexOf(value.visibility) === -1) {
    fail("node.visibility is not a stable value");
  }
  node.visibility = value.visibility;
  if (layer === "wilderness") {
    node.visited = bool(value.visited, "node.visited");
    if (node.visibility === "current" && !node.visited) {
      fail("the current wilderness node must be visited");
    }
  }
  node.gateway = areaGateway(value.gateway);
  node.action = areaAction(value.action);
  return node;
}

function areaMarker(value) {
  exact(value, "quest marker", ["id", "title", "tracked", "destination"]);
  var destination = value.destination;
  if (!isPlainObject(destination) || !has(destination, "kind")) {
    fail("quest marker destination must be a tagged object");
  }
  var normalized;
  if (destination.kind === "node") {
    exact(destination, "node destination", ["kind", "node_id"]);
    normalized = { kind: "node", node_id: nodeId(destination.node_id, "destination.node_id") };
  } else if (destination.kind === "bearing") {
    exact(destination, "bearing destination", ["kind", "bearing_deg", "distance_km"]);
    var bearing = number(destination.bearing_deg, "destination.bearing_deg", 0, 360);
    if (bearing >= 360) {
      fail("destination.bearing_deg must be below 360");
    }
    normalized = {
      kind: "bearing",
      bearing_deg: bearing,
      distance_km: number(destination.distance_km, "destination.distance_km", 0),
    };
  } else {
    fail("quest marker destination kind is not a stable value");
  }
  return {
    id: text(value.id, "quest marker id", MAP_MAX_QUEST_ID),
    title: text(value.title, "quest marker title", MAP_MAX_TITLE),
    tracked: bool(value.tracked, "quest marker tracked"),
    destination: normalized,
  };
}

function validateAreaMapPanel(payload) {
  if (!isPlainObject(payload)) {
    fail("area_map panel must be a JSON object");
  }
  var layer = payload.layer;
  if (AREA_LAYERS.indexOf(layer) === -1) {
    fail("area_map layer is not a stable value");
  }
  head(
    payload,
    "area_map",
    layer === "wilderness" ? AREA_WILDERNESS_FIELDS : AREA_COMMON_FIELDS,
    AREA_MAP_SCHEMA_VERSION
  );
  var mapId = payload.map_id;
  if (layer === "wilderness") {
    if (mapId !== WILDERNESS_MAP_ID) {
      fail("a wilderness area_map must use the continental map_id");
    }
  } else if (layer === "grid") {
    if (typeof mapId !== "string" || !GRID_MAP_ID_RE.test(mapId)) {
      fail("a grid map_id must be a canonical z-map key");
    }
  } else if (typeof mapId !== "string" || !ROOM_GRAPH_MAP_ID_RE.test(mapId)) {
    fail("an instance/interior map_id must be a stable bounded identity");
  }
  exact(payload.frame, "frame", ["key", "unit"]);
  if (payload.frame.key !== mapId) {
    fail("frame.key must equal map_id");
  }
  if (payload.frame.unit !== AREA_FRAME_UNITS[layer]) {
    fail("frame.unit must be " + AREA_FRAME_UNITS[layer] + " for " + layer);
  }
  var current = nodeId(payload.current_node, "current_node");
  var title = text(payload.title, "title", MAP_MAX_TITLE);
  var limit = layer === "wilderness" ? WILDERNESS_MAX_NODES : AREA_MAX_NODES;
  var nodes = list(payload.nodes, "nodes", 1, limit).map(function (item) {
    return areaNode(item, layer);
  });
  var ids = nodes.map(function (node) {
    return node.id;
  });
  unique(ids, "node ids");
  var currentRows = nodes.filter(function (node) {
    return node.visibility === "current";
  });
  if (currentRows.length !== 1 || currentRows[0].id !== current) {
    fail("exactly one node must be current and equal current_node");
  }
  nodes.forEach(function (node) {
    if (layer === "grid" && node.id.indexOf("grid:" + mapId + ":") !== 0) {
      fail("grid area nodes must belong to the declared map");
    }
    if ((layer === "instance" || layer === "interior") && node.id.indexOf("room:") !== 0) {
      fail("instance/interior area nodes must be rooms");
    }
    if (layer === "wilderness" && node.id.indexOf("wild:") !== 0 && node.gateway === null) {
      fail("a non-wilderness node in the wilderness window must be a gateway");
    }
  });
  if (layer === "wilderness" && current.indexOf("wild:") !== 0) {
    fail("a wilderness area_map must have a wild current node");
  }
  var known = new Set(ids);
  var edges = list(payload.edges, "edges", 0, AREA_MAX_EDGES).map(function (item) {
    exact(item, "edge", ["source", "destination"]);
    var source = nodeId(item.source, "edge.source");
    var destination = nodeId(item.destination, "edge.destination");
    if (source === destination) {
      fail("an edge must connect two distinct nodes");
    }
    if (!known.has(source) || !known.has(destination)) {
      fail("an edge must reference presented nodes");
    }
    return { source: source, destination: destination };
  });
  unique(
    edges.map(function (edge) {
      return edge.source + "\u0000" + edge.destination;
    }),
    "edges"
  );
  var markers = list(payload.quest_markers, "quest_markers", 0, AREA_MAX_QUEST_MARKERS).map(areaMarker);
  unique(
    markers.map(function (marker) {
      return marker.id;
    }),
    "quest marker ids"
  );
  var result = {
    schema_version: AREA_MAP_SCHEMA_VERSION,
    available: true,
    layer: layer,
    map_id: mapId,
    frame: { key: mapId, unit: AREA_FRAME_UNITS[layer] },
    current_node: current,
    title: title,
    nodes: nodes,
    edges: edges,
    quest_markers: markers,
  };
  if (layer === "wilderness") {
    result.district_name = text(payload.district_name, "district_name", MAP_MAX_TITLE);
    var cellKm = number(payload.cell_km, "cell_km", 0, AREA_MAX_CELL_KM);
    if (cellKm <= 0) {
      fail("cell_km must be positive");
    }
    result.cell_km = cellKm;
  }
  checkMapSafety(result, MAP_PANEL_DEPTH);
  return result;
}

// ---------------------------------------------------------------------------
// world_map.
// ---------------------------------------------------------------------------

function point(value, name) {
  if (!Array.isArray(value) || value.length !== 2) {
    fail(name + " must be an [x, y] pair");
  }
  return [number(value[0], name + ".x"), number(value[1], name + ".y")];
}

function polyline(value, name) {
  return list(value, name, 2, WORLD_MAX_POLYLINE_POINTS).map(function (item) {
    return point(item, name);
  });
}

function signedArea(points) {
  var total = 0;
  for (var i = 0; i + 1 < points.length; i++) {
    total += points[i][0] * points[i + 1][1] - points[i + 1][0] * points[i][1];
  }
  return total / 2;
}

function polygon(value, name) {
  var points = list(value, name, 4, WORLD_MAX_POLYGON_POINTS).map(function (item) {
    return point(item, name);
  });
  var first = points[0];
  var last = points[points.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) {
    fail(name + " must be closed (first point equals last)");
  }
  if (signedArea(points) === 0) {
    fail(name + " must enclose a nonzero area");
  }
  return points;
}

// A list of closed rings: counter-clockwise (positive signed area with
// north-positive y) outer rings, clockwise holes.
function outline(value, name) {
  var rings = list(value, name, 1, WORLD_MAX_OUTLINE_POLYGONS).map(function (ring) {
    return polygon(ring, name);
  });
  if (!rings.some(function (ring) { return signedArea(ring) > 0; })) {
    fail(name + " needs at least one counter-clockwise outer ring");
  }
  return rings;
}

function place(value, name) {
  exact(value, name, ["id", "name", "kind", "x", "y"]);
  if (PLACE_KINDS.indexOf(value.kind) === -1) {
    fail(name + ".kind is not a stable value");
  }
  return {
    id: mapKey(value.id, name + ".id"),
    name: text(value.name, name + ".name", MAP_MAX_LABEL),
    kind: value.kind,
    x: number(value.x, name + ".x"),
    y: number(value.y, name + ".y"),
  };
}

function places(value, name) {
  var rows = list(value, name, 0, WORLD_MAX_PLACES).map(function (row) {
    return place(row, name);
  });
  unique(rows.map(function (row) { return row.id; }), name + " ids");
  return rows;
}

function common(value) {
  exact(value, "common", ["coastline", "borders", "nations"]);
  var nations = list(value.nations, "common.nations", 0, WORLD_MAX_NATIONS).map(function (row) {
    exact(row, "nation", ["id", "name", "x", "y"]);
    return {
      id: mapKey(row.id, "nation.id"),
      name: text(row.name, "nation.name", MAP_MAX_LABEL),
      x: number(row.x, "nation.x"),
      y: number(row.y, "nation.y"),
    };
  });
  unique(nations.map(function (row) { return row.id; }), "nation ids");
  return {
    coastline: polygon(value.coastline, "common.coastline"),
    borders: list(value.borders, "common.borders", 0, WORLD_MAX_BORDERS).map(function (line) {
      return polyline(line, "common.borders");
    }),
    nations: nations,
  };
}

function lines(value, name) {
  return list(value, name, 0, WORLD_MAX_DISTRICT_POLYLINES).map(function (line) {
    return polyline(line, name);
  });
}

function district(value, nationIds) {
  if (!isPlainObject(value)) {
    fail("district must be a JSON object");
  }
  if (value.lit === false) {
    exact(value, "unlit district", ["id", "lit", "outline"]);
    return { id: mapKey(value.id, "district.id"), lit: false, outline: outline(value.outline, "district.outline") };
  }
  if (value.lit !== true) {
    fail("district.lit must be a boolean discriminator");
  }
  exact(value, "lit district", [
    "id",
    "lit",
    "name",
    "outline",
    "landmark",
    "nations",
    "terrain",
    "rivers",
    "ridge",
    "roads",
    "places",
  ]);
  var landmark = exact(value.landmark, "landmark", ["name", "x", "y"]);
  var nations = list(value.nations, "district.nations", 0, WORLD_MAX_DISTRICT_NATIONS).map(function (item) {
    return mapKey(item, "district.nations");
  });
  unique(nations, "district nations");
  nations.forEach(function (nation) {
    if (!nationIds.has(nation)) {
      fail("district.nations must name common nations");
    }
  });
  var terrain = list(value.terrain, "district.terrain", 0, WORLD_MAX_TERRAIN_REGIONS).map(function (row) {
    exact(row, "terrain", ["region", "polygons"]);
    return { region: mapKey(row.region, "terrain.region"), polygons: outline(row.polygons, "terrain.polygons") };
  });
  return {
    id: mapKey(value.id, "district.id"),
    lit: true,
    name: text(value.name, "district.name", MAP_MAX_LABEL),
    outline: outline(value.outline, "district.outline"),
    landmark: {
      name: text(landmark.name, "landmark.name", MAP_MAX_LABEL),
      x: number(landmark.x, "landmark.x"),
      y: number(landmark.y, "landmark.y"),
    },
    nations: nations,
    terrain: terrain,
    rivers: lines(value.rivers, "district.rivers"),
    ridge: lines(value.ridge, "district.ridge"),
    roads: lines(value.roads, "district.roads"),
    places: places(value.places, "district.places"),
  };
}

function trail(value) {
  exact(value, "trail", ["resolution_km", "rows"]);
  var resolution = int(value.resolution_km, "trail.resolution_km", 1, 5);
  if (TRAIL_RESOLUTIONS.indexOf(resolution) === -1) {
    fail("trail.resolution_km must be 1 or 5");
  }
  var cells = Math.ceil(TRAIL_FRAME_CELLS / resolution);
  var previousRow = -1;
  var totalRuns = 0;
  var rows = list(value.rows, "trail.rows", 0, cells).map(function (row) {
    if (!Array.isArray(row) || row.length !== 2) {
      fail("trail row must be [row_index, runs]");
    }
    var rowIndex = int(row[0], "trail row index", 0, cells - 1);
    if (rowIndex <= previousRow) {
      fail("trail rows must be strictly increasing");
    }
    previousRow = rowIndex;
    var end = -1;
    var runs = list(row[1], "trail runs", 1, cells).map(function (run) {
      if (!Array.isArray(run) || run.length !== 2) {
        fail("trail run must be [start_column, length]");
      }
      var start = int(run[0], "trail run start", 0, cells - 1);
      var length = int(run[1], "trail run length", 1, cells);
      if (start < end) {
        fail("trail runs must be sorted and non-overlapping");
      }
      end = start + length;
      if (end > cells) {
        fail("trail run exceeds the trail grid");
      }
      return [start, length];
    });
    totalRuns += runs.length;
    return [rowIndex, runs];
  });
  if (totalRuns > TRAIL_MAX_RUNS) {
    fail("trail exceeds " + TRAIL_MAX_RUNS + " runs");
  }
  return { resolution_km: resolution, rows: rows };
}

function worldMarker(value) {
  exact(value, "world quest marker", ["id", "title", "tracked", "x", "y", "approximate"]);
  var approximate = bool(value.approximate, "quest marker approximate");
  var x = number(value.x, "quest marker x");
  var y = number(value.y, "quest marker y");
  if (approximate) {
    x = int(x, "quest marker x", MAP_COORD_MIN, MAP_COORD_MAX);
    y = int(y, "quest marker y", MAP_COORD_MIN, MAP_COORD_MAX);
    if (x % WORLD_APPROXIMATE_GRID_KM !== 0 || y % WORLD_APPROXIMATE_GRID_KM !== 0) {
      fail("an approximate marker must sit on the 50 km grid");
    }
  }
  return {
    id: text(value.id, "quest marker id", MAP_MAX_QUEST_ID),
    title: text(value.title, "quest marker title", MAP_MAX_TITLE),
    tracked: bool(value.tracked, "quest marker tracked"),
    x: x,
    y: y,
    approximate: approximate,
  };
}

function validateWorldMapPanel(payload) {
  head(
    payload,
    "world_map",
    ["schema_version", "available", "common", "districts", "trail", "visited_places", "current", "quest_markers"],
    WORLD_MAP_SCHEMA_VERSION
  );
  var commonView = common(payload.common);
  var nationIds = new Set(commonView.nations.map(function (row) { return row.id; }));
  var districts = list(payload.districts, "districts", 0, WORLD_MAX_DISTRICTS).map(function (item) {
    return district(item, nationIds);
  });
  unique(districts.map(function (row) { return row.id; }), "district ids");
  var current = exact(payload.current, "current", ["x", "y"]);
  var markers = list(payload.quest_markers, "quest_markers", 0, WORLD_MAX_QUEST_MARKERS).map(worldMarker);
  unique(markers.map(function (marker) { return marker.id; }), "quest marker ids");
  var result = {
    schema_version: WORLD_MAP_SCHEMA_VERSION,
    available: true,
    common: commonView,
    districts: districts,
    trail: trail(payload.trail),
    visited_places: places(payload.visited_places, "visited_places"),
    current: { x: number(current.x, "current.x"), y: number(current.y, "current.y") },
    quest_markers: markers,
  };
  checkMapSafety(result, MAP_PANEL_DEPTH);
  return result;
}

var VALIDATORS = { area_map: validateAreaMapPanel, world_map: validateWorldMapPanel };

// The scoped world-map frame allowance (transport-world-map-panel), mirror of
// map_panels.carries_intact_world_map / check_world_map_envelope.
var WORLD_MAP_FRAME_MAX_BYTES = require("../constants.js").MAX_CANONICAL_JSON_BYTES + WORLD_MAX_BYTES;

// Whether a frame claims the allowance: an envelope object whose panels
// object owns a world_map object that is not a bounded part.
function carriesIntactWorldMap(envelope) {
  if (!isPlainObject(envelope) || !has(envelope, "panels") || !isPlainObject(envelope.panels)) {
    return false;
  }
  if (!has(envelope.panels, "world_map")) {
    return false;
  }
  var body = envelope.panels.world_map;
  return isPlainObject(body) && !has(body, "part");
}

// Copy own enumerable keys as data properties. Object.assign would run the
// __proto__ setter for a JSON-parsed "__proto__" key and hide that value from
// the generic walk.
function ownCopy(value) {
  var copy = {};
  Object.keys(value).forEach(function (key) {
    Object.defineProperty(copy, key, { value: value[key], enumerable: true, writable: true, configurable: true });
  });
  return copy;
}

// The world map is the only value exempt from the generic frame budget: the
// rest of the envelope, with the world map replaced by null, passes the
// unchanged generic check (siblings such as local_map and area_map keep the
// 65,536-byte frame), and the world map passes the generic scalar rules and
// its logical byte ceiling. The exact schema runs later in validateUpdate.
function checkWorldMapEnvelope(envelope) {
  if (!carriesIntactWorldMap(envelope)) {
    fail("the world-map allowance needs an intact world_map panel");
  }
  var panels = ownCopy(envelope.panels);
  var body = panels.world_map;
  panels.world_map = null;
  var remainder = ownCopy(envelope);
  remainder.panels = panels;
  core.checkEnvelope(remainder);
  checkMapSafety(body, MAP_PANEL_DEPTH);
  if (core.jsonByteSize(body) > WORLD_MAX_BYTES) {
    fail("world_map exceeds " + WORLD_MAX_BYTES + " canonical bytes");
  }
}

// One logical map panel: its available form or the common unavailable form.
function validateMapPanel(name, payload) {
  if (!has(MAP_PANEL_SCHEMAS, name)) {
    fail(name + " is not an on-demand map panel");
  }
  if (isPlainObject(payload) && payload.available === false) {
    exact(payload, name + " panel", ["schema_version", "available", "reason"]);
    if (int(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER) !== MAP_PANEL_SCHEMAS[name]) {
      fail("unsupported " + name + " schema_version");
    }
    var reason = payload.reason;
    if (!isPlainObject(reason)) {
      fail("reason must be a JSON object");
    }
    var withCorrelation = has(reason, "correlation_id");
    exact(reason, "reason", withCorrelation ? ["code", "message", "correlation_id"] : ["code", "message"]);
    validateIdentifier(reason.code, "reason.code");
    validateMessage(reason.message, "reason.message");
    if (withCorrelation) {
      validateCorrelationId(reason.correlation_id);
    }
    return payload;
  }
  return VALIDATORS[name](payload);
}

module.exports = {
  AREA_MAP_SCHEMA_VERSION: AREA_MAP_SCHEMA_VERSION,
  WORLD_MAP_SCHEMA_VERSION: WORLD_MAP_SCHEMA_VERSION,
  MAP_PANEL_SCHEMAS: MAP_PANEL_SCHEMAS,
  MAP_MAX_BYTES: MAP_MAX_BYTES,
  MAP_CONSTANTS: {
    MAP_MAX_LABEL: MAP_MAX_LABEL,
    MAP_MAX_TITLE: MAP_MAX_TITLE,
    MAP_MAX_NODE_ID: MAP_MAX_NODE_ID,
    MAP_MAX_EXIT_REF: MAP_MAX_EXIT_REF,
    MAP_MAX_ID: MAP_MAX_ID,
    MAP_MAX_QUEST_ID: MAP_MAX_QUEST_ID,
    MAP_COORD_MIN: MAP_COORD_MIN,
    MAP_COORD_MAX: MAP_COORD_MAX,
    MAP_MAX_LIST_ITEMS: MAP_MAX_LIST_ITEMS,
    MAP_PANEL_DEPTH: MAP_PANEL_DEPTH,
    AREA_MAX_NODES: AREA_MAX_NODES,
    AREA_MAX_EDGES: AREA_MAX_EDGES,
    AREA_MAX_QUEST_MARKERS: AREA_MAX_QUEST_MARKERS,
    AREA_MAX_BYTES: AREA_MAX_BYTES,
    WILDERNESS_WINDOW: WILDERNESS_WINDOW,
    WILDERNESS_MAX_NODES: WILDERNESS_MAX_NODES,
    AREA_MAX_CELL_KM: AREA_MAX_CELL_KM,
    WORLD_MAX_BYTES: WORLD_MAX_BYTES,
    WORLD_MAX_POLYGON_POINTS: WORLD_MAX_POLYGON_POINTS,
    WORLD_MAX_POLYLINE_POINTS: WORLD_MAX_POLYLINE_POINTS,
    WORLD_MAX_BORDERS: WORLD_MAX_BORDERS,
    WORLD_MAX_NATIONS: WORLD_MAX_NATIONS,
    WORLD_MAX_DISTRICTS: WORLD_MAX_DISTRICTS,
    WORLD_MAX_OUTLINE_POLYGONS: WORLD_MAX_OUTLINE_POLYGONS,
    WORLD_MAX_TERRAIN_REGIONS: WORLD_MAX_TERRAIN_REGIONS,
    WORLD_MAX_DISTRICT_POLYLINES: WORLD_MAX_DISTRICT_POLYLINES,
    WORLD_MAX_PLACES: WORLD_MAX_PLACES,
    WORLD_MAX_DISTRICT_NATIONS: WORLD_MAX_DISTRICT_NATIONS,
    WORLD_MAX_QUEST_MARKERS: WORLD_MAX_QUEST_MARKERS,
    WORLD_APPROXIMATE_GRID_KM: WORLD_APPROXIMATE_GRID_KM,
    TRAIL_RESOLUTIONS: TRAIL_RESOLUTIONS,
    TRAIL_FRAME_CELLS: TRAIL_FRAME_CELLS,
    TRAIL_MAX_RUNS: TRAIL_MAX_RUNS,
    AREA_LAYERS: AREA_LAYERS,
    AREA_VISIBILITIES: AREA_VISIBILITIES,
    AREA_ACTION_KINDS: AREA_ACTION_KINDS,
    AREA_FRAME_UNITS: AREA_FRAME_UNITS,
    WILDERNESS_MAP_ID: WILDERNESS_MAP_ID,
    PLACE_KINDS: PLACE_KINDS,
    MAP_NODE_ID_RE: MAP_NODE_ID_RE.source,
  },
  WORLD_MAP_FRAME_MAX_BYTES: WORLD_MAP_FRAME_MAX_BYTES,
  checkMapSafety: checkMapSafety,
  carriesIntactWorldMap: carriesIntactWorldMap,
  checkWorldMapEnvelope: checkWorldMapEnvelope,
  validateAreaMapPanel: validateAreaMapPanel,
  validateWorldMapPanel: validateWorldMapPanel,
  validateMapPanel: validateMapPanel,
};
