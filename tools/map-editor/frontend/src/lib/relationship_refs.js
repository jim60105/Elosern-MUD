// Editor-local references of the entrance relationships (no imports, so the
// settlement and interior helpers can link their rows to them).

export const gateRef = (settlementId, direction) => `gate:${settlementId}:${direction}`;
export const cityGateRef = (settlementId) => `city_gate:${settlementId}`;
export const exteriorRef = (interiorId) => `exterior:${interiorId}`;
// The label is free text: percent-encoding keeps `:`, `>` and `/` out of the
// structure, so the link identity round-trips exactly.
export const linkRef = (interiorId, link) =>
  `interior_link:${interiorId}:${link.source_room}>${link.target_interior}:${link.target_room}/${encodeURIComponent(link.label)}`;
