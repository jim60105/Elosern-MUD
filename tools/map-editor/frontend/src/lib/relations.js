// Directed relationships of one map object, read from authored projection
// fields only (roads, connections, entrances, links, gates, landmarks, local
// maps and anchors) plus the external incoming references the service looked
// up in the reference index. Nothing is derived: no reachability, length or
// geometry is computed here. Each row names the document that declares it.
//
// Row: { kind, label, ref (navigable qualified or map reference, or null),
//        source (workspace-relative declaring document), external }

function roomName(interior, roomId) {
  return interior.rooms.find((room) => room.id === roomId)?.name_zh ?? roomId;
}

function nodeKey(settlement, nodeId) {
  return settlement?.nodes.find((node) => node.id === nodeId)?.key ?? nodeId;
}

function landmarkRows(world, matches) {
  const rows = [];
  for (const district of world.districts ?? []) {
    const landmark = district.landmark ?? {};
    if (matches(landmark)) {
      rows.push({
        kind: "地標",
        label: `${district.district_name_zh}（${district.id}）`,
        ref: null,
        source: district.relative_path,
        external: false,
      });
    }
  }
  return rows;
}

function externalRows(incoming, ref) {
  return (incoming?.[ref] ?? []).map((item) => ({
    kind: "外部",
    label: `${item.source}（${item.source_domain}）`,
    ref: null,
    source: item.source_file,
    external: true,
  }));
}

function nodeRelations(world, settlement, node) {
  const ref = (id) => `settlement_node:${settlement.id}:${id}`;
  const path = settlement.relative_path;
  const outgoing = settlement.roads
    .filter((road) => road.source === node.id)
    .map((road) => ({
      kind: "道路",
      label: `${road.direction} → ${nodeKey(settlement, road.destination)}${road.length_m === null ? "" : ` · ${Math.round(road.length_m)} m`}`,
      ref: ref(road.destination),
      source: path,
      external: false,
    }));
  const incoming = settlement.roads
    .filter((road) => road.destination === node.id)
    .map((road) => ({
      kind: "道路",
      label: `← ${road.direction} 來自 ${nodeKey(settlement, road.source)}`,
      ref: ref(road.source),
      source: path,
      external: false,
    }));
  for (const interior of world.interiors) {
    const exterior = interior.exterior;
    if (exterior?.settlement === settlement.id && exterior.node === node.id) {
      incoming.push({
        kind: "入口",
        label: `⌂ ${interior.id} · ${roomName(interior, exterior.room)} ⇄ ${node.key}`,
        ref: `interior_room:${interior.id}:${exterior.room}`,
        source: interior.relative_path,
        external: false,
      });
    }
  }
  if (settlement.city_gate?.node === node.id) {
    incoming.push({ kind: "城門", label: settlement.city_gate.exit_key ?? node.key, ref: null, source: path, external: false });
  }
  for (const gate of settlement.wilderness_entry?.gates ?? []) {
    if (gate.destination_node === node.id) {
      incoming.push({ kind: "野外入口", label: `${gate.return_direction} → ${node.key}`, ref: null, source: path, external: false });
    }
  }
  incoming.push(
    ...landmarkRows(world, (l) => l.domain === "settlement_node" && l.map_id === settlement.id && l.object_id === node.id),
  );
  return { outgoing, incoming };
}

function roomRelations(world, interior, room) {
  const ref = (id) => `interior_room:${interior.id}:${id}`;
  const path = interior.relative_path;
  const outgoing = interior.connections
    .filter((connection) => connection.source === room.id)
    .map((connection) => ({
      kind: "連接",
      label: `${connection.label} → ${roomName(interior, connection.destination)}`,
      ref: ref(connection.destination),
      source: path,
      external: false,
    }));
  const incoming = interior.connections
    .filter((connection) => connection.destination === room.id)
    .map((connection) => ({
      kind: "連接",
      label: `← ${connection.label} 來自 ${roomName(interior, connection.source)}`,
      ref: ref(connection.source),
      source: path,
      external: false,
    }));
  const exterior = interior.exterior;
  if (exterior && exterior.room === room.id) {
    const settlement = world.settlements.find((item) => item.id === exterior.settlement);
    outgoing.push({
      kind: "入口",
      label: `⌂ ${nodeKey(settlement, exterior.node)}（${exterior.settlement}）⇄ ${room.name_zh}`,
      ref: `settlement_node:${exterior.settlement}:${exterior.node}`,
      source: path,
      external: false,
    });
  }
  for (const link of interior.interior_links ?? []) {
    if (link.source_room === room.id) {
      outgoing.push({
        kind: "室內連結",
        label: `${link.label ?? ""} → ${link.target_interior} · ${link.target_room}`.trim(),
        ref: `interior_room:${link.target_interior}:${link.target_room}`,
        source: path,
        external: false,
      });
    }
  }
  for (const other of world.interiors) {
    for (const link of other.interior_links ?? []) {
      if (link.target_interior === interior.id && link.target_room === room.id) {
        incoming.push({
          kind: "室內連結",
          label: `← ${link.label ?? ""} 來自 ${other.id} · ${roomName(other, link.source_room)}`,
          ref: `interior_room:${other.id}:${link.source_room}`,
          source: other.relative_path,
          external: false,
        });
      }
    }
  }
  incoming.push(
    ...landmarkRows(world, (l) => l.domain === "interior_room" && l.map_id === interior.id && l.object_id === room.id),
  );
  return { outgoing, incoming };
}

function locationRelations(world, location) {
  const incoming = [];
  for (const settlement of world.settlements) {
    if (settlement.location_ref === location.id) {
      incoming.push({ kind: "本地圖", label: settlement.id, ref: `settlement:${settlement.id}`, source: settlement.relative_path, external: false });
    }
    for (const node of settlement.nodes) {
      if (node.anchor_key === location.id) {
        incoming.push({
          kind: "錨點",
          label: `${node.key}（${settlement.id}）`,
          ref: node.qualified_ref,
          source: settlement.relative_path,
          external: false,
        });
      }
    }
  }
  return { outgoing: [], incoming };
}

export function relationsOf(world, incomingExternal, ref) {
  if (!world || !ref) return null;
  let found = null;
  for (const location of world.locations) {
    if (location.qualified_ref === ref) found = locationRelations(world, location);
  }
  for (const settlement of world.settlements) {
    for (const node of settlement.nodes) {
      if (node.qualified_ref === ref) found = nodeRelations(world, settlement, node);
    }
  }
  for (const interior of world.interiors) {
    for (const room of interior.rooms) {
      if (room.qualified_ref === ref) found = roomRelations(world, interior, room);
    }
  }
  if (!found) return null;
  return { outgoing: found.outgoing, incoming: [...found.incoming, ...externalRows(incomingExternal, ref)] };
}
