// The inline delete explanation (frontend design §5.4). It is explanatory
// only: the service's execution-time reference guard is the authority, and
// this slice ships no object-removing command, so nothing here sends a write.
//
// Order, first match wins:
//   cross-document     a selection spanning documents is inspect/copy only;
//   index-unavailable  the external index is not current, so external
//                      references are unknown and deletion is refused (an
//                      index that is not current never proves anything);
//   referenced         the current index names external references, exactly
//                      what the service guard enforces;
//   unavailable        nothing refuses, but no delete command exists for this
//                      kind of object yet (domain tools register it).
// Map-internal incoming relations are listed alongside as references that a
// deletion would leave dangling; they never cascade.

export const INDEX_UNAVAILABLE = "index-unavailable";
export const REFERENCED = "referenced";
export const CROSS_DOCUMENT = "cross-document";
export const UNAVAILABLE = "unavailable";

export function deletionRefusal({ externalStatus, summary, relations = [] }) {
  const external = relations.filter((row) => row.external);
  const internal = relations.filter((row) => !row.external);
  if (summary?.crossDocument) {
    return { key: CROSS_DOCUMENT, external: [], internal: [], reasons: [] };
  }
  if (!externalStatus?.current) {
    return {
      key: INDEX_UNAVAILABLE,
      external: [],
      internal,
      reasons: [...(externalStatus?.reasons ?? [])],
    };
  }
  if (external.length) {
    return { key: REFERENCED, external, internal, reasons: [] };
  }
  return { key: UNAVAILABLE, external: [], internal, reasons: [] };
}
