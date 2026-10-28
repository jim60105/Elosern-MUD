// The inline delete explanation (frontend design §5.4). It is explanatory
// only: the service's execution-time reference guard is the authority. A
// selection this explanation does not refuse, of a kind that has a delete
// command (a location, continental control points, passes, sites and
// waterways), is sent as that one command.
//
// Order, first match wins:
//   cross-document     a selection spanning documents is inspect/copy only;
//   index-unavailable  the external index is not current, so external
//                      references are unknown and deletion is refused (an
//                      index that is not current never proves anything);
//   referenced         the current index names external references, exactly
//                      what the service guard enforces (for a location, its
//                      map-internal references refuse as well);
//   unavailable        nothing refuses; the page sends the kind's delete
//                      command, or explains that this kind has none.
// Map-internal incoming relations are listed alongside as references that a
// deletion would leave dangling; they never cascade.

export const INDEX_UNAVAILABLE = "index-unavailable";
export const REFERENCED = "referenced";
export const CROSS_DOCUMENT = "cross-document";
export const UNAVAILABLE = "unavailable";

// `internalBlocks`: the selected kind's map-internal incoming references
// also refuse its deletion (a location named by a settlement, an anchor or a
// landmark), exactly as the service's internal guard does.
export function deletionRefusal({ externalStatus, summary, relations = [], internalBlocks = false }) {
  const external = relations.filter((row) => row.external);
  const internal = relations.filter((row) => !row.external);
  if (summary?.crossDocument) {
    return { key: CROSS_DOCUMENT, external: [], internal: [], reasons: [], count: 0 };
  }
  if (internalBlocks && internal.length) {
    return { key: REFERENCED, external, internal, reasons: [], count: external.length + internal.length, internalBlocks: true };
  }
  if (!externalStatus?.current) {
    return {
      key: INDEX_UNAVAILABLE,
      external: [],
      internal,
      reasons: [...(externalStatus?.reasons ?? [])],
      count: 0,
    };
  }
  if (external.length) {
    return { key: REFERENCED, external, internal, reasons: [], count: external.length };
  }
  return { key: UNAVAILABLE, external: [], internal, reasons: [], count: 0 };
}
