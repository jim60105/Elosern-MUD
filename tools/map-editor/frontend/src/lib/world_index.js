// Navigation tree and inspection records over the service projection.
//
// Records name their owning source document and qualified identity; every
// value stays a plain string or number for text interpolation. Nothing here
// builds markup or a URL from authored content.

import { companionText, featurePoints, frameOf, parseContinentRef } from "./continent.js";
import { featureLabel } from "./map_scene.js";
import { compassLabel, findRoad, findSettlement, nodeName, parseSettlementRef, roadLabel } from "./settlement.js";

export function worldTree(world) {
  if (!world) return [];
  const settlements = new Map(world.settlements.map((s) => [s.id, s]));
  return [
    {
      id: "continent",
      domain: "continent",
      label: "大陸",
      relativePath: world.continent.relative_path,
      children: world.locations.map((location) => ({
        id: location.qualified_ref,
        domain: "continent",
        label: location.display_name_zh,
        tag: location.local_maps.length ? null : "無本地圖",
        children: location.local_maps
          .filter((mapId) => settlements.has(mapId))
          .map((mapId) => {
            const settlement = settlements.get(mapId);
            return {
              id: `settlement:${mapId}`,
              domain: "settlement",
              mapId,
              label: mapId,
              tag: "據點",
              children: settlement.interiors.map((interiorId) => ({
                id: `interior:${interiorId}`,
                domain: "interior",
                mapId: interiorId,
                label: interiorId,
                tag: "室內",
                children: [],
              })),
            };
          }),
      })),
    },
  ];
}

const row = (label, value) => ({ label, value: value === null || value === undefined ? "—" : String(value) });

function locationRecord(world, location) {
  return {
    title: location.display_name_zh,
    qualifiedRef: location.qualified_ref,
    relativePath: location.relative_path,
    fields: [
      row("種類", location.kind),
      row("格", `${location.cell[0]}, ${location.cell[1]}（1 km 格）`),
      row("中心", `${location.centre_m[0]} m 東, ${location.centre_m[1]} m 北（地理）`),
      row("本地圖", location.local_maps.length ? location.local_maps.join("、") : "無本地圖"),
      row("場景", location.scene_archetype),
      row("描述", location.description),
    ],
  };
}

function nodeRecord(settlement, node) {
  return {
    title: node.key,
    qualifiedRef: node.qualified_ref,
    relativePath: settlement.relative_path,
    fields: [
      row("ID", node.id),
      row("原型", node.prototype_parent),
      row("錨點地點", node.anchor_key),
      row("位置", `${node.local_m[0]} m 東, ${node.local_m[1]} m 北（地方）`),
      row("世界座標", `${node.world_m[0]} m 東, ${node.world_m[1]} m 北`),
      row("場景", node.scene_archetype),
      row("描述", node.desc),
    ],
  };
}

function roomRecord(interior, room) {
  return {
    title: room.name_zh,
    qualifiedRef: room.qualified_ref,
    relativePath: interior.relative_path,
    fields: [
      row("場景", room.scene_archetype),
      row("美術", room.art_key),
      row("描述", room.desc_zh),
      row("版面", interior.layout_relative_path ?? "無版面文件（依清單排列）"),
    ],
  };
}

// Continental features, points and declarations (editable fields are the
// continent inspector's; these rows are read-only context).
function continentRecord(world, ref) {
  const parsed = parseContinentRef(ref);
  const continent = world.continent;
  if (!parsed || !continent) return null;
  const path = continent.relative_path;
  const base = (title, fields, relativePath = path, extra = {}) => ({ title, qualifiedRef: ref, relativePath, fields, ...extra });
  if (parsed.feature) {
    const points = featurePoints(world, parsed.feature);
    if (parsed.index !== null) {
      const entry = points[parsed.index];
      if (!entry) return null;
      const noun = parsed.kind === "ford" ? "渡口" : "控制點";
      return base(`${featureLabel(parsed.feature)} · ${noun} ${parsed.index + 1}`, [
        row("座標", `${entry.stored[0]}, ${entry.stored[1]}（${frameOf(ref)}）`),
        row("對應", companionText(world, ref, entry.stored)),
      ], path, { owner: parsed.kind === "ford" ? `continent:waterway:${parsed.id}` : parsed.feature, ownerLabel: featureLabel(parsed.feature), pointCount: points.length });
    }
    if (parsed.kind === "waterway" && !continent.waterways.some((item) => item.id === parsed.id)) return null;
    const fields = [row("控制點", `${points.length} 個（${frameOf(ref)}）`)];
    if (parsed.kind === "waterway") {
      const waterway = continent.waterways.find((item) => item.id === parsed.id);
      fields.push(row("渡口", `${waterway.fords.length} 個`), row("國界河", waterway.id === continent.border_river_key ? "是" : "否"));
    }
    return base(featureLabel(parsed.feature), fields);
  }
  if (parsed.kind === "ridge") {
    return base("中央山脊", [row("隘口", `${continent.ridge?.passes?.length ?? 0} 個`), row("單位", "欄／列索引與格數（1 km 格）")]);
  }
  if (parsed.kind === "pass") {
    const pass = continent.ridge?.passes?.[parsed.index];
    if (!pass) return null;
    return base(`隘口 ${parsed.index + 1}`, [row("列範圍", `${pass.y_min}–${pass.y_max}（1 km 格）`)]);
  }
  if (parsed.kind === "site") {
    const site = (continent.harbor_sites ?? []).find((item) => item.id === parsed.id);
    if (!site) return null;
    return base(site.display_name, [
      row("格", `${site.cell[0]}, ${site.cell[1]}（1 km 格）`),
      row("中心", `${site.centre_m[0]} m 東, ${site.centre_m[1]} m 北（地理）`),
    ]);
  }
  if (parsed.kind === "region") {
    const region = (continent.regions ?? []).find((item) => item.id === parsed.id);
    if (!region) return null;
    return base(region.display_name_zh, [row("鍵", region.id), row("說明", "分類由核心依地形輸入推導，無可編輯座標")]);
  }
  if (parsed.kind === "district") {
    const district = (world.districts ?? []).find((item) => item.id === parsed.id);
    if (!district) return null;
    return base(district.district_name_zh, [row("種類", district.kind), row("地形區", district.region_key)], district.relative_path);
  }
  if (parsed.kind === "footprint") {
    const settlement = world.settlements.find((item) => item.id === parsed.id);
    if (!settlement?.footprint) return null;
    return base(`${settlement.id} 佔地`, [
      row("原點", `${settlement.footprint.origin[0]}, ${settlement.footprint.origin[1]}（1 km 格）`),
      row("佔地格", `${settlement.footprint.cells.length} 格`),
    ], settlement.relative_path);
  }
  return null;
}

// A directed road or one of its bends (editable fields are the settlement
// inspector's; these rows are read-only context, the length is the core's).
function roadRecord(world, ref) {
  const parsed = parseSettlementRef(ref);
  if (!parsed || parsed.kind === "node") return null;
  const settlement = findSettlement(world, parsed.settlementId);
  const road = findRoad(settlement, parsed.source, parsed.destination);
  if (!road) return null;
  const length = road.length_m === null || road.length_m === undefined ? "—" : `${road.length_m} m（核心計算的物理長度）`;
  if (parsed.kind === "bend") {
    const bend = road.bends[parsed.index];
    if (!bend) return null;
    return {
      title: `${roadLabel(settlement, road)} · 彎點 ${parsed.index + 1}`,
      qualifiedRef: ref,
      relativePath: settlement.relative_path,
      fields: [row("座標", `${bend[0]} m 東, ${bend[1]} m 北（地方）`), row("道路長度", length)],
    };
  }
  return {
    title: roadLabel(settlement, road),
    qualifiedRef: ref,
    relativePath: settlement.relative_path,
    fields: [
      row("起點", `${nodeName(settlement, road.source)}（${road.source}）`),
      row("終點", `${nodeName(settlement, road.destination)}（${road.destination}）`),
      row("方向", `${compassLabel(road.direction)}（${road.direction}）`),
      row("長度", length),
      row("彎點", `${road.bends.length} 個`),
    ],
  };
}

export function inspect(world, qualifiedRef) {
  if (!world || !qualifiedRef) return null;
  const continental = continentRecord(world, qualifiedRef);
  if (continental) return continental;
  const road = roadRecord(world, qualifiedRef);
  if (road) return road;
  for (const location of world.locations) {
    if (location.qualified_ref === qualifiedRef) return locationRecord(world, location);
  }
  for (const settlement of world.settlements) {
    for (const node of settlement.nodes) {
      if (node.qualified_ref === qualifiedRef) return nodeRecord(settlement, node);
    }
  }
  for (const interior of world.interiors) {
    for (const room of interior.rooms) {
      if (room.qualified_ref === qualifiedRef) return roomRecord(interior, room);
    }
  }
  return null;
}

export function mapTitle(world, domain, mapId) {
  if (!world) return "";
  if (domain === "continent") return "大陸";
  if (domain === "settlement") {
    const settlement = world.settlements.find((s) => s.id === mapId);
    const location = settlement && world.locations.find((l) => l.id === settlement.location_ref);
    return location ? `${location.display_name_zh} › ${mapId}` : mapId ?? "";
  }
  return mapId ?? "";
}

export function sourcePathFor(world, domain, mapId) {
  if (!world) return null;
  if (domain === "continent") return world.continent.relative_path;
  const list = domain === "settlement" ? world.settlements : world.interiors;
  return list.find((item) => item.id === mapId)?.relative_path ?? null;
}
