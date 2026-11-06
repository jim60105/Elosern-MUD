// The read-only monster spawn layer (frontend design: map-editor monster
// spawn layer). Every value comes from the exported `monster_spawns` section
// of the reference context; this module only arranges it into drawables,
// catalog entries and inspector rows. It applies no game rule, offers no drag,
// edit or delete path, and keeps authored names as plain strings for text
// interpolation only.

import { cellMetres } from "./continent.js";

export const MONSTER_LAYER = "monsters";
export const MONSTER_SOURCE_PATH = "world/lore/monster_placement.py";
export const REGENERATION_COMMAND = "uv run --locked python -m tools.map_reference_context";
export const SITE_KIND_WORDS = Object.freeze({
  camp: "營地", nest: "巢穴", boss_site: "首領點", stray: "游蕩", encounter: "遭遇",
});
export const ZONE_GLYPH = "M-7 0 L-3.5 -6 L3.5 -6 L7 0 L3.5 6 L-3.5 6 Z";
export const SITE_KIND_GLYPHS = Object.freeze({
  camp: "M0 -7 L7 6 L-7 6 Z",
  nest: "M-7 0 A7 7 0 1 0 7 0 A7 7 0 1 0 -7 0 Z",
  boss_site: "M0 -8 L2.4 -2.4 L8 0 L2.4 2.4 L0 8 L-2.4 2.4 L-8 0 L-2.4 -2.4 Z",
  stray: "M-7 -6 L7 -6 L0 7 Z",
  encounter: "M-6 -6 H6 V6 H-6 Z",
});

export const monsterZoneRef = (key) => `monster_zone:${key}`;
export const monsterSiteRef = (key) => `monster_site:${key}`;

const PREFIXES = [["monster_zone:", "zone"], ["monster_site:", "site"]];

export function parseMonsterRef(ref) {
  const text = String(ref ?? "");
  for (const [prefix, kind] of PREFIXES) {
    if (text.startsWith(prefix) && text.length > prefix.length) return { kind, key: text.slice(prefix.length) };
  }
  return null;
}

const zonesOf = (spawns) => spawns?.zones ?? [];
const sitesOf = (spawns) => spawns?.sites ?? [];

function unique(values) {
  return [...new Set(values)];
}

function zoneMembers(zone) {
  return (zone.pool ?? []).flatMap((entry) => entry.members ?? []);
}

function speciesNames(members) {
  return unique(members.map((member) => member.species_name_zh));
}

export function zoneLabel(zone) {
  return `生態區：${speciesNames(zoneMembers(zone)).join("、")}`;
}

export function siteLabel(site) {
  return `${SITE_KIND_WORDS[site.kind]}：${site.individual_name_zh ?? speciesNames(site.members ?? []).join("、")}`;
}

const DURATION_UNITS = [[86400, "天"], [3600, "小時"], [60, "分"], [1, "秒"]];

// Game seconds in the largest fitting units, zero parts left out.
export function gameDuration(seconds) {
  let rest = Math.max(0, Math.floor(Number(seconds) || 0));
  if (rest === 0) return "0 秒";
  const parts = [];
  for (const [size, unit] of DURATION_UNITS) {
    const count = Math.floor(rest / size);
    if (count) parts.push(`${count} ${unit}`);
    rest -= count * size;
  }
  return parts.join(" ");
}

// One polygon per zone rectangle over its inclusive cells: SW, SE, NE, NW.
export function monsterShapes(world, spawns, chosen = new Set()) {
  const cell = cellMetres(world);
  return zonesOf(spawns).flatMap((zone) => {
    const ref = monsterZoneRef(zone.key);
    const label = zoneLabel(zone);
    return zone.rectangles.map(([xMin, xMax, yMin, yMax], index) => {
      const west = xMin * cell;
      const east = (xMax + 1) * cell;
      const south = yMin * cell;
      const north = (yMax + 1) * cell;
      return {
        id: `monster-zone:${zone.key}:${index}`,
        ref,
        role: "monster-zone",
        type: "polygon",
        points: [{ x: west, y: south }, { x: east, y: south }, { x: east, y: north }, { x: west, y: north }],
        label,
        layer: MONSTER_LAYER,
        selectable: true,
        hoverTitle: true,
        selected: chosen.has(ref),
      };
    });
  });
}

// One fixed-size mark per zone (centre of its first rectangle) and per site
// (its cell centre). Never draggable.
export function monsterMarks(world, spawns) {
  const cell = cellMetres(world);
  const zones = zonesOf(spawns).map((zone) => {
    const [xMin, xMax, yMin, yMax] = zone.rectangles[0];
    return {
      id: monsterZoneRef(zone.key),
      kind: "monster",
      role: "monster-zone",
      glyph: ZONE_GLYPH,
      label: zoneLabel(zone),
      layer: MONSTER_LAYER,
      draggable: false,
      x: ((xMin + xMax + 1) / 2) * cell,
      y: ((yMin + yMax + 1) / 2) * cell,
    };
  });
  const sites = sitesOf(spawns).map((site) => {
    const [cx, cy] = site.coordinates;
    return {
      id: monsterSiteRef(site.key),
      kind: "monster",
      role: "monster-site",
      glyph: SITE_KIND_GLYPHS[site.kind],
      label: siteLabel(site),
      layer: MONSTER_LAYER,
      draggable: false,
      x: (cx + 0.5) * cell,
      y: (cy + 0.5) * cell,
    };
  });
  return [...zones, ...sites];
}

function searchTerms(members) {
  return unique(
    members.flatMap((member) => [member.species_name_zh, member.species_key, member.variant_name_zh, member.variant_key]),
  );
}

export function monsterCatalogEntries(spawns) {
  const entry = (ref, kind, label, frame, members) => ({
    ref,
    kind,
    domain: "continent",
    mapId: null,
    id: ref,
    label,
    parentLabel: "大陸",
    relativePath: MONSTER_SOURCE_PATH,
    layer: MONSTER_LAYER,
    frame,
    searchTerms: searchTerms(members),
  });
  return [
    ...zonesOf(spawns).map((zone) =>
      entry(
        monsterZoneRef(zone.key),
        "monster_zone",
        zoneLabel(zone),
        `生態區矩形（1 km 格，含端點）：${zone.rectangles
          .map(([xMin, xMax, yMin, yMax]) => `x ${xMin}–${xMax}, y ${yMin}–${yMax}`)
          .join("；")}`,
        zoneMembers(zone),
      ),
    ),
    ...sitesOf(spawns).map((site) =>
      entry(
        monsterSiteRef(site.key),
        "monster_site",
        siteLabel(site),
        `座標：格 (${site.coordinates[0]}, ${site.coordinates[1]})（1 km 格）`,
        site.members ?? [],
      ),
    ),
  ];
}

function find(spawns, ref) {
  const parsed = parseMonsterRef(ref);
  if (!parsed) return null;
  const rows = parsed.kind === "zone" ? zonesOf(spawns) : sitesOf(spawns);
  const row = rows.find((item) => item.key === parsed.key);
  return row ? { kind: parsed.kind, row } : null;
}

// Region display names live in the map document, not the export.
function regionName(world, key) {
  const region = (world?.continent?.regions ?? []).find((item) => item.id === key);
  return region?.display_name_zh ?? key;
}

const text = (value) => (value === null || value === undefined ? "—" : String(value));

export function monsterRecord(spawns, ref, world) {
  const found = find(spawns, ref);
  if (!found) return null;
  const { kind, row } = found;
  if (kind === "zone") {
    return {
      title: zoneLabel(row),
      qualifiedRef: ref,
      relativePath: MONSTER_SOURCE_PATH,
      fields: [
        { label: "地形區", value: text(regionName(world, row.region_key)) },
        { label: "密度（每 100 格）", value: `${row.lower_density}–${row.upper_density}` },
        { label: "單格上限", value: text(row.cell_capacity) },
        { label: "波次預算", value: text(row.wave_budget) },
        { label: "恢復延遲", value: gameDuration(row.recovery_delay) },
        { label: "補充間隔", value: gameDuration(row.replenishment_interval) },
      ],
    };
  }
  let recovery = "—";
  if (row.one_shot) recovery = "一次性";
  else if (row.recover_after_ticks !== null && row.recover_after_ticks !== undefined) {
    recovery = gameDuration(row.recover_after_ticks);
  }
  return {
    title: siteLabel(row),
    qualifiedRef: ref,
    relativePath: MONSTER_SOURCE_PATH,
    fields: [
      { label: "種類", value: text(SITE_KIND_WORDS[row.kind]) },
      { label: "地形區", value: text(regionName(world, row.region_key)) },
      { label: "座標", value: `格 (${row.coordinates[0]}, ${row.coordinates[1]})` },
      { label: "容量", value: text(row.capacity) },
      { label: "重生", value: recovery },
      { label: "個體名稱", value: text(row.individual_name_zh) },
    ],
  };
}

function memberRows(members) {
  return (members ?? []).map((member) => ({
    species: member.species_name_zh,
    variant: member.variant_name_zh,
    count: member.minimum === member.maximum ? String(member.minimum) : `${member.minimum}–${member.maximum}`,
  }));
}

export function monsterDetail(spawns, ref) {
  const found = find(spawns, ref);
  if (!found) return null;
  const { kind, row } = found;
  if (kind === "site") {
    return { compositions: [{ key: row.composition_key, chance: null, members: memberRows(row.members) }] };
  }
  const total = (row.pool ?? []).reduce((sum, entry) => sum + entry.weight, 0);
  return {
    compositions: (row.pool ?? []).map((entry) => ({
      key: entry.composition_key,
      chance: `${((entry.weight / total) * 100).toFixed(1)}%`,
      members: memberRows(entry.members),
    })),
  };
}

// current: draws normally; stale: draws with a notice; unavailable: empty,
// with the reason on the layer row.
export function monsterLayerState(workspace) {
  const status = workspace?.external_context_status;
  const spawns = workspace?.monster_spawns;
  const rows = (spawns?.zones?.length ?? 0) + (spawns?.sites?.length ?? 0);
  if (!status || status.current) return { state: "current", note: null, notice: null };
  if (rows) return { state: "stale", note: null, notice: `索引已過期，資料可能落後原始檔。重新產生：${REGENERATION_COMMAND}` };
  return { state: "unavailable", note: `匯出資料不可用：${status.reasons?.[0] ?? status.status}`, notice: null };
}
