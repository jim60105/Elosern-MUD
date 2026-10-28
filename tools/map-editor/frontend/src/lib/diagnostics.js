// The diagnostics strip (frontend design §2, requirements §5.2): every
// condition grouped by class, each row naming its object, file, field and
// line, with a navigable target when one resolves. Classes:
//
//   structure  the candidate cannot load or be written;
//   external   the external reference index or result is invalid/unavailable;
//   service    a failed/uncertain/rejected command, a watcher error or a lost
//              connection;
//   semantic   saveable unfinished map work;
//   partition  the generated partition does not describe the current inputs.
//
// A target that sits on a hidden continent layer is offered as reveal-go
// (顯示圖層並前往), never selected silently. A diagnostic of a read that did
// not load, or one whose reference does not resolve, keeps its file:line and
// offers no navigation (there is no source editor).

import { DISCONNECTED } from "./workspace_client.js";
import { REFERENCE_CONTEXT_PATH } from "./paths.js";
import { cityGateRef, exteriorRef } from "./relationship_refs.js";

export const CLASSES = Object.freeze([
  { key: "structure", label: "結構錯誤", glyph: "✕", tone: "seal" },
  { key: "external", label: "外部索引與引用", glyph: "✕", tone: "seal" },
  { key: "service", label: "服務與存檔", glyph: "✕", tone: "seal" },
  { key: "semantic", label: "未完成", glyph: "▲", tone: "warn" },
  { key: "partition", label: "分區產物", glyph: "▲", tone: "warn" },
]);

export const GO = "go";
export const REVEAL_GO = "reveal-go";

export function diagnosticClass(item) {
  if (item.code === "stale_partition" || item.category === "freshness") return "partition";
  if (item.category === "external") return "external";
  if (item.category === "semantic") return "semantic";
  if (item.category === "service") return "service";
  return "structure";
}

function continentLayer(fieldPath) {
  if (/^terrain\.waterways/.test(fieldPath)) return "water";
  if (/^terrain\.ridge/.test(fieldPath)) return "ridge";
  return "terrain";
}

function objectTarget(catalog, ref) {
  const entry = catalog.get(ref);
  return entry ? { domain: entry.domain, mapId: entry.mapId, ref, layer: entry.layer } : null;
}

// Entrance fields whose diagnostic locates one relationship object (a
// field naming a list of several, such as the gates or links, keeps its map).
const RELATIONSHIP_FIELDS = Object.freeze([
  { prefix: "city_gate", owner: "settlement", ref: (id) => cityGateRef(id) },
  { prefix: "exterior", owner: "interior", ref: (id) => exteriorRef(id) },
]);

function relationshipTarget(catalog, settlementId, interiorId, field) {
  for (const rule of RELATIONSHIP_FIELDS) {
    const id = rule.owner === "settlement" ? settlementId : interiorId;
    if (!id || !(field === rule.prefix || field.startsWith(`${rule.prefix}.`))) continue;
    return objectTarget(catalog, rule.ref(id));
  }
  return null;
}

// Where a diagnostic of the displayed (loaded) snapshot points, or null.
export function diagnosticTarget(world, catalog, item) {
  if (!world) return null;
  const path = item.relative_path;
  const field = item.field_path ?? "";
  if (!path) {
    return item.code === "stale_partition" ? { domain: "continent", mapId: null, ref: null, layer: "partition" } : null;
  }
  if (path === world.continent.relative_path) {
    return { domain: "continent", mapId: null, ref: null, layer: continentLayer(field) };
  }
  if (world.locations.some((location) => location.relative_path === path)) {
    if (!item.object_id) return { domain: "continent", mapId: null, ref: null, layer: "locations" };
    return objectTarget(catalog, `location:${item.object_id}`);
  }
  if ((world.districts ?? []).some((district) => district.relative_path === path)) {
    const district = world.districts.find((row) => row.id === item.object_id);
    const landmark = district?.landmark;
    if (!landmark?.map_id || !landmark.object_id) return null;
    if (landmark.domain !== "settlement_node" && landmark.domain !== "interior_room") return null;
    return objectTarget(catalog, `${landmark.domain}:${landmark.map_id}:${landmark.object_id}`);
  }
  const settlement = world.settlements.find((row) => row.relative_path === path);
  if (settlement) {
    const entrance = relationshipTarget(catalog, settlement.id, null, field);
    if (entrance) return entrance;
    if (field.startsWith("wilderness_entry")) {
      const location = objectTarget(catalog, `location:${settlement.location_ref}`);
      return location ? { ...location, layer: "footprint" } : null;
    }
    return { domain: "settlement", mapId: settlement.id, ref: null, layer: null };
  }
  const interior =
    world.interiors.find((row) => row.relative_path === path) ??
    world.interiors.find((row) => row.layout_relative_path === path);
  if (interior) {
    const entrance = interior.relative_path === path ? relationshipTarget(catalog, null, interior.id, field) : null;
    return entrance ?? { domain: "interior", mapId: interior.id, ref: null, layer: null };
  }
  const layout = (world.layouts ?? []).find((row) => row.relative_path === path);
  if (layout && world.interiors.some((row) => row.id === layout.id)) {
    return { domain: "interior", mapId: layout.id, ref: null, layer: null };
  }
  return null;
}

function where(item) {
  if (!item.relative_path) return "（工作區）";
  return item.line ? `${item.relative_path}:${item.line}` : item.relative_path;
}

function synthesized(workspace, failure, connection) {
  const rows = [];
  const index = workspace?.external_context_status;
  if (index && !index.current) {
    rows.push({
      code: `external_index_${index.status ?? "unavailable"}`,
      category: "external",
      message: `外部索引不可用（${index.status}）：無法確認外部引用，刪除會被拒絕；檢視與一般編輯不受影響。${(index.reasons ?? []).join("；")}`,
      relative_path: index.relative_path ?? REFERENCE_CONTEXT_PATH,
      field_path: "",
      line: null,
    });
  }
  const partition = workspace?.partition_status;
  const core = [...(workspace?.diagnostics ?? [])].some((item) => item.code === "stale_partition");
  if (partition && !partition.current && !core) {
    rows.push({
      code: `partition_${partition.status}`,
      category: "freshness",
      message: `分區產物${partition.status === "stale" ? "過期" : "不可用"}：${(partition.reasons ?? []).join("；")}`,
      relative_path: partition.relative_path ?? null,
      field_path: "",
      line: null,
    });
  }
  if (connection === DISCONNECTED) {
    rows.push({ code: "disconnected", category: "service", message: "與編纂服務的連線中斷；現在無法寫入。", relative_path: null, field_path: "", line: null });
  }
  if (workspace?.following?.error) {
    rows.push({
      code: "watcher_error",
      category: "service",
      message: `檔案追蹤錯誤：${workspace.following.error}`,
      relative_path: null,
      field_path: "",
      line: null,
    });
  }
  if (failure) {
    rows.push({
      code: failure.code,
      category: "service",
      message: `${failure.command}：${failure.message}`,
      relative_path: failure.documentId ?? null,
      field_path: "",
      line: null,
    });
  }
  return rows;
}

// Grouped rows in class order; each group lists only active conditions.
export function diagnosticGroups({ workspace, world, catalog, failure = null, connection = null, hidden = [] }) {
  const candidate = (workspace?.candidate_diagnostics ?? []).map((item) => ({ item, navigable: false }));
  const current = (workspace?.diagnostics ?? []).map((item) => ({ item, navigable: true }));
  const extra = synthesized(workspace, failure, connection).map((item) => ({ item, navigable: false }));
  const off = new Set(hidden);
  const groups = new Map(CLASSES.map((entry) => [entry.key, { ...entry, rows: [] }]));
  [...candidate, ...current, ...extra].forEach(({ item, navigable }, index) => {
    const target = navigable ? diagnosticTarget(world, catalog, item) : null;
    const hiddenLayer = Boolean(target?.layer && target.domain === "continent" && off.has(target.layer));
    const entry = item.object_id ? catalog.get(`location:${item.object_id}`) : null;
    groups.get(diagnosticClass(item)).rows.push({
      id: `${index}:${item.code}`,
      code: item.code,
      message: item.message,
      where: where(item),
      field: item.field_path || null,
      object: entry?.label ?? item.object_id ?? null,
      target,
      action: target ? (hiddenLayer ? REVEAL_GO : GO) : null,
    });
  });
  return [...groups.values()].filter((group) => group.rows.length);
}

export function groupCounts(groups) {
  let errors = 0;
  let warnings = 0;
  for (const group of groups) {
    if (group.tone === "seal") errors += group.rows.length;
    else warnings += group.rows.length;
  }
  return { errors, warnings, total: errors + warnings };
}
