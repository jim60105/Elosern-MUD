// Drawable scenes built from the service's core-derived projection.
//
// Every coordinate here comes from the service (core cell centres, local
// metres, world metres, road lengths); this module only arranges them into
// shapes, marks and links for one map. It never re-derives a map rule, never
// fabricates a metric coordinate for a coordinate-free interior, and never
// turns an authored identifier into a URL.

import { boundsOfPoints, UNITS } from "@elosern/map-view";
import { storedPosition, toScene } from "./layout_edit.js";
import {
  FOREST,
  KM as CONTINENT_KM,
  MAINLAND,
  RIDGE,
  cellMetres,
  districtRef,
  featurePoints,
  footprintRef,
  fordFeatureRef,
  parseContinentRef,
  passRef,
  pointRef,
  regionRef,
  siteRef,
  waterwayRef,
} from "./continent.js";

import { bendRef, parseSettlementRef, roadLabel, roadRef } from "./settlement.js";

export { INTERIOR_COLUMNS } from "./layout_edit.js";

const KM = CONTINENT_KM;

function point([x, y]) {
  return { x, y };
}

// The continent: authored inputs (selectable features, draggable points)
// distinguished from derived output (the core's terrain preview raster, ridge
// walls and national borders; never selectable, never handled). Control-point
// diamonds appear only for the selected feature or the feature of the
// selected point. `items` is the object list: features, then marks.
export function continentScene(world, selection = []) {
  const continent = world.continent;
  const preview = continent.terrain_preview?.status === "current" ? continent.terrain_preview : null;
  const cell = cellMetres(world);
  const centre = ([x, y]) => ({ x: (x + 0.5) * cell, y: (y + 0.5) * cell });
  const chosen = new Set(selection);
  const active = new Set(
    selection.map((ref) => parseContinentRef(ref)?.feature).filter(Boolean),
  );
  const boundary = continent.mainland_boundary_km.map(([east, north]) => ({ x: east * KM, y: north * KM }));
  const feature = (id, ref, role, type, points, label, layer) => ({
    id, ref, role, type, points, label, layer, selectable: true, selected: chosen.has(ref) || active.has(ref),
  });
  const shapes = [
    feature("mainland", MAINLAND, "land", "polygon", boundary, "大陸海岸線", "terrain"),
    ...continent.waterways.map((waterway) =>
      feature(
        `waterway:${waterway.id}`,
        waterwayRef(waterway.id),
        waterway.id === continent.border_river_key ? "water water--border" : "water",
        "polyline",
        waterway.route_m.map(point),
        waterway.id,
        "water",
      ),
    ),
    feature("forest-edge", FOREST, "forest", "polyline", continent.forest_edge_m.map(point), "北部林線", "terrain"),
    ...(preview?.ridge_walls ?? []).map((wall, index) => ({
      id: `ridge-wall:${index}`,
      ref: RIDGE,
      role: "ridge",
      type: "polyline",
      points: wall.map(centre),
      label: "中央山脊",
      layer: "ridge",
      selectable: true,
      selected: chosen.has(RIDGE),
    })),
    ...(preview?.national_borders ?? []).map((border, index) => ({
      id: `border:${index}`,
      ref: null,
      role: "border",
      type: "polyline",
      points: border.points.map(centre),
      label: border.nation_keys.join(" / "),
      layer: "partition",
      selectable: false,
      derived: true,
    })),
    ...world.settlements.flatMap((settlement) =>
      (settlement.footprint?.cells ?? []).map(([x, y]) => ({
        id: `footprint-cell:${settlement.id}:${x}:${y}`,
        ref: footprintRef(settlement.id),
        role: "footprint",
        type: "polygon",
        points: [
          { x: x * cell, y: y * cell },
          { x: (x + 1) * cell, y: y * cell },
          { x: (x + 1) * cell, y: (y + 1) * cell },
          { x: x * cell, y: (y + 1) * cell },
        ],
        label: `${settlement.id} 佔地`,
        layer: "footprint",
        selectable: true,
        selected: chosen.has(footprintRef(settlement.id)),
      })),
    ),
  ];
  const marks = [
    ...world.locations.map((location) => ({
      id: location.qualified_ref,
      kind: "location",
      label: location.display_name_zh,
      role: location.local_maps.length ? "location" : "location-bare",
      layer: "locations",
      draggable: true,
      ...point(location.centre_m),
    })),
    ...(continent.harbor_sites ?? []).map((site) => ({
      id: siteRef(site.id),
      kind: "site",
      label: site.display_name,
      role: "site",
      layer: "locations",
      draggable: true,
      ...point(site.centre_m),
    })),
    ...continent.waterways.flatMap((waterway) =>
      (waterway.fords_m ?? []).map((ford, index) => ({
        id: pointRef(fordFeatureRef(waterway.id), index),
        kind: "ford",
        label: `${waterway.id} · 渡口 ${index + 1}`,
        role: "ford",
        layer: "ridge",
        draggable: true,
        ...point(ford),
      })),
    ),
    ...(preview?.passes ?? []).map((pass) => ({
      id: passRef(pass.index),
      kind: "pass",
      label: `隘口 ${pass.index + 1}（${pass.y_min}–${pass.y_max}）`,
      role: "pass",
      layer: "ridge",
      draggable: false,
      ...centre(pass.centre),
    })),
  ];
  const featureLayers = { mainland: "terrain", forest_edge: "terrain", waterway: "water" };
  for (const featureRef of active) {
    const parsed = parseContinentRef(featureRef);
    if (parsed.kind === "ford") continue; // fords are their own point marks
    featurePoints(world, featureRef).forEach((entry, index) => {
      marks.push({
        id: pointRef(featureRef, index),
        kind: "handle",
        label: `${featureLabel(featureRef)} · 控制點 ${index + 1}`,
        role: "handle",
        layer: featureLayers[parsed.kind],
        draggable: true,
        ...entry.m,
      });
    });
  }
  const listed = [
    { id: MAINLAND, label: "大陸海岸線", layer: "terrain" },
    { id: FOREST, label: "北部林線", layer: "terrain" },
    ...continent.waterways.map((waterway) => ({ id: waterwayRef(waterway.id), label: `水系 ${waterway.id}`, layer: "water" })),
    { id: RIDGE, label: "中央山脊", layer: "ridge" },
    ...(continent.regions ?? []).map((region) => ({ id: regionRef(region.id), label: `地形區 ${region.display_name_zh}`, layer: "terrain" })),
    ...(world.districts ?? []).map((district) => ({ id: districtRef(district.id), label: `分區 ${district.district_name_zh}`, layer: "partition" })),
    ...world.settlements
      .filter((settlement) => settlement.footprint)
      .map((settlement) => ({ id: footprintRef(settlement.id), label: `${settlement.id} 佔地`, layer: "footprint" })),
  ];
  const items = [...listed, ...marks.map((mark) => ({ id: mark.id, label: mark.label, layer: mark.layer }))];
  const frame = continent.frame_cells * cell;
  const raster = preview
    ? { preview, west: 0, south: 0, east: preview.columns * preview.step * cell, north: preview.rows * preview.step * cell, layer: "terrain" }
    : null;
  const bounds = boundsOfPoints([...boundary, { x: 0, y: 0 }, { x: frame, y: frame }]);
  return { kind: "continent", unit: UNITS.m, bounds, shapes, marks, links: [], items, raster };
}

export function featureLabel(featureRef) {
  const parsed = parseContinentRef(featureRef);
  if (!parsed) return featureRef;
  if (parsed.kind === "mainland") return "大陸海岸線";
  if (parsed.kind === "forest_edge") return "北部林線";
  if (parsed.kind === "ford") return `${parsed.id} 渡口`;
  return parsed.id;
}

// A settlement: node marks (draggable), directed roads (selectable links
// through their authored bends) and, for the selected road or bend, the bend
// diamonds and the road's direction chevron. `items` is the object list:
// nodes, then roads. An empty new map draws nothing and fabricates nothing.
export function settlementScene(settlement, selection = []) {
  const nodes = new Map(settlement.nodes.map((node) => [node.id, node]));
  const gates = new Set();
  if (settlement.city_gate) gates.add(settlement.city_gate.node);
  for (const gate of settlement.wilderness_entry?.gates ?? []) gates.add(gate.destination_node);
  const chosen = new Set(selection);
  const activeRoads = new Set(
    selection
      .map(parseSettlementRef)
      .filter((parsed) => parsed && parsed.settlementId === settlement.id && parsed.kind !== "node")
      .map((parsed) => parsed.road),
  );
  const marks = settlement.nodes.map((node) => ({
    id: node.qualified_ref,
    kind: "node",
    label: node.key,
    role: gates.has(node.id) ? "gate" : "node",
    gateway: gates.has(node.id),
    draggable: true,
    ...point(node.local_m),
  }));
  const pairs = new Set(settlement.roads.map((road) => `${road.source}>${road.destination}`));
  const links = settlement.roads
    .filter((road) => nodes.has(road.source) && nodes.has(road.destination))
    .map((road) => {
      const ref = roadRef(settlement.id, road.source, road.destination);
      const points = [nodes.get(road.source).local_m, ...road.bends, nodes.get(road.destination).local_m].map(point);
      return {
        id: `road:${settlement.id}:${road.id}`,
        ref,
        kind: "road",
        direction: road.direction,
        lengthM: road.length_m,
        twoWay: pairs.has(`${road.destination}>${road.source}`),
        selected: activeRoads.has(ref),
        points,
      };
    });
  for (const link of links) {
    if (!link.selected) continue;
    const road = settlement.roads.find((item) => roadRef(settlement.id, item.source, item.destination) === link.ref);
    road.bends.forEach((bend, index) => {
      marks.push({
        id: bendRef(link.ref, index),
        kind: "handle",
        label: `${roadLabel(settlement, road)} · 彎點 ${index + 1}`,
        role: "handle",
        draggable: true,
        selected: chosen.has(bendRef(link.ref, index)),
        ...point(bend),
      });
    });
  }
  const items = [
    ...settlement.nodes.map((node) => ({ id: node.qualified_ref, label: node.key })),
    ...settlement.roads.map((road) => ({ id: roadRef(settlement.id, road.source, road.destination), label: `道路 ${roadLabel(settlement, road)}` })),
  ];
  const drawn = [...marks, ...links.flatMap((link) => link.points)];
  const bounds = boundsOfPoints(drawn.length ? drawn : [{ x: 0, y: 0 }]);
  return { kind: "settlement", unit: UNITS.m, bounds, shapes: [], marks, links, items };
}

// Interior rooms carry no coordinates: an editor layout position is used when
// one exists, otherwise a deterministic list order. Neither is a distance.
export function interiorPositions(interior) {
  const positions = new Map();
  for (const room of interior.rooms) positions.set(room.id, toScene(storedPosition(interior, room.id)));
  return positions;
}

export function interiorScene(interior) {
  const positions = interiorPositions(interior);
  const marks = interior.rooms.map((room) => ({
    id: room.qualified_ref,
    kind: "room",
    label: room.name_zh,
    detail: room.id,
    role: "room",
    draggable: true,
    ...positions.get(room.id),
  }));
  const pairs = new Set(interior.connections.map((c) => `${c.source}>${c.destination}`));
  const links = interior.connections
    .filter((connection) => positions.has(connection.source) && positions.has(connection.destination))
    .map((connection) => ({
      id: `connection:${interior.id}:${connection.source}>${connection.destination}`,
      kind: "connection",
      label: connection.label,
      twoWay: pairs.has(`${connection.destination}>${connection.source}`),
      points: [positions.get(connection.source), positions.get(connection.destination)],
    }));
  const bounds = boundsOfPoints(marks.length ? marks : [{ x: 0, y: 0 }]);
  return { kind: "interior", unit: null, bounds, shapes: [], marks, links };
}

export function sceneFor(world, domain, mapId, selection = []) {
  if (!world) return null;
  if (domain === "continent") return continentScene(world, selection);
  if (domain === "settlement") {
    const settlement = world.settlements.find((item) => item.id === mapId);
    return settlement ? settlementScene(settlement, selection) : null;
  }
  const interior = world.interiors.find((item) => item.id === mapId);
  return interior ? interiorScene(interior) : null;
}
