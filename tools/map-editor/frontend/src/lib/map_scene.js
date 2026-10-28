// Drawable scenes built from the service's core-derived projection.
//
// Every coordinate here comes from the service (core cell centres, local
// metres, world metres, road lengths); this module only arranges them into
// shapes, marks and links for one map. It never re-derives a map rule, never
// fabricates a metric coordinate for a coordinate-free interior, and never
// turns an authored identifier into a URL.

import { boundsOfPoints, UNITS } from "@elosern/map-view";
import { storedPosition, toScene } from "./layout_edit.js";

export { INTERIOR_COLUMNS } from "./layout_edit.js";

const KM = 1000;

function point([x, y]) {
  return { x, y };
}

export function continentScene(world) {
  const continent = world.continent;
  const boundary = continent.mainland_boundary_km.map(([east, north]) => ({ x: east * KM, y: north * KM }));
  const shapes = [
    { id: "mainland", role: "land", type: "polygon", points: boundary },
    ...continent.waterways.map((waterway) => ({
      id: `waterway:${waterway.id}`,
      role: "water",
      type: "polyline",
      points: waterway.route_m.map(point),
    })),
    {
      id: "forest-edge",
      role: "forest",
      type: "polyline",
      points: continent.forest_edge_m.map(point),
    },
  ];
  const marks = world.locations.map((location) => ({
    id: location.qualified_ref,
    kind: "location",
    label: location.display_name_zh,
    role: location.local_maps.length ? "location" : "location-bare",
    ...point(location.centre_m),
  }));
  const frame = continent.frame_cells * continent.cell_size_km * KM;
  const bounds = boundsOfPoints([...boundary, { x: 0, y: 0 }, { x: frame, y: frame }]);
  return { kind: "continent", unit: UNITS.m, bounds, shapes, marks, links: [] };
}

export function settlementScene(settlement) {
  const nodes = new Map(settlement.nodes.map((node) => [node.id, node]));
  const gates = new Set();
  if (settlement.city_gate) gates.add(settlement.city_gate.node);
  for (const gate of settlement.wilderness_entry?.gates ?? []) gates.add(gate.destination_node);
  const marks = settlement.nodes.map((node) => ({
    id: node.qualified_ref,
    kind: "node",
    label: node.key,
    role: gates.has(node.id) ? "gate" : "node",
    gateway: gates.has(node.id),
    ...point(node.local_m),
  }));
  const pairs = new Set(settlement.roads.map((road) => `${road.source}>${road.destination}`));
  const links = settlement.roads.map((road) => {
    const from = nodes.get(road.source);
    const to = nodes.get(road.destination);
    return {
      id: `road:${settlement.id}:${road.id}`,
      kind: "road",
      direction: road.direction,
      lengthM: road.length_m,
      twoWay: pairs.has(`${road.destination}>${road.source}`),
      points: [from.local_m, ...road.bends, to.local_m].map(point),
    };
  });
  const bounds = boundsOfPoints([...marks, ...links.flatMap((link) => link.points)]);
  return { kind: "settlement", unit: UNITS.m, bounds, shapes: [], marks, links };
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

export function sceneFor(world, domain, mapId) {
  if (!world) return null;
  if (domain === "continent") return continentScene(world);
  if (domain === "settlement") {
    const settlement = world.settlements.find((item) => item.id === mapId);
    return settlement ? settlementScene(settlement) : null;
  }
  const interior = world.interiors.find((item) => item.id === mapId);
  return interior ? interiorScene(interior) : null;
}
