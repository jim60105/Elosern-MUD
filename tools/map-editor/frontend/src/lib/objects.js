// One catalog of every selectable map object in the displayed snapshot,
// keyed by its qualified reference. Each entry names its domain, the map it
// is drawn on, its owning source document and a parent label for
// disambiguation. Values are plain strings for text interpolation only; the
// catalog never derives geometry or a map rule.

import {
  FOREST,
  MAINLAND,
  RIDGE,
  companionText,
  districtRef,
  featurePoints,
  footprintRef,
  fordFeatureRef,
  frameOf,
  passRef,
  pointRef,
  regionRef,
  siteRef,
  waterwayRef,
} from "./continent.js";

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
  continentEntries(world, catalog);
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

// Continental features, control points, ridge passes, sites, regions,
// districts and footprints: editor-local references (not qualified map
// objects), each naming its owning document, layer and stored frame.
function continentEntries(world, catalog) {
  const continent = world.continent;
  if (!continent) return;
  const path = continent.relative_path;
  const add = (ref, kind, label, layer, frame, relativePath = path) =>
    catalog.set(ref, {
      ref, kind, domain: "continent", mapId: null, id: ref, label, parentLabel: "大陸", relativePath, layer, frame,
    });
  const points = (featureRef, label, layer) => {
    featurePoints(world, featureRef).forEach((entry, index) => {
      const ref = pointRef(featureRef, index);
      const frame = `座標：${entry.stored[0]}, ${entry.stored[1]}（${frameOf(ref)}）；${companionText(world, ref, entry.stored)}`;
      add(ref, "point", `${label} · ${featureRef.startsWith("continent:ford:") ? "渡口" : "控制點"} ${index + 1}`, layer, frame);
    });
  };
  add(MAINLAND, "feature", "大陸海岸線", "terrain", "大陸海岸線頂點：km 地理");
  points(MAINLAND, "大陸海岸線", "terrain");
  add(FOREST, "feature", "北部林線", "terrain", "林線控制點：1 km 格");
  points(FOREST, "北部林線", "terrain");
  for (const waterway of continent.waterways ?? []) {
    add(waterwayRef(waterway.id), "feature", `水系 ${waterway.id}`, "water", "水系控制點：1 km 格");
    points(waterwayRef(waterway.id), waterway.id, "water");
    points(fordFeatureRef(waterway.id), waterway.id, "ridge");
  }
  add(RIDGE, "ridge", "中央山脊", "ridge", "山脊參數：1 km 格（欄／列索引與格數）");
  for (const pass of continent.terrain_preview?.passes ?? []) {
    add(passRef(pass.index), "pass", `隘口 ${pass.index + 1}`, "ridge", `列 ${pass.y_min}–${pass.y_max}（1 km 格）`);
  }
  for (const site of continent.harbor_sites ?? []) {
    add(siteRef(site.id), "site", site.display_name, "locations", `座標：格 (${site.cell[0]}, ${site.cell[1]})（1 km 格）`);
  }
  for (const region of continent.regions ?? []) {
    add(regionRef(region.id), "region", region.display_name_zh, "terrain", "地形區（分類輸出，無座標）");
  }
  for (const district of world.districts ?? []) {
    add(districtRef(district.id), "district", district.district_name_zh, "partition", "分區宣告（地標為穩定參照）", district.relative_path);
  }
  for (const settlement of world.settlements ?? []) {
    if (!settlement.footprint) continue;
    const [x, y] = settlement.footprint.origin;
    add(footprintRef(settlement.id), "footprint", `${settlement.id} 佔地`, "footprint",
      `佔地遮罩原點 格 (${x}, ${y})（1 km 格）`, settlement.relative_path);
  }
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
