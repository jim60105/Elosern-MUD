// Navigation tree and inspection records over the service projection.
//
// Records name their owning source document and qualified identity; every
// value stays a plain string or number for text interpolation. Nothing here
// builds markup or a URL from authored content.

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
  const outgoing = settlement.roads.filter((road) => road.source === node.id);
  const incoming = settlement.roads.filter((road) => road.destination === node.id);
  return {
    title: node.key,
    qualifiedRef: node.qualified_ref,
    relativePath: settlement.relative_path,
    fields: [
      row("原型", node.prototype_parent),
      row("位置", `${node.local_m[0]} m 東, ${node.local_m[1]} m 北（地方）`),
      row("世界座標", `${node.world_m[0]} m 東, ${node.world_m[1]} m 北`),
      row("場景", node.scene_archetype),
      row("描述", node.desc),
      ...outgoing.map((road) =>
        row("道路", `${road.direction} → ${road.destination}${road.length_m === null ? "" : ` · ${Math.round(road.length_m)} m`}`),
      ),
      ...incoming.map((road) => row("來路", `← ${road.direction} 來自 ${road.source}`)),
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
      ...interior.connections
        .filter((connection) => connection.source === room.id)
        .map((connection) => row("連接", `${connection.label} → ${connection.destination}`)),
    ],
  };
}

export function inspect(world, qualifiedRef) {
  if (!world || !qualifiedRef) return null;
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
