// Cross-layer entrance relationships (frontend design §4.4): editor-local
// references, one read-only view per relationship naming both endpoints,
// their directional labels and the one-way/two-way meaning, the endpoint
// rules of the qualified-object selector and the named single-document
// command descriptors.
//
// Each relationship is stored once in its owning document; nothing here
// writes or implies a mirrored reverse record. Every value comes from the
// service's projection (the wilderness approach cell is the core's); the
// service decides validity. Endpoints are always sent as qualified IDs.

import { compassLabel, findSettlement, settlementDocument } from "./settlement.js";
import { findInterior, interiorDocument, roomName } from "./interior.js";
import { footprintRef } from "./continent.js";
import { cityGateRef, exteriorRef, gateRef, linkRef } from "./relationship_refs.js";

const ID = "[a-z][a-z0-9_]*";
const GATE = new RegExp(`^gate:(${ID}):(${ID})$`);
const CITY_GATE = new RegExp(`^city_gate:(${ID})$`);
const EXTERIOR = new RegExp(`^exterior:(${ID})$`);
const LINK = new RegExp(`^interior_link:(${ID}):(${ID})>(${ID}):(${ID})/(.+)$`);

export { cityGateRef, exteriorRef, gateRef, linkRef };
export const nodeRef = (settlementId, nodeId) => `settlement_node:${settlementId}:${nodeId}`;
export const roomRef = (interiorId, roomId) => `interior_room:${interiorId}:${roomId}`;

export const KINDS = Object.freeze({
  gate: "野外入口",
  city_gate: "起始房間入口",
  exterior: "外部入口",
  interior_link: "室內連結",
});

// { kind, settlementId? | interiorId?, direction?, source?, targetInterior?, targetRoom?, label? }
export function parseRelationshipRef(ref) {
  const text = ref ?? "";
  let match = GATE.exec(text);
  if (match) return { kind: "gate", settlementId: match[1], direction: match[2] };
  match = CITY_GATE.exec(text);
  if (match) return { kind: "city_gate", settlementId: match[1] };
  match = EXTERIOR.exec(text);
  if (match) return { kind: "exterior", interiorId: match[1] };
  match = LINK.exec(text);
  if (!match) return null;
  let label;
  try {
    label = decodeURIComponent(match[5]);
  } catch {
    return null;
  }
  return { kind: "interior_link", interiorId: match[1], source: match[2], targetInterior: match[3], targetRoom: match[4], label };
}

export const isRelationshipRef = (ref) => parseRelationshipRef(ref) !== null;

const DIRECTIONS = ["n", "ne", "e", "se", "s", "sw", "w", "nw"];
// The authored gate's outward face (the game's documented meaning: leaving
// the gate room toward the wilderness is opposite the return direction).
function outward(direction) {
  const index = DIRECTIONS.indexOf(direction);
  return index < 0 ? direction : DIRECTIONS[(index + 4) % 8];
}

const aliasText = (aliases) => (aliases?.length ? `（別名 ${aliases.join("、")}）` : "");

function nodeEnd(settlement, nodeId, label) {
  const node = settlement?.nodes.find((row) => row.id === nodeId) ?? null;
  return {
    role: "node",
    domain: "settlement",
    domainLabel: "據點",
    ref: settlement ? nodeRef(settlement.id, nodeId) : null,
    mapId: settlement?.id ?? null,
    name: node?.key ?? nodeId,
    present: Boolean(node),
    label,
    position: node ? `東 ${node.local_m[0]} m、北 ${node.local_m[1]} m（${settlement.id} 地方座標）` : null,
  };
}

function roomEnd(interior, interiorId, roomId, label) {
  const room = interior?.rooms.find((row) => row.id === roomId) ?? null;
  return {
    role: "room",
    domain: "interior",
    domainLabel: "室內",
    ref: roomRef(interiorId, roomId),
    mapId: interiorId,
    name: room ? roomName(interior, roomId) : roomId,
    present: Boolean(room),
    label,
    position: null,
  };
}

// The view of one relationship, or null when it is not in the snapshot.
export function relationshipView(world, ref) {
  const parsed = parseRelationshipRef(ref);
  if (!world || !parsed) return null;
  if (parsed.kind === "gate" || parsed.kind === "city_gate") {
    const settlement = findSettlement(world, parsed.settlementId);
    if (!settlement) return null;
    const base = { ref, kind: parsed.kind, kindLabel: KINDS[parsed.kind], ownerId: settlement.id, ownerPath: settlement.relative_path };
    if (parsed.kind === "gate") {
      const gate = (settlement.wilderness_entry?.gates ?? []).find((row) => row.return_direction === parsed.direction);
      if (!gate) return null;
      const cell = gate.approach_cell;
      const wild = {
        role: "wilderness",
        domain: "continent",
        domainLabel: "野外",
        // The wilderness end is a computed cell, not an object: it is
        // reached through the settlement's footprint on the continent.
        ref: settlement.footprint ? footprintRef(settlement.id) : null,
        mapId: null,
        name: cell ? `野外格 (${cell[0]}, ${cell[1]})` : "野外格（無法計算）",
        present: Boolean(cell),
        label: `往 ${compassLabel(gate.return_direction)} 進入據點`,
        position: cell ? `格 (${cell[0]}, ${cell[1]})（1 km 格；核心依佔地與方向計算，唯讀）` : null,
      };
      const node = nodeEnd(settlement, gate.destination_node, `往 ${compassLabel(outward(gate.return_direction))} 回到野外`);
      return {
        ...base,
        title: `野外 ⇄ ${node.name}`,
        twoWay: true,
        oneWayFixed: false,
        values: { direction: gate.return_direction, node: node.ref },
        endpoints: [wild, node],
      };
    }
    const gate = settlement.city_gate;
    if (!gate) return null;
    const start = {
      role: "start",
      domain: null,
      domainLabel: "起始房間",
      ref: null,
      mapId: null,
      name: "起始房間",
      present: true,
      label: `出口「${gate.exit_key}」${aliasText(gate.exit_aliases)}`,
      position: null,
    };
    const node = nodeEnd(settlement, gate.node, "沒有回程（單向）");
    return {
      ...base,
      title: `起始房間 → ${node.name}`,
      twoWay: false,
      oneWayFixed: true,
      values: { node: node.ref, exit_key: gate.exit_key, exit_aliases: [...(gate.exit_aliases ?? [])] },
      endpoints: [start, node],
    };
  }
  const interior = findInterior(world, parsed.interiorId);
  if (!interior) return null;
  const base = { ref, kind: parsed.kind, kindLabel: KINDS[parsed.kind], ownerId: interior.id, ownerPath: interior.relative_path };
  if (parsed.kind === "exterior") {
    const exterior = interior.exterior;
    if (!exterior) return null;
    const settlement = findSettlement(world, exterior.settlement);
    const outer = nodeEnd(settlement, exterior.node, `進入 →「${exterior.doorway_key}」${aliasText(exterior.doorway_aliases)}`);
    if (!settlement) Object.assign(outer, { ref: nodeRef(exterior.settlement, exterior.node), mapId: exterior.settlement });
    const inner = roomEnd(interior, interior.id, exterior.room, "離開 → 遊戲提供的固定返回出口");
    return {
      ...base,
      title: `${outer.name} ⇄ ${inner.name}`,
      twoWay: true,
      oneWayFixed: false,
      values: {
        room: inner.ref,
        node: nodeRef(exterior.settlement, exterior.node),
        doorway_key: exterior.doorway_key,
        doorway_aliases: [...(exterior.doorway_aliases ?? [])],
      },
      endpoints: [outer, inner],
    };
  }
  const link = (interior.interior_links ?? []).find(
    (row) =>
      row.source_room === parsed.source &&
      row.target_interior === parsed.targetInterior &&
      row.target_room === parsed.targetRoom &&
      row.label === parsed.label,
  );
  if (!link) return null;
  const twoWay = link.return_label !== null && link.return_label !== undefined;
  const source = { ...roomEnd(interior, interior.id, link.source_room, `去 →「${link.label}」`), role: "source" };
  const target = roomEnd(
    findInterior(world, link.target_interior),
    link.target_interior,
    link.target_room,
    twoWay ? `回 →「${link.return_label}」` : "沒有回程（單向）",
  );
  target.role = "target";
  return {
    ...base,
    title: `${source.name} ${twoWay ? "⇄" : "→"} ${target.name}`,
    twoWay,
    oneWayFixed: false,
    values: { source: source.ref, target: target.ref, label: link.label, return_label: link.return_label ?? null },
    endpoints: [source, target],
  };
}

// Every relationship of the snapshot, in authored order.
export function relationshipRefs(world) {
  const refs = [];
  for (const settlement of world?.settlements ?? []) {
    for (const gate of settlement.wilderness_entry?.gates ?? []) refs.push(gateRef(settlement.id, gate.return_direction));
    if (settlement.city_gate) refs.push(cityGateRef(settlement.id));
  }
  for (const interior of world?.interiors ?? []) {
    if (interior.exterior) refs.push(exteriorRef(interior.id));
    for (const link of interior.interior_links ?? []) refs.push(linkRef(interior.id, link));
  }
  return refs;
}

// The map a relationship is shown on: its owner's.
export function ownerMap(ref) {
  const parsed = parseRelationshipRef(ref);
  if (!parsed) return null;
  return parsed.settlementId
    ? { domain: "settlement", mapId: parsed.settlementId }
    : { domain: "interior", mapId: parsed.interiorId };
}

const placeOf = (endpoint) => `${endpoint.domain}:${endpoint.mapId ?? ""}`;

// 前往另一端: the navigable endpoint off the map on display (the far end);
// when both ends are on it, the target (the second end). Null when no end is
// a navigable object (the starting room is not a map object).
export function otherEnd(view, { domain, mapId }) {
  const navigable = (view?.endpoints ?? []).filter((endpoint) => endpoint.ref && endpoint.present);
  if (!navigable.length) return null;
  const here = `${domain}:${mapId ?? ""}`;
  const away = navigable.filter((endpoint) => placeOf(endpoint) !== here);
  return (away.at(-1) ?? navigable.at(-1)) || null;
}

// -- the qualified-object selector -----------------------------------------------
// The ends whose endpoint can be changed (更換端點…), by role.
export function editableRoles(view) {
  if (!view) return [];
  if (view.kind === "gate" || view.kind === "city_gate") return ["node"];
  if (view.kind === "exterior") return ["node", "room"];
  return ["source", "target"];
}

// The endpoint rule of each editable end: the catalog kind and, where the
// relationship requires it, the one map the end must be on.
export function endpointRule(view, role) {
  if (!view) return null;
  if (view.kind === "gate" || view.kind === "city_gate") return { kind: "node", mapId: view.ownerId };
  if (view.kind === "exterior") return role === "room" ? { kind: "room", mapId: view.ownerId } : { kind: "node", mapId: null };
  if (role === "source") return { kind: "room", mapId: view.ownerId };
  return { kind: "room", mapId: null };
}

// Catalog entries an end may name, ranked by a name/ID query; equal names
// are counted so each result can be told apart by its parent map.
export function endpointChoices(catalog, rule, query = "", limit = 40) {
  const needle = String(query ?? "").trim().toLowerCase();
  const allowed = [...catalog.values()].filter(
    (entry) => entry.kind === rule?.kind && (!rule.mapId || entry.mapId === rule.mapId),
  );
  const score = (entry) => {
    if (!needle) return 0;
    const fields = [entry.label, entry.id, entry.ref].map((value) => String(value ?? "").toLowerCase());
    if (fields.some((value) => value === needle)) return 0;
    if (fields.some((value) => value.startsWith(needle))) return 1;
    if (fields.some((value) => value.includes(needle))) return 2;
    return null;
  };
  const ranked = allowed
    .map((entry, order) => ({ entry, order, rank: score(entry) }))
    .filter((row) => row.rank !== null)
    .sort((a, b) => a.rank - b.rank || a.order - b.order)
    .slice(0, limit)
    .map((row) => row.entry);
  const counts = new Map();
  for (const entry of allowed) counts.set(entry.label, (counts.get(entry.label) ?? 0) + 1);
  return ranked.map((entry) => ({ ref: entry.ref, label: entry.label, parent: entry.parentLabel, sameLabel: counts.get(entry.label) }));
}

// -- command descriptors ------------------------------------------------------------
const settlementCommand = (name, settlementId, args) => ({
  name,
  documentId: settlementDocument(settlementId),
  arguments: { settlement_id: settlementId, ...args },
});
const interiorCommand = (name, interiorId, args) => ({
  name,
  documentId: interiorDocument(interiorId),
  arguments: { interior_id: interiorId, ...args },
});

export const createGate = (settlementId, direction, node) =>
  settlementCommand("create_wilderness_gate", settlementId, { return_direction: direction, node });
export const setGate = (settlementId, direction, value) =>
  settlementCommand("set_wilderness_gate", settlementId, { return_direction: direction, value });
export const deleteGate = (settlementId, direction) =>
  settlementCommand("delete_wilderness_gate", settlementId, { return_direction: direction });
export const removeWildernessEntry = (settlementId) => settlementCommand("remove_wilderness_entry", settlementId, {});
export const setCityGate = (settlementId, value) => settlementCommand("set_city_gate", settlementId, { value });
export const setExterior = (interiorId, value) => interiorCommand("set_exterior", interiorId, { value });
export const createLink = (interiorId, source, target, label, returnLabel = null) =>
  interiorCommand("create_interior_link", interiorId, { source, target, label, return_label: returnLabel });
export const setLink = (interiorId, current, value) =>
  interiorCommand("set_interior_link", interiorId, { source: current.source, target: current.target, label: current.label, value });
export const deleteLink = (interiorId, current) =>
  interiorCommand("delete_interior_link", interiorId, { source: current.source, target: current.target, label: current.label });

// One edit of a relationship's values as its one command, and the reference
// the relationship has afterwards (its identity can change with the edit).
export function editCommand(view, patch) {
  const values = { ...view.values, ...patch };
  if (view.kind === "gate") {
    return {
      descriptor: setGate(view.ownerId, view.values.direction, { return_direction: values.direction, node: values.node }),
      ref: gateRef(view.ownerId, values.direction),
    };
  }
  if (view.kind === "city_gate") {
    const value = { node: values.node, exit_key: values.exit_key, exit_aliases: values.exit_aliases };
    return { descriptor: setCityGate(view.ownerId, value), ref: view.ref };
  }
  if (view.kind === "exterior") {
    const value = { room: values.room, node: values.node, doorway_key: values.doorway_key, doorway_aliases: values.doorway_aliases };
    return { descriptor: setExterior(view.ownerId, value), ref: view.ref };
  }
  const target = /^interior_room:([^:]+):([^:]+)$/.exec(values.target);
  const source = /^interior_room:([^:]+):([^:]+)$/.exec(values.source);
  const next = { source_room: source?.[2], target_interior: target?.[1], target_room: target?.[2], label: values.label };
  return {
    descriptor: setLink(view.ownerId, view.values, { source: values.source, target: values.target, label: values.label, return_label: values.return_label }),
    ref: source && target ? linkRef(view.ownerId, next) : null,
  };
}

// The removal of a selected relationship (sent directly: it is not a
// qualified object any other document can name), or null.
export function relationshipRemoval(world, ref) {
  const view = relationshipView(world, ref);
  if (!view) return null;
  if (view.kind === "gate") return deleteGate(view.ownerId, view.values.direction);
  if (view.kind === "city_gate") return setCityGate(view.ownerId, null);
  if (view.kind === "exterior") return setExterior(view.ownerId, null);
  return deleteLink(view.ownerId, view.values);
}

// The editor-only place of the dashed exterior card: one layout column to the
// left of the room it opens onto (presentation, never a distance).
export function exteriorCardPosition(roomPosition) {
  return roomPosition ? { x: roomPosition.x - 1, y: roomPosition.y } : null;
}

// The creation request of the 入口 E / 外部入口 E tools for the picked node
// (settlement) or room (interior); typed values live on in its defaults.
export function entranceRequest(mapId, objectId, domain = "interior") {
  if (domain === "settlement") {
    return { type: "entrance", defaults: { kind: "gate", node: nodeRef(mapId, objectId), direction: "", exit_key: "", exit_aliases: "" } };
  }
  return {
    type: "entrance",
    defaults: {
      kind: "exterior", room: roomRef(mapId, objectId), node: "", doorway_key: "", doorway_aliases: "",
      target: "", label: "", two_way: false, return_label: "",
    },
  };
}
