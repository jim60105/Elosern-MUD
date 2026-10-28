// A mutation applies to exactly one owning document. A selection whose
// objects belong to different documents (rooms of two interiors, or a room
// plus a settlement node) cannot be mutated together; the service refuses it
// as cross_document as well, so such a selection is inspect/copy only.

import { layoutDocumentId, parseRoomRef } from "./layout_edit.js";

export const CROSS_DOCUMENT_REASON = "跨文件的選取只能檢視與複製";

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

// The owning source documents of a selection (inspection and copy context).
export function selectionSummary(catalog, refs) {
  const entries = [...(refs ?? [])].map((ref) => catalog.get(ref)).filter(Boolean);
  const owners = [...new Set(entries.map((entry) => entry.relativePath))].sort();
  const crossDocument = owners.length > 1;
  return {
    count: entries.length,
    entries,
    owners,
    crossDocument,
    reason: crossDocument ? CROSS_DOCUMENT_REASON : null,
  };
}
