# Design

The approved design is `docs/superpowers/specs/2026-11-06-map-editor-monster-spawn-layer-design.md`. It is authoritative for behaviour. This document fixes the code-level contracts a worker needs and records where the code forced an interpretation.

## Context

- The editor runs in its own environment and may not import the game. `tools/map_reference_context.py` is the only bridge: it writes `content/map-reference-context.json`, and `elosern_map_core.reference_context` decodes it.
- `snapshot.read_external_context` returns `ExternalContext(status, document, freshness)`. `document` is `None` when the artifact is missing, undecodable or refused before the freshness check. It is present when the artifact decoded but is not current.
- `decode_reference_context` raises `ReferenceContextError` on a schema mismatch. `read_external_context` turns that into status `incompatible` with no document. A decoded document can also report `incompatible` when only `exporter_version` differs.
- `EditorService` skips publication when `WorkspaceRead.digest` is unchanged (`app.py` around line 388). `_workspace_state` reads `external_context_status` from `latest`, not from `published`.
- Scene drawables already carry `layer`. `visibleScene` filters by it, and `continentScene` builds `items` from every mark except landmarks.
- `NavigationPanel` and `InspectorPanel` are generic. `ompContext.coordinates` falls through to interior code when a catalog entry has no `frame`, so every monster entry needs one.
- `parseContinentRef`, `removalOf`, `isRelationshipRef` and the settlement and interior parsers all return nothing for an unknown prefix, so `requestDelete` already falls through to the refusal path.
- `tools.spec_traceability` reads Python tests only. Node tests under `tools/map-editor/frontend/tests/` cannot carry a `covers_requirement` annotation, so every frontend requirement also needs a Python browser test before archive.

## Goals / Non-Goals

**Goals:**

- One workday of work inside the files listed in `proposal.md`.
- Pure frontend logic in one new module, `lib/monster_spawns.js`, so it is tested with `node --test`.

**Non-Goals:**

- Any game code change, including `world/lore/monster_placement.py` and `world/maps/`.
- Any new service route, document command, command kind or history entry.
- Bumping `EXPORTER_VERSION`.
- A section for activity areas, or a new discovery rule in `DISCOVERY_RULES`.
- Capture output: `capture.js` and `capture_snapshot.py` stay untouched, because the capture path never passes a section to `continentScene`.
- Per-control disabling or new warning UI. The existing delete explanation covers delete requests.

## Decisions

### D1. Core data model

In `packages/map-core/elosern_map_core/reference_context.py`, set `SCHEMA_VERSION: int = 2` and add:

```python
#: Closed site-kind vocabulary. Mirrors world.lore.monster_placement.MONSTER_SITE_KINDS;
#: a parity test holds them equal because the core may not import the game.
MONSTER_SITE_KINDS: tuple[str, ...] = ("camp", "nest", "boss_site", "stray", "encounter")


@dataclass(frozen=True, slots=True)
class MonsterSpawnMember:
    variant_key: str
    variant_name_zh: str
    species_key: str
    species_name_zh: str
    minimum: int
    maximum: int


@dataclass(frozen=True, slots=True)
class MonsterPoolEntry:
    composition_key: str
    weight: int
    members: tuple[MonsterSpawnMember, ...]


@dataclass(frozen=True, slots=True)
class MonsterZoneRow:
    key: str
    region_key: str
    region_name_zh: str
    rectangles: tuple[tuple[int, int, int, int], ...]  # (x_min, x_max, y_min, y_max)
    lower_density: int
    upper_density: int
    cell_capacity: int
    wave_budget: int
    recovery_delay: int
    replenishment_interval: int
    pool: tuple[MonsterPoolEntry, ...]


@dataclass(frozen=True, slots=True)
class MonsterSiteRow:
    key: str
    kind: str
    region_key: str
    region_name_zh: str
    coordinates: tuple[int, int]
    capacity: int
    one_shot: bool
    recover_after_ticks: int | None
    individual_name_zh: str | None
    composition_key: str
    members: tuple[MonsterSpawnMember, ...]


@dataclass(frozen=True, slots=True)
class MonsterSpawnSection:
    zones: tuple[MonsterZoneRow, ...] = ()
    sites: tuple[MonsterSiteRow, ...] = ()

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MonsterSpawnSection": ...
```

- `ReferenceContextDocument` gains a last field `monster_spawns: MonsterSpawnSection = MonsterSpawnSection()`. The default keeps the existing constructor calls in tests valid. Decoding still requires the key.
- `to_dict` includes `"monster_spawns": self.monster_spawns.to_dict()`.
- `MonsterSpawnSection.to_dict` sorts `zones` and `sites` by `key`, and keeps `pool` and `members` order. JSON key names are exactly the dataclass field names, and the shape matches the approved design's example. Rectangles and coordinates encode as lists.
- `from_dict` uses one private helper, `_exact_keys(data, keys, what)`, which raises `ReferenceContextError` when `data` is not a mapping or its key set differs in either direction. A private `_integer(value, what)` rejects `bool` and non-`int`.
- Beyond the approved list, decoding also refuses a zone with an empty `rectangles` list, because the zone mark is drawn from the first rectangle. The game's `_check_rectangles` already refuses that.
- `decode_reference_context` reads `monster_spawns` after `fingerprint`, so the existing error messages for partial documents stay reachable. A non-mapping value raises `ReferenceContextError`. It reads through `MonsterSpawnSection.from_dict`, not `data.get(..., {})`.
- Update the module docstring's format layout.
- `elosern_map_core/__init__.py` stays unchanged: callers import from the `reference_context` module, as `snapshot.py` already does.

### D2. Exporter

In `tools/map_reference_context.py`, add one pure function so tests inject synthetic rows:

```python
def build_monster_spawn_section(
    *,
    zones: Mapping[str, Any],
    sites: Mapping[str, Any],
    compositions: Mapping[str, Any],
    variants: Mapping[str, Any],
    species: Mapping[str, Any],
    region_names: Mapping[str, str],
) -> MonsterSpawnSection:
```

- Rows may be real registry rows or `types.SimpleNamespace` stand-ins; it reads attributes only. A member row is built from `compositions[key].members`, `variants[member.variant_key]` and `species[variant.species_key]`.
- `build_reference_context_document` calls it with `ECOLOGY_ZONE_REGISTRY`, `MONSTER_SITE_REGISTRY`, `ENCOUNTER_COMPOSITION_REGISTRY`, `MONSTER_VARIANT_REGISTRY`, `MONSTER_SPECIES_REGISTRY`, and `{key: row.display_name_zh for key, row in regions().items()}`, and passes the result as `monster_spawns=`.
- `DISCOVERY_RULES` stays unchanged.

### D3. Service

In `tools/map-editor/elosern_map_editor/snapshot.py`:

```python
def _empty_monster_spawns() -> dict[str, Any]:
    return {"zones": [], "sites": []}


def _monster_spawns(context: ExternalContext) -> dict[str, Any]:
    if context.document is None:
        return _empty_monster_spawns()
    return context.document.monster_spawns.to_dict()
```

- `WorkspaceRead` gains `monster_spawns: dict[str, Any] = field(default_factory=_empty_monster_spawns)` after `external_identifiers`, and it joins the `digest` payload list. Without that, a section-only change would never publish: the fingerprint hashes sources, not the section, so re-exporting after a region rename leaves `external_context_status` identical.
- Both `WorkspaceRead(...)` returns in `read_workspace` pass `monster_spawns=_monster_spawns(context)`, including the `load.world is None` branch.
- `_workspace_state` in `app.py` adds `"monster_spawns": latest.monster_spawns` directly after `external_context_status`. Reading from `latest` pairs the section with the status it is judged by.

### D4. Frontend module

Create `tools/map-editor/frontend/src/lib/monster_spawns.js`, importing only `cellMetres` from `./continent.js`. It exports exactly:

```js
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
export function parseMonsterRef(ref) {}   // { kind: "zone" | "site", key } | null
export function zoneLabel(zone) {}        // `生態區：${names.join("、")}`
export function siteLabel(site) {}        // `${SITE_KIND_WORDS[site.kind]}：${site.individual_name_zh ?? names.join("、")}`
export function gameDuration(seconds) {}  // "1 天 2 小時"; 0 -> "0 秒"
export function monsterShapes(world, spawns, chosen) {} // chosen is a Set of refs
export function monsterMarks(world, spawns) {}
export function monsterCatalogEntries(spawns) {}
export function monsterRecord(spawns, ref) {}    // { title, qualifiedRef, relativePath, fields } | null
export function monsterDetail(spawns, ref) {}    // { compositions: [...] } | null
export function monsterLayerState(workspace) {}  // { state, note, notice }
```

Rules:

- Species names come from the member rows in pool order, then member order, deduplicated by first appearance.
- `monsterShapes`: for each zone and each rectangle at `index`, a shape `{ id: `monster-zone:${key}:${index}`, ref, role: "monster-zone", type: "polygon", points, label, layer: MONSTER_LAYER, selectable: true, hoverTitle: true, selected: chosen.has(ref) }`. `points` are the four corners in the footprint order, with `west = x_min * cell`, `east = (x_max + 1) * cell`, `south = y_min * cell`, `north = (y_max + 1) * cell`, where `cell = cellMetres(world)`.
- `monsterMarks`: a zone mark `{ id: ref, kind: "monster", role: "monster-zone", glyph: ZONE_GLYPH, label, layer: MONSTER_LAYER, draggable: false, x, y }` at `x = (x_min + x_max + 1) / 2 * cell` and `y = (y_min + y_max + 1) / 2 * cell` of the first rectangle. A site mark has `role: "monster-site"`, `glyph: SITE_KIND_GLYPHS[site.kind]`, and sits at `x = (cx + 0.5) * cell`, `y = (cy + 0.5) * cell`.
- `monsterCatalogEntries` returns `{ ref, kind: "monster_zone" | "monster_site", domain: "continent", mapId: null, id: ref, label, parentLabel: "大陸", relativePath: MONSTER_SOURCE_PATH, layer: MONSTER_LAYER, frame, searchTerms }`.
  - Zone `frame`: `生態區矩形（1 km 格，含端點）：` followed by `x ${x_min}–${x_max}, y ${y_min}–${y_max}` per rectangle, joined with `；`.
  - Site `frame`: `座標：格 (${x}, ${y})（1 km 格）`.
  - `searchTerms` holds each member's `species_name_zh`, `species_key`, `variant_name_zh` and `variant_key`, deduplicated.
- `monsterRecord` returns `fields` built as `{ label, value }` strings, `—` for null.
  - Zone rows: 地形區, 密度（每 100 格）as `${lower}–${upper}`, 單格上限, 波次預算, 恢復延遲, 補充間隔.
  - Site rows: 種類 (the kind word), 地形區, 座標, 容量, 重生, 個體名稱. 重生 is `一次性` for a one-shot site, else `gameDuration(recover_after_ticks)` when that is not null.
  - 恢復延遲, 補充間隔 and 重生 render through `gameDuration`.
- `monsterDetail` returns `{ compositions: [{ key, chance, members: [{ species, variant, count }] }] }`.
  - Zone `chance` is `` `${(weight / total * 100).toFixed(1)}%` `` of the summed pool weight. A site has one composition with `chance: null`.
  - `count` is the single number when `minimum === maximum`, else `` `${minimum}–${maximum}` ``.
- `gameDuration` walks 天 (86400), 小時 (3600), 分 (60), 秒 (1) greedily and joins the nonzero parts with one space.
- `monsterLayerState(workspace)`:

```js
const status = workspace?.external_context_status;
const spawns = workspace?.monster_spawns;
const rows = (spawns?.zones?.length ?? 0) + (spawns?.sites?.length ?? 0);
if (!status || status.current) return { state: "current", note: null, notice: null };
if (rows) return { state: "stale", note: null, notice: `索引已過期，資料可能落後原始檔。重新產生：${REGENERATION_COMMAND}` };
return { state: "unavailable", note: `匯出資料不可用：${status.reasons?.[0] ?? status.status}`, notice: null };
```

### D5. Existing frontend modules

- `lib/layers.js`: append `{ key: "monsters", label: "怪物生成（匯出・唯讀）", visible: false }` to `CONTINENT_LAYERS`.
- `lib/search.js`: in `rank`, use `[entry.label, entry.id, entry.ref, ...(entry.searchTerms ?? [])]`.
- `lib/objects.js`: `objectCatalog(world, monsterSpawns = null)` sets `monsterCatalogEntries(monsterSpawns)` after `relationshipEntries`.
- `lib/map_scene.js`: `continentScene(world, selection = [], partition = null, monsterSpawns = null)` appends `monsterShapes(world, monsterSpawns, chosen)` last in `shapes`, so polygons sit above the land and take clicks, and `monsterMarks(world, monsterSpawns)` last in `marks`. `sceneFor` gains `{ partition = null, monsterSpawns = null }`. `items` picks the marks up unchanged. `capture.js` keeps calling without the fourth argument.
- `components/MapSurface.vue`:
  - The shape title condition becomes `(shape.derived || shape.hoverTitle) && shape.label && shape.showLabel !== false`.
  - Add one branch before the final `v-else`:

```vue
<template v-else-if="mark.kind === 'monster'">
  <title>{{ mark.label }}</title>
  <circle r="16" class="map-mark__hit" />
  <circle v-if="chosen.has(mark.id)" r="14" class="map-mark__ring" />
  <path :d="mark.glyph" class="map-mark__monster" data-monster-glyph />
</template>
```

- `components/NavigationPanel.vue`: new prop `layerNotes: { type: Object, default: () => ({}) }`. Under each layer's label, render `<p v-if="layerNotes[layer.key]" class="inspector__muted" :data-layer-note="layer.key">{{ layerNotes[layer.key] }}</p>`.
- `components/MonsterSpawnInspector.vue` (new): props `detail` (Object, required) and `notice` (String, default `""`). It has no emits and no controls.
  - Stale notice: `<p v-if="notice" class="inspector__reason" data-monster-stale>{{ notice }}</p>`.
  - `<h3 class="section-label">生成內容</h3>`, then one `<section data-monster-composition>` per composition with its `key` in `.mono`, the chance when not null, and one `<p data-monster-member>` per member showing species, variant and count.
  - Authored text uses text interpolation only.
- `App.vue`:
  - `const monsterSpawns = computed(() => workspace.value?.monster_spawns ?? null);`
  - `catalog` passes it as the second argument, and `fullScene` passes `monsterSpawns: monsterSpawns.value`.
  - `record` becomes `monsterRecord(monsterSpawns.value, selected.value) ?? inspect(world.value, selected.value)`.
  - Add `monsterInspection = computed(() => monsterDetail(monsterSpawns.value, selected.value))` and `monsterLayer = computed(() => monsterLayerState(workspace.value))`.
  - Pass `:layer-notes="monsterLayer.note ? { monsters: monsterLayer.note } : {}"` to `NavigationPanel`.
  - Render `<MonsterSpawnInspector v-if="monsterInspection" :detail="monsterInspection" :notice="monsterLayer.notice ?? ''" />` in the default slot of `InspectorPanel`, before the existing `ContinentInspector` block. Do not change `requestDelete`, `onCanvasMove` or any command path.
- `styles/editor.css`: directly before `.map-shape--selected`, so that rule still wins:

```css
.map-shape--monster-zone {
  fill: rgba(207, 68, 68, 0.18);
  stroke: var(--seal-400);
  stroke-width: 1;
}

.map-mark__monster {
  fill: var(--seal-500);
  stroke: var(--paper-300);
  stroke-width: 1;
}
```

### D6. Reuse of `InspectorPanel`

The approved design calls the header part of `MonsterSpawnInspector`. The code gets the same screen with less work by letting `monsterRecord` feed the existing `InspectorPanel`, which already renders title, monospace reference, source path and field rows. The new component holds only what the panel cannot: the notice and the composition rows. Alternative rejected: a parallel header, which would duplicate the panel and its focus handling.

### D7. Delete behaviour

`InspectorPanel` keeps its generic delete button, and `requestDelete` needs no change. With a current index the explanation key is `unavailable`, as the approved design states. With a stale or unavailable index the existing first-match order yields `index-unavailable` instead. Both write nothing, so this is accepted rather than special-cased.

### D8. Stale versus unavailable

The approved design's three states are derived on the frontend from `current` and row count, as in D4. An alternative, a new `available` flag in the payload, was rejected because the design specifies an empty section and the extra field would serve only one corner case: a decoded but empty section that is not current reports as unavailable, which is harmless in a dev-only tool.

### D9. Test placement

| Requirement | Node or service test | Traceable Python test for archive |
|---|---|---|
| Export and decode | `packages/map-core/tests/test_reference_context.py` round trip | `tests/test_map_reference_context.py` new classes |
| Workspace state | `tools/map-editor/tests/test_snapshot.py` | `tests/test_map_editor_service.py` new process test |
| Layer drawing | `tools/map-editor/frontend/tests/monster_spawns.test.mjs` | `web/tests/browser/test_map_editor_geography.py` new tests |
| Interaction and artifact state | same Node file | same browser file |

Every new browser test method must be added to exactly one list in `.github/browser-shards.json` in the same commit; `tests.test_evennia_test_optimization_contract` enforces this. All tests use the synthetic `synthetic.MONSTER_SPAWNS` fixture or inline synthetic rows. No test asserts shipped wording, real monster content or row counts of the committed artifact. Assertions read `data-*` hooks, references, order and numbers. `covers_requirement` annotations wait for archive sync, as `docs/development/spec-test-traceability.md` requires.

## Risks / Trade-offs

- [Region names come from `content/maps/continent.yaml`, which the source manifest excludes, and the editor can change one through `set_region_field`] → After such an edit the editor still reports the index as current and shows the old region name, while CI `--check` fails until the artifact is regenerated. This is kept as the approved design specifies, documented in `docs/development/map-editor.md`, and reported to the user as an open conflict. It affects only the region name row.
- [A new site kind in the game would make the regenerated artifact undecodable, emptying the layer] → The vocabulary parity test fails in CI at the same change.
- [Every later edit to `packages/map-core/**` or `tools/map_reference_context.py` makes the artifact stale] → Regeneration is the last implementation task, and `--check` runs after it.
- [Polygons above the land take clicks meant for the mainland] → The layer is hidden by default, and the mainland stays selectable from the object list.

## Migration Plan

Pre-release, so there is no compatibility path. Regenerate the committed artifact once. Rollback is a revert of the change, including the artifact.

## Human review document

`docs/development/map-editor.md`, section "3.14.3 Human review record", records the manual browser check. Visual legibility of the zone colour on the terrain raster, glyph readability at full-continent zoom, the site kind words and the theme fit at 1451x790 and 2560x1440 are human-reviewed. They are not requirements. The task list leaves that section as a dated record template for the reviewer, and no test depends on it.
