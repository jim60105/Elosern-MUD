// A mutation applies to exactly one owning document. A selection whose
// objects belong to different documents (rooms of two interiors, or a room
// plus a settlement node) cannot be mutated together; the service refuses it
// as cross_document as well.

import { layoutDocumentId, parseRoomRef } from "./layout_edit.js";

// The document a layout mutation of this object would write, else null.
export function layoutOwner(ref) {
  const room = parseRoomRef(ref);
  return room ? layoutDocumentId(room.interiorId) : null;
}

export function selectionOwner(refs) {
  const list = [...(refs ?? [])];
  if (!list.length) return { owner: null, reason: "empty" };
  const owners = new Set(list.map(layoutOwner));
  if (owners.has(null)) return { owner: null, reason: "not_editable" };
  if (owners.size > 1) return { owner: null, reason: "cross_document", owners: [...owners].sort() };
  return { owner: [...owners][0], reason: null };
}
