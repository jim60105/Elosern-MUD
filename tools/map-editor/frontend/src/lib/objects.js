// One catalog of every selectable map object in the displayed snapshot,
// keyed by its qualified reference. Each entry names its domain, the map it
// is drawn on, its owning source document and a parent label for
// disambiguation. Values are plain strings for text interpolation only; the
// catalog never derives geometry or a map rule.

export const DOMAIN_LABELS = Object.freeze({ continent: "大陸", settlement: "據點", interior: "室內" });

export function objectCatalog(world) {
  const catalog = new Map();
  if (!world) return catalog;
  const locations = new Map(world.locations.map((location) => [location.id, location]));
  const settlements = new Map(world.settlements.map((settlement) => [settlement.id, settlement]));
  for (const location of world.locations) {
    catalog.set(location.qualified_ref, {
      ref: location.qualified_ref,
      kind: "location",
      domain: "continent",
      mapId: null,
      id: location.id,
      label: location.display_name_zh,
      parentLabel: "大陸",
      relativePath: location.relative_path,
      layer: "locations",
    });
  }
  for (const settlement of world.settlements) {
    const parent = locations.get(settlement.location_ref)?.display_name_zh ?? settlement.location_ref;
    for (const node of settlement.nodes) {
      catalog.set(node.qualified_ref, {
        ref: node.qualified_ref,
        kind: "node",
        domain: "settlement",
        mapId: settlement.id,
        id: node.id,
        label: node.key,
        parentLabel: `${parent} › ${settlement.id}`,
        relativePath: settlement.relative_path,
        layer: null,
      });
    }
  }
  for (const interior of world.interiors) {
    const settlement = interior.exterior ? settlements.get(interior.exterior.settlement) : null;
    const town = settlement ? locations.get(settlement.location_ref)?.display_name_zh ?? settlement.id : null;
    const parent = town ? `${town} › ${interior.id}` : interior.id;
    for (const room of interior.rooms) {
      catalog.set(room.qualified_ref, {
        ref: room.qualified_ref,
        kind: "room",
        domain: "interior",
        mapId: interior.id,
        id: room.id,
        label: room.name_zh,
        parentLabel: parent,
        relativePath: interior.relative_path,
        layer: null,
      });
    }
  }
  return catalog;
}

// The map a reference is shown on, also for map-level references.
export function locate(catalog, ref) {
  const entry = catalog.get(ref);
  if (entry) return { domain: entry.domain, mapId: entry.mapId, ref };
  const settlement = /^settlement:([^:]+)$/.exec(ref ?? "");
  if (settlement) return { domain: "settlement", mapId: settlement[1], ref: null };
  const interior = /^interior:([^:]+)$/.exec(ref ?? "");
  if (interior) return { domain: "interior", mapId: interior[1], ref: null };
  return null;
}
