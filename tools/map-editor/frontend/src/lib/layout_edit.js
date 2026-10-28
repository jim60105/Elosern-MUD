// Interior layout positions: the one place that converts between the stored
// editor layout grid (`content/map-editor-layouts/<id>.yaml`, y grows down
// the screen) and scene points (north up). Layout positions are editor-only
// grid steps, never metres or world coordinates.

export const INTERIOR_COLUMNS = 3;
export const LAYOUT_DIRECTORY = "content/map-editor-layouts";
export const ABSENT = "absent";

export function layoutDocumentId(interiorId) {
  return `${LAYOUT_DIRECTORY}/${interiorId}.yaml`;
}

// The expected presence for a guarded write: the layout's content hash, or
// the explicit absence sentinel before the first layout exists.
export function layoutFingerprint(world, interiorId) {
  const layout = world?.layouts?.find((item) => item.id === interiorId);
  return layout ? layout.fingerprint : ABSENT;
}

// Stored grid position of a room: its layout entry, else the list fallback.
export function storedPosition(interior, roomId) {
  const index = interior.rooms.findIndex((room) => room.id === roomId);
  if (index < 0) return null;
  const layout = interior.rooms[index].layout_position;
  if (layout) return [layout[0], layout[1]];
  return [index % INTERIOR_COLUMNS, Math.floor(index / INTERIOR_COLUMNS)];
}

export function toScene([x, y]) {
  return { x, y: -y };
}

export function fromScene(point) {
  // `+ 0` folds a negative zero into 0 so it serialises as a plain integer.
  return [Math.round(point.x) + 0, Math.round(-point.y) + 0];
}

const NUDGES = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };

export function nudgeDelta(key) {
  return NUDGES[key] ?? null;
}

// `interior_room:<interior>:<room>` -> { interiorId, roomId }, else null.
export function parseRoomRef(ref) {
  const match = /^interior_room:([^:]+):([^:]+)$/.exec(ref ?? "");
  return match ? { interiorId: match[1], roomId: match[2] } : null;
}

export function findInterior(world, interiorId) {
  return world?.interiors?.find((item) => item.id === interiorId) ?? null;
}

// The complete command for one room move, built against `world` at send time.
export function moveCommand(world, interiorId, roomId, position) {
  return {
    name: "move_interior_layout",
    documentId: layoutDocumentId(interiorId),
    expected: layoutFingerprint(world, interiorId),
    arguments: { interior_id: interiorId, room_id: roomId, x: position[0], y: position[1] },
  };
}
