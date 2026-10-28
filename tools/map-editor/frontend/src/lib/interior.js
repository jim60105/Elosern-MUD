// Interior authoring helpers (frontend design §4.3): editor-local connection
// references, the directed connection rows with their two-way pairing, the
// explanatory delete blockers of a room, the read-only service identity of a
// joined room, the 自動排列 arrangement and the named single-document command
// descriptors.
//
// Interiors are coordinate-free. Layout positions are editor-only grid steps
// written to `content/map-editor-layouts/<id>.yaml`; nothing here produces a
// distance, a length or a world coordinate. The service and the core schema
// decide validity.

import { LAYOUT_DIRECTORY, layoutDocumentId } from "./layout_edit.js";

export { layoutDocumentId };

const ID = "[a-z][a-z0-9_]*";
const ROOM = new RegExp(`^interior_room:(${ID}):(${ID})$`);
const CONNECTION = new RegExp(`^connection:(${ID}):(${ID})>(${ID})/(.+)$`);

export const IDENTIFIER = /^[a-z][a-z0-9_]*$/;
export const roomRef = (interiorId, roomId) => `interior_room:${interiorId}:${roomId}`;
// The label is free text: percent-encoding keeps `:`, `>` and `/` out of the
// structure, so (interior, source, destination, label) round-trips exactly.
export const connectionRef = (interiorId, source, destination, label) =>
  `connection:${interiorId}:${source}>${destination}/${encodeURIComponent(label)}`;
export const interiorDocument = (interiorId) => `content/maps/interiors/${interiorId}.yaml`;
export { LAYOUT_DIRECTORY };

// { kind: room | connection, interiorId, roomId? | source, destination, label }
export function parseInteriorRef(ref) {
  const room = ROOM.exec(ref ?? "");
  if (room) return { kind: "room", interiorId: room[1], roomId: room[2] };
  const connection = CONNECTION.exec(ref ?? "");
  if (!connection) return null;
  let label;
  try {
    label = decodeURIComponent(connection[4]);
  } catch {
    return null;
  }
  return { kind: "connection", interiorId: connection[1], source: connection[2], destination: connection[3], label };
}

export function findInterior(world, interiorId) {
  return world?.interiors?.find((row) => row.id === interiorId) ?? null;
}

export function findConnection(interior, source, destination, label) {
  return (
    interior?.connections?.find((row) => row.source === source && row.destination === destination && row.label === label) ?? null
  );
}

export function roomName(interior, roomId) {
  return interior?.rooms?.find((room) => room.id === roomId)?.name_zh ?? roomId;
}

// The reverse connection of a two-way pair (the first one back), else null.
export function reverseOf(interior, connection) {
  return interior.connections.find((row) => row.source === connection.destination && row.destination === connection.source) ?? null;
}

// Canvas label of each connection: a two-way pair reads `去 ⇄ 回` once (on
// the first of the two in authored order), a one-way connection its label.
export function connectionLabels(interior) {
  const labels = new Map();
  const paired = new Set();
  interior.connections.forEach((connection, index) => {
    const key = `${index}`;
    if (paired.has(index)) {
      labels.set(key, "");
      return;
    }
    const back = interior.connections.findIndex(
      (row, other) => other > index && !paired.has(other) && row.source === connection.destination && row.destination === connection.source,
    );
    if (back >= 0) {
      paired.add(back);
      labels.set(key, `${connection.label} ⇄ ${interior.connections[back].label}`);
    } else {
      labels.set(key, connection.label);
    }
  });
  return labels;
}

// Directed rows of one room: `label → room` leaving it, `← label 來自 room`
// arriving, each marked 單向 when no connection returns. `sameLabel` marks a
// second connection leaving the same room under the same name (the game would
// get two exits with one name): an explanation, never a refusal.
export function connectionRows(interior, roomId) {
  const ref = (row) => connectionRef(interior.id, row.source, row.destination, row.label);
  const outgoing = interior.connections
    .filter((row) => row.source === roomId)
    .map((row) => ({
      ref: ref(row),
      label: `${row.label} → ${roomName(interior, row.destination)}`,
      oneWay: !reverseOf(interior, row),
      sameLabel: interior.connections.filter((other) => other.source === roomId && other.label === row.label).length > 1,
    }));
  const incoming = interior.connections
    .filter((row) => row.destination === roomId)
    .map((row) => ({ ref: ref(row), label: `← ${row.label} 來自 ${roomName(interior, row.source)}`, oneWay: !reverseOf(interior, row) }));
  return { outgoing, incoming };
}

// Map references that must be removed before the room can be deleted (the
// service refuses them the same way; nothing cascades).
export function roomBlockers(world, ref) {
  const parsed = parseInteriorRef(ref);
  const interior = parsed?.kind === "room" ? findInterior(world, parsed.interiorId) : null;
  if (!interior) return [];
  const roomId = parsed.roomId;
  const path = interior.relative_path;
  const rows = [];
  for (const row of interior.connections) {
    if (row.source === roomId || row.destination === roomId) {
      rows.push({
        kind: "連接",
        label: `${roomName(interior, row.source)} → ${roomName(interior, row.destination)}（${row.label}）`,
        ref: connectionRef(interior.id, row.source, row.destination, row.label),
        source: path,
        external: false,
      });
    }
  }
  const exterior = interior.exterior;
  if (exterior?.room === roomId) {
    rows.push({ kind: "入口", label: `⌂ ${exterior.settlement} · ${exterior.node}`, ref: `settlement_node:${exterior.settlement}:${exterior.node}`, source: path, external: false });
  }
  for (const other of world.interiors) {
    for (const link of other.interior_links ?? []) {
      const own = other.id === interior.id && link.source_room === roomId;
      const target = link.target_interior === interior.id && link.target_room === roomId;
      if (own || target) {
        rows.push({ kind: "室內連結", label: `${other.id} · ${link.source_room} → ${link.target_interior} · ${link.target_room}`, ref: roomRef(other.id, link.source_room), source: other.relative_path, external: false });
      }
    }
  }
  for (const district of world.districts ?? []) {
    const landmark = district.landmark ?? {};
    if (landmark.domain === "interior_room" && landmark.map_id === interior.id && landmark.object_id === roomId) {
      rows.push({ kind: "地標", label: `${district.district_name_zh}（${district.id}）`, ref: `district:${district.id}`, source: district.relative_path, external: false });
    }
  }
  return rows;
}

// Service and host records that join this room through the reference index
// (read-only identity context; no service record is ever required).
export const SERVICE_DOMAINS = Object.freeze(["places", "service_hosts"]);
export function serviceIdentity(incomingExternal, ref) {
  return (incomingExternal?.[ref] ?? [])
    .filter((item) => SERVICE_DOMAINS.includes(item.source_domain))
    .map((item) => ({ source: item.source, domain: item.source_domain, file: item.source_file }));
}

// 自動排列: a deterministic layered arrangement over the authored graph. The
// entrance room (the exterior's room, else the first room) is column 0; each
// connection, followed either way, adds a column; rows follow authored order.
// Unreached rooms follow in further columns, three per column, in authored
// order. The result is presentation only and is never a distance.
export const ARRANGE_ROWS = 3;
export function arrangement(interior) {
  const order = interior.rooms.map((room) => room.id);
  if (!order.length) return [];
  const neighbours = new Map(order.map((id) => [id, []]));
  for (const row of interior.connections) {
    if (neighbours.has(row.source) && neighbours.has(row.destination)) {
      neighbours.get(row.source).push(row.destination);
      neighbours.get(row.destination).push(row.source);
    }
  }
  const rank = new Map(order.map((id, index) => [id, index]));
  const start = neighbours.has(interior.exterior?.room) ? interior.exterior.room : order[0];
  const depth = new Map([[start, 0]]);
  const queue = [start];
  while (queue.length) {
    const id = queue.shift();
    const next = [...neighbours.get(id)].sort((a, b) => rank.get(a) - rank.get(b));
    for (const other of next) {
      if (!depth.has(other)) {
        depth.set(other, depth.get(id) + 1);
        queue.push(other);
      }
    }
  }
  const columns = new Map();
  for (const id of order) {
    if (!depth.has(id)) continue;
    const column = depth.get(id);
    if (!columns.has(column)) columns.set(column, []);
    columns.get(column).push(id);
  }
  const positions = [];
  for (const [column, ids] of [...columns.entries()].sort((a, b) => a[0] - b[0])) {
    ids.forEach((id, row) => positions.push({ room_id: id, x: column, y: row }));
  }
  const firstFree = columns.size ? Math.max(...columns.keys()) + 1 : 0;
  order
    .filter((id) => !depth.has(id))
    .forEach((id, index) => positions.push({ room_id: id, x: firstFree + Math.floor(index / ARRANGE_ROWS), y: index % ARRANGE_ROWS }));
  return positions;
}

// -- command descriptors ----------------------------------------------------------
// { name, documentId, arguments }; documentCommand adds the expected
// fingerprint from the snapshot the command is built against.
const command = (name, interiorId, args) => ({
  name,
  documentId: interiorDocument(interiorId),
  arguments: { interior_id: interiorId, ...args },
});

export const blankRoom = ({ name_zh = "", desc_zh = "", scene_archetype = null, art_key = null } = {}) => ({
  name_zh,
  desc_zh,
  scene_archetype,
  art_key,
});
export const createInterior = (interiorId, roomId, fields) => command("create_interior", interiorId, { room_id: roomId, fields });
export const deleteInterior = (interiorId) => command("delete_interior", interiorId, {});
export const createRoom = (interiorId, roomId, fields) => command("create_room", interiorId, { room_id: roomId, fields });
export const duplicateRoom = (interiorId, roomId, newRoomId) => command("duplicate_room", interiorId, { room_id: roomId, new_room_id: newRoomId });
export const roomFields = (interiorId, roomId, fields) => command("set_room_fields", interiorId, { room_id: roomId, fields });
export const deleteRoom = (interiorId, roomId) => command("delete_room", interiorId, { room_id: roomId });
export const createConnection = (interiorId, source, destination, label, returnLabel = null) =>
  command("create_connection", interiorId, { source, destination, label, return_label: returnLabel });
export const setConnection = (interiorId, source, destination, label, value) =>
  command("set_connection", interiorId, { source, destination, label, value });
export const deleteConnection = (interiorId, source, destination, label) =>
  command("delete_connection", interiorId, { source, destination, label });
export const arrangeLayout = (interiorId, positions) => ({
  name: "arrange_interior_layout",
  documentId: layoutDocumentId(interiorId),
  arguments: { interior_id: interiorId, positions },
});

// The removal of a selected connection (sent directly: no other document can
// name it), or null.
export function interiorRemoval(ref) {
  const parsed = parseInteriorRef(ref);
  return parsed?.kind === "connection" ? deleteConnection(parsed.interiorId, parsed.source, parsed.destination, parsed.label) : null;
}
