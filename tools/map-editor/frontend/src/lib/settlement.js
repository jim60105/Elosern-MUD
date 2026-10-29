// Settlement authoring helpers (frontend design §4.2): editor-local road and
// bend references, the node field controls derived from the core schema, the
// directed road rows, multi-selection values, explanatory delete blockers and
// the named single-document command descriptors.
//
// Positions are integer metres in the settlement's local east/north frame
// (`m 地方`). Directions are always authored values chosen by the user:
// nothing here infers a compass direction from positions. Lengths and routes
// come from the core through the service; nothing here measures the canvas.
// The service and the core schema decide validity.

import { FRAME_LOCAL_M, nextId } from "./continent.js";
import { cityGateRef, exteriorRef, gateRef } from "./relationship_refs.js";

export { FRAME_LOCAL_M, nextId };
// One Shift+arrow press moves the selected nodes by this many metres.
export const NUDGE_M = 10;

export const COMPASS = Object.freeze([
  { value: "n", label: "北" },
  { value: "ne", label: "東北" },
  { value: "e", label: "東" },
  { value: "se", label: "東南" },
  { value: "s", label: "南" },
  { value: "sw", label: "西南" },
  { value: "w", label: "西" },
  { value: "nw", label: "西北" },
]);

export function compassLabel(direction) {
  return COMPASS.find((item) => item.value === direction)?.label ?? direction ?? "—";
}

const ID = "[a-z][a-z0-9_]*";
const NODE = new RegExp(`^settlement_node:(${ID}):(${ID})$`);
const ROAD = new RegExp(`^road:(${ID}):(${ID})>(${ID})(?:#(\\d+))?$`);

export const nodeRef = (settlementId, nodeId) => `settlement_node:${settlementId}:${nodeId}`;
export const roadRef = (settlementId, source, destination) => `road:${settlementId}:${source}>${destination}`;
export const bendRef = (road, index) => `${road}#${index}`;
export const settlementDocument = (settlementId) => `content/maps/settlements/${settlementId}.yaml`;

// { kind: node | road | bend, settlementId, nodeId?, source?, destination?, index?, road? }
export function parseSettlementRef(ref) {
  const node = NODE.exec(ref ?? "");
  if (node) return { kind: "node", settlementId: node[1], nodeId: node[2] };
  const road = ROAD.exec(ref ?? "");
  if (!road) return null;
  const base = { settlementId: road[1], source: road[2], destination: road[3], road: roadRef(road[1], road[2], road[3]) };
  return road[4] === undefined ? { kind: "road", ...base } : { kind: "bend", ...base, index: Number(road[4]) };
}

export function findSettlement(world, settlementId) {
  return world?.settlements?.find((row) => row.id === settlementId) ?? null;
}

export function findRoad(settlement, source, destination) {
  return settlement?.roads?.find((road) => road.source === source && road.destination === destination) ?? null;
}

export function nodeName(settlement, nodeId) {
  return settlement?.nodes?.find((node) => node.id === nodeId)?.key ?? nodeId;
}

export function roundPoint(point) {
  return [Math.round(point.x) + 0, Math.round(point.y) + 0];
}

export const IDENTIFIER = /^[a-z][a-z0-9_]*$/;

// -- schema-driven node fields ---------------------------------------------------
// The editable node fields (the position moves separately), each typed from
// the core schema the service serves: an enum is a select, a nullable string
// a field whose empty value is null, a string a text field (the multiline
// description a text area). Reference fields keep their own controls:
// anchor_key is chosen with the prototype, scene_archetype from the index.
export function nodeFieldSpecs(schema) {
  const fields = schema?.document_kinds?.settlement?.fields?.nodes?.items?.fields ?? {};
  return Object.entries(fields)
    .filter(([key]) => key !== "x_m" && key !== "y_m")
    .map(([key, spec]) => {
      let type = "text";
      if (spec.type === "enum") type = "select";
      else if (spec.nullable) type = "nullable";
      else if (key === "desc") type = "textarea";
      return {
        key,
        type,
        options: spec.type === "enum" ? spec.values.map((value) => ({ value, label: value })) : [],
        nullable: Boolean(spec.nullable),
        minLength: spec.min_length ?? null,
        reference: key === "anchor_key" ? "location" : key === "scene_archetype" ? "scene" : null,
      };
    });
}

// The core's rule pairs: an anchor room names its location, a grid room none.
export function prototypeFields(prototype, anchorKey) {
  return { prototype_parent: prototype, anchor_key: prototype === "anchor_room" ? anchorKey ?? null : null };
}

// A blank node in the stored shape (create_node carries every field).
export function blankNode(x, y, { key = "", desc = "" } = {}) {
  return {
    x_m: x,
    y_m: y,
    prototype_parent: "grid_room",
    key,
    desc,
    anchor_key: null,
    typeclass: null,
    scene_archetype: null,
  };
}

// -- multi-selection ---------------------------------------------------------------
// The settlement and node IDs of a selection made only of nodes of one
// settlement document, else null (another kind or a second document).
export function oneDocumentNodes(refs) {
  const parsed = [...(refs ?? [])].map(parseSettlementRef);
  if (!parsed.length || parsed.some((item) => item?.kind !== "node")) return null;
  const settlements = new Set(parsed.map((item) => item.settlementId));
  if (settlements.size !== 1) return null;
  return { settlementId: parsed[0].settlementId, nodeIds: parsed.map((item) => item.nodeId) };
}

// The value every node shares, or "—" when they differ (design §4.2).
export function mixedValue(nodes, read) {
  const values = new Set(nodes.map((node) => JSON.stringify(read(node) ?? null)));
  if (values.size !== 1) return "—";
  const value = read(nodes[0]);
  return value === null || value === undefined || value === "" ? "（無）" : String(value);
}

// One integer metre delta applied to every node: the same translation for
// each, never a per-node rounding.
export function groupMoves(settlement, nodeIds, dx, dy) {
  const ids = new Set(nodeIds);
  const step = [Math.round(dx), Math.round(dy)];
  return settlement.nodes
    .filter((node) => ids.has(node.id))
    .map((node) => ({ node_id: node.id, x_m: node.local_m[0] + step[0], y_m: node.local_m[1] + step[1] }));
}

// -- road rows and blockers --------------------------------------------------------
const lengthText = (length) => (length === null || length === undefined ? "" : ` · ${Math.round(length)} m`);

export function outgoingRows(settlement, nodeId) {
  return settlement.roads
    .filter((road) => road.source === nodeId)
    .map((road) => ({
      road: roadRef(settlement.id, road.source, road.destination),
      label: `${compassLabel(road.direction)} → ${nodeName(settlement, road.destination)}${lengthText(road.length_m)}`,
    }));
}

export function incomingRows(settlement, nodeId) {
  return settlement.roads
    .filter((road) => road.destination === nodeId)
    .map((road) => ({
      road: roadRef(settlement.id, road.source, road.destination),
      label: `← ${compassLabel(road.direction)} 來自 ${nodeName(settlement, road.source)}`,
    }));
}

export function roadLabel(settlement, road) {
  return `${nodeName(settlement, road.source)} → ${nodeName(settlement, road.destination)}（${compassLabel(road.direction)}）`;
}

// Map references that must be removed explicitly before the nodes can be
// deleted (the service refuses them the same way; nothing cascades): roads
// in either direction, wilderness gates, the city gate, interior exteriors
// and district landmarks. Each row links to the declaring object (an
// entrance row to its relationship, where it is removed separately).
export function nodeBlockers(world, refs) {
  const rows = [];
  const selection = oneDocumentNodes(refs);
  const settlement = selection && findSettlement(world, selection.settlementId);
  if (!settlement) return rows;
  const ids = new Set(selection.nodeIds);
  const path = settlement.relative_path;
  for (const road of settlement.roads) {
    if (ids.has(road.source) || ids.has(road.destination)) {
      rows.push({ kind: "道路", label: roadLabel(settlement, road), ref: roadRef(settlement.id, road.source, road.destination), source: path, external: false });
    }
  }
  for (const gate of settlement.wilderness_entry?.gates ?? []) {
    if (ids.has(gate.destination_node)) {
      rows.push({ kind: "野外入口", label: `${compassLabel(gate.return_direction)} → ${nodeName(settlement, gate.destination_node)}`, ref: gateRef(settlement.id, gate.return_direction), source: path, external: false });
    }
  }
  if (settlement.city_gate && ids.has(settlement.city_gate.node)) {
    rows.push({ kind: "城門", label: nodeName(settlement, settlement.city_gate.node), ref: cityGateRef(settlement.id), source: path, external: false });
  }
  for (const interior of world.interiors ?? []) {
    const exterior = interior.exterior;
    if (exterior?.settlement === settlement.id && ids.has(exterior.node)) {
      rows.push({ kind: "入口", label: `⌂ ${interior.id}`, ref: exteriorRef(interior.id), source: interior.relative_path, external: false });
    }
  }
  for (const district of world.districts ?? []) {
    const landmark = district.landmark ?? {};
    if (landmark.domain === "settlement_node" && landmark.map_id === settlement.id && ids.has(landmark.object_id)) {
      rows.push({ kind: "地標", label: `${district.district_name_zh}（${district.id}）`, ref: `district:${district.id}`, source: district.relative_path, external: false });
    }
  }
  return rows;
}

// -- command descriptors ----------------------------------------------------------
// { name, documentId, arguments }; documentCommand adds the expected
// fingerprint from the snapshot the command is built against.
const command = (name, settlementId, args) => ({
  name,
  documentId: settlementDocument(settlementId),
  arguments: { settlement_id: settlementId, ...args },
});

export const createSettlement = (settlementId, locationId, options) =>
  command("create_settlement", settlementId, { location_id: locationId, options });
export const settlementField = (settlementId, field, value) => command("set_settlement_field", settlementId, { field, value });
export const createNode = (settlementId, nodeId, fields) => command("create_node", settlementId, { node_id: nodeId, fields });
export const duplicateNode = (settlementId, nodeId, newNodeId, [x, y]) =>
  command("duplicate_node", settlementId, { node_id: nodeId, new_node_id: newNodeId, x_m: x, y_m: y });
export const nodeFields = (settlementId, nodeId, fields) => command("set_node_fields", settlementId, { node_id: nodeId, fields });
export const moveNodes = (settlementId, moves) => command("move_nodes", settlementId, { moves });
export const deleteNodes = (settlementId, nodeIds) => command("delete_nodes", settlementId, { node_ids: nodeIds });
export const createRoad = (settlementId, source, destination, direction, bends = [], reverse = null) =>
  command("create_road", settlementId, { source, destination, direction, bends, return: reverse });
export const setRoad = (settlementId, source, destination, value) => command("set_road", settlementId, { source, destination, value });
export const deleteRoad = (settlementId, source, destination) => command("delete_road", settlementId, { source, destination });
export const insertBend = (settlementId, source, destination, index, point) =>
  command("insert_bend", settlementId, { source, destination, index, point });
export const moveBend = (settlementId, source, destination, index, point) =>
  command("move_bend", settlementId, { source, destination, index, point });
export const removeBend = (settlementId, source, destination, index) => command("remove_bend", settlementId, { source, destination, index });

// The polyline of a road in local metres: source, bends, destination.
export function roadPoints(settlement, road) {
  const at = (id) => settlement.nodes.find((node) => node.id === id)?.local_m;
  return [at(road.source), ...road.bends, at(road.destination)].filter(Boolean);
}

// The bend 前方插入 / 後方插入 adds next to bend `index`, halfway to its
// neighbour on the polyline; with no index (加彎點) it is appended halfway
// along the road's last segment.
export function bendInsertion(settlement, road, index, before) {
  const points = roadPoints(settlement, road);
  const half = (a, b) => [Math.round((a[0] + b[0]) / 2), Math.round((a[1] + b[1]) / 2)];
  if (index === null || index === undefined) {
    return { index: road.bends.length, point: half(points.at(-2), points.at(-1)) };
  }
  const here = points[index + 1];
  const other = points[before ? index : index + 2];
  return { index: before ? index : index + 1, point: half(here, other) };
}

// The removal of a selected settlement road or bend (sent directly; neither
// is a qualified object other documents can name), or null.
export function settlementRemoval(ref) {
  const parsed = parseSettlementRef(ref);
  if (parsed?.kind === "road") return deleteRoad(parsed.settlementId, parsed.source, parsed.destination);
  if (parsed?.kind === "bend") return removeBend(parsed.settlementId, parsed.source, parsed.destination, parsed.index);
  return null;
}
