"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var skillDescriptor = require("./skill_descriptor.js");

var requireNumber = skillDescriptor.requireNumber;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;
var requireNodeId = core.requireNodeId;
var requireExitRef = core.requireExitRef;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var LOCAL_MAP_MAX_NODES = C.LOCAL_MAP_MAX_NODES;
var LOCAL_MAP_MAX_EDGES = C.LOCAL_MAP_MAX_EDGES;
var LOCAL_MAP_MAX_LEGEND = C.LOCAL_MAP_MAX_LEGEND;
var LOCAL_MAP_MAX_STRING = C.LOCAL_MAP_MAX_STRING;
var LINEAGE_MAX_CHAINS = C.LINEAGE_MAX_CHAINS;
var LINEAGE_MAX_NODES_PER_CHAIN = C.LINEAGE_MAX_NODES_PER_CHAIN;
var LINEAGE_MAX_TEXT = C.LINEAGE_MAX_TEXT;
var LOCAL_MAP_MAX_TITLE = C.LOCAL_MAP_MAX_TITLE;
var LOCAL_MAP_COORD_MIN = C.LOCAL_MAP_COORD_MIN;
var LOCAL_MAP_COORD_MAX = C.LOCAL_MAP_COORD_MAX;
var LOCAL_MAP_VISIBILITIES = C.LOCAL_MAP_VISIBILITIES;
var LOCAL_MAP_LAYERS = C.LOCAL_MAP_LAYERS;
var LOCAL_MAP_ACTION_KINDS = C.LOCAL_MAP_ACTION_KINDS;


// Exact available local_map panel v1 schema (design D10a).

function requireCoord(value, field) {
  requireInt(value, field, LOCAL_MAP_COORD_MIN, LOCAL_MAP_COORD_MAX);
  return value;
}

function validateLocalMapAction(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(value, "action", ["kind", "exit_ref", "destination"], []);
  if (LOCAL_MAP_ACTION_KINDS.indexOf(value.kind) === -1) {
    throw new Error("action kind is not a stable value");
  }
  requireExitRef(value.exit_ref, "action.exit_ref");
  requireNodeId(value.destination, "action.destination");
  return {
    kind: value.kind,
    exit_ref: value.exit_ref,
    destination: value.destination,
  };
}

function validateLocalMapNode(value) {
  requireExactFields(
    value,
    "node",
    ["id", "label", "x", "y", "visibility", "current", "anchor", "landmark", "action"],
    []
  );
  var nodeId = requireNodeId(value.id, "node.id");
  var label = requireString(value.label, "node.label", LOCAL_MAP_MAX_STRING);
  if (!label.trim()) {
    throw new Error("node.label must be non-empty");
  }
  var x = requireCoord(value.x, "node.x");
  var y = requireCoord(value.y, "node.y");
  if (LOCAL_MAP_VISIBILITIES.indexOf(value.visibility) === -1) {
    throw new Error("node.visibility is not a stable value");
  }
  var current = requireBool(value.current, "current");
  var anchor = requireBool(value.anchor, "anchor");
  var landmark = requireBool(value.landmark, "landmark");
  var action = validateLocalMapAction(value.action);
  if (value.visibility === "current" && !current) {
    throw new Error("the current node must carry current=true");
  }
  if (current && value.visibility !== "current") {
    throw new Error("a non-current node must not carry current=true");
  }
  return {
    id: nodeId,
    label: label,
    x: x,
    y: y,
    visibility: value.visibility,
    current: current,
    anchor: anchor,
    landmark: landmark,
    action: action,
  };
}

function validateLocalMapEdge(value) {
  requireExactFields(
    value,
    "edge",
    ["source", "destination", "label", "known", "traversable"],
    []
  );
  var source = requireNodeId(value.source, "edge.source");
  var destination = requireNodeId(value.destination, "edge.destination");
  var label = requireString(value.label, "edge.label", LOCAL_MAP_MAX_STRING);
  var known = requireBool(value.known, "known");
  var traversable = requireBool(value.traversable, "traversable");
  if (source === destination) {
    throw new Error("an edge must connect two distinct nodes");
  }
  return {
    source: source,
    destination: destination,
    label: label,
    known: known,
    traversable: traversable,
  };
}

function validateLineageNode(value) {
  requireExactFields(
    value,
    "lineage node",
    [
      "skill_key",
      "display_name_zh",
      "owned",
      "usable",
      "level",
      "xp_into_level",
      "xp_to_next_level",
      "capped",
      "prereq_text_zh",
    ],
    []
  );
  var skillKey = validateIdentifier(value.skill_key, "skill_key");
  var displayName = requireString(
    value.display_name_zh,
    "display_name_zh",
    LINEAGE_MAX_TEXT
  );
  if (!displayName.trim()) {
    throw new Error("display_name_zh must be non-empty");
  }
  var prereqText = requireString(
    value.prereq_text_zh,
    "prereq_text_zh",
    LINEAGE_MAX_TEXT
  );
  return {
    skill_key: skillKey,
    display_name_zh: displayName,
    owned: requireBool(value.owned, "owned"),
    usable: requireBool(value.usable, "usable"),
    level: requireInt(value.level, "level", 0, MAX_SAFE_INTEGER),
    xp_into_level: requireNumber(
      value.xp_into_level,
      "xp_into_level",
      0,
      MAX_SAFE_INTEGER
    ),
    xp_to_next_level: requireNumber(
      value.xp_to_next_level,
      "xp_to_next_level",
      0,
      MAX_SAFE_INTEGER
    ),
    capped: requireBool(value.capped, "capped"),
    prereq_text_zh: prereqText,
  };
}

function validateLineageChain(value) {
  requireExactFields(
    value,
    "lineage chain",
    ["root_skill_key", "element_or_style_zh", "consumed", "meter", "nodes"],
    []
  );
  var rootKey = validateIdentifier(value.root_skill_key, "root_skill_key");
  var label = requireString(
    value.element_or_style_zh,
    "element_or_style_zh",
    LINEAGE_MAX_TEXT
  );
  if (!label.trim()) {
    throw new Error("element_or_style_zh must be non-empty");
  }
  if (!Array.isArray(value.nodes) || value.nodes.length < 1 || value.nodes.length > LINEAGE_MAX_NODES_PER_CHAIN) {
    throw new Error(
      "nodes must be a list of 1.." + LINEAGE_MAX_NODES_PER_CHAIN + " entries"
    );
  }
  var nodeViews = value.nodes.map(validateLineageNode);
  if (nodeViews[0].skill_key !== rootKey) {
    throw new Error("truncated chains keep their head: nodes[0] must be the root");
  }
  return {
    root_skill_key: rootKey,
    element_or_style_zh: label,
    consumed: requireBool(value.consumed, "consumed"),
    meter: requireNumber(value.meter, "meter", 0, 1),
    nodes: nodeViews,
  };
}

function validateLineagePanel(payload) {
  requireExactFields(
    payload,
    "lineage panel",
    ["schema_version", "available", "kind", "completed_count", "total_count", "chains"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 1) {
    throw new Error("unsupported lineage panel schema_version");
  }
  // Mirror the Python validate_lineage: the exported validator rejects the
  // unavailable discriminator directly (rubber-duck R2-2); the dispatcher's
  // guard is defense in depth, not the only gate.
  requireBool(payload.available, "available");
  if (payload.available !== true) {
    throw new Error("lineage panel available must be true in the available form");
  }
  if (payload.kind !== "lineage") {
    throw new Error("lineage panel kind must be lineage");
  }
  var completed = requireInt(
    payload.completed_count,
    "completed_count",
    0,
    MAX_SAFE_INTEGER
  );
  var total = requireInt(payload.total_count, "total_count", 0, MAX_SAFE_INTEGER);
  if (completed > total) {
    throw new Error("completed_count must not exceed total_count");
  }
  if (!Array.isArray(payload.chains) || payload.chains.length > LINEAGE_MAX_CHAINS) {
    throw new Error(
      "chains must be a list of at most " + LINEAGE_MAX_CHAINS + " entries"
    );
  }
  var chainViews = payload.chains.map(validateLineageChain);
  var result = {
    schema_version: 1,
    available: true,
    kind: "lineage",
    completed_count: completed,
    total_count: total,
    chains: chainViews,
  };
  // Envelope guarantee: the presenter truncates until a real payload fits;
  // the validator enforces the serialized byte size directly and fails
  // closed over the envelope.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("lineage payload exceeds the OOB envelope limit");
  }
  return result;
}

function validateLocalMapPanel(payload) {
  requireExactFields(
    payload,
    "local_map panel",
    ["schema_version", "available", "layer", "current_node", "title", "nodes", "edges", "legend"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 1) {
    throw new Error("unsupported local_map panel schema_version");
  }
  if (LOCAL_MAP_LAYERS.indexOf(payload.layer) === -1) {
    throw new Error("layer is not a stable value");
  }
  var currentNode = requireNodeId(payload.current_node, "current_node");
  var prefix = currentNode.split(":")[0];
  if (payload.layer === "grid" && prefix !== "grid") {
    throw new Error("a grid-layer payload must have a grid current node");
  }
  if (payload.layer === "wilderness" && prefix !== "wild") {
    throw new Error("a wilderness-layer payload must have a wild current node");
  }
  if (
    (payload.layer === "instance" || payload.layer === "interior") &&
    prefix !== "room"
  ) {
    throw new Error("an instance/interior payload must have a room current node");
  }
  var title = requireString(payload.title, "title", LOCAL_MAP_MAX_TITLE);
  if (!title.trim()) {
    throw new Error("title must be non-empty");
  }

  var nodes = payload.nodes;
  if (!Array.isArray(nodes) || nodes.length < 1 || nodes.length > LOCAL_MAP_MAX_NODES) {
    throw new Error("nodes must be a list of 1.." + LOCAL_MAP_MAX_NODES + " entries");
  }
  var nodeViews = nodes.map(validateLocalMapNode);
  var currentCount = nodeViews.filter(function (node) {
    return node.current;
  }).length;
  if (currentCount !== 1) {
    throw new Error("the payload must mark exactly one current node");
  }
  if (!nodeViews.some(function (node) {
    return node.id === currentNode;
  })) {
    throw new Error("current_node must be present in nodes");
  }
  var nodeIds = nodeViews.map(function (node) {
    return node.id;
  });
  var unique = {};
  nodeIds.forEach(function (id) {
    if (unique[id]) {
      throw new Error("node ids must be unique");
    }
    unique[id] = true;
  });

  var edges = payload.edges;
  if (!Array.isArray(edges) || edges.length > LOCAL_MAP_MAX_EDGES) {
    throw new Error("edges must be a list of at most " + LOCAL_MAP_MAX_EDGES + " entries");
  }
  var edgeViews = edges.map(validateLocalMapEdge);
  edgeViews.forEach(function (edge) {
    if (!unique[edge.source]) {
      throw new Error("edge.source must reference a presented node");
    }
    if (!unique[edge.destination]) {
      throw new Error("edge.destination must reference a presented node");
    }
  });

  var legend = payload.legend;
  if (!Array.isArray(legend) || legend.length > LOCAL_MAP_MAX_LEGEND) {
    throw new Error("legend must be a list of at most " + LOCAL_MAP_MAX_LEGEND + " entries");
  }
  var legendViews = legend.map(function (entry) {
    var text = requireString(entry, "legend", LOCAL_MAP_MAX_STRING);
    if (!text.trim()) {
      throw new Error("legend entries must be non-empty");
    }
    return text;
  });

  var result = {
    schema_version: 1,
    available: true,
    layer: payload.layer,
    current_node: currentNode,
    title: title,
    nodes: nodeViews,
    edges: edgeViews,
    legend: legendViews,
  };
  // Envelope guarantee (design D10a): the per-field bounds are ceilings, not
  // a guarantee that any combination of them fits, so the validator enforces
  // the serialized byte size directly and fails closed over the envelope.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("local_map payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validateLocalMapPanel: validateLocalMapPanel,
  validateLineagePanel: validateLineagePanel,
};
