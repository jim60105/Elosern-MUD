# Proposal

## Why

Monster spawn data is authored in `world/lore/monster_placement.py`, but the map editor cannot show it, so an author cannot see where monsters are born or find the places that can spawn a given monster. The approved design `docs/superpowers/specs/2026-11-06-map-editor-monster-spawn-layer-design.md` adds a read-only continent layer for both lookups.

## What Changes

- **BREAKING** `content/map-reference-context.json` moves to schema version 2 with a required `monster_spawns` section. Version 1 documents are refused; the committed artifact is regenerated and no compatibility path exists.
- `tools/map_reference_context.py` exports every ecology zone and manual site, with names resolved at export.
- `elosern_map_core.reference_context` encodes the section deterministically and decodes it strictly.
- The editor service publishes the decoded section in the workspace state as `monster_spawns`.
- The continent view gains a hidden-by-default layer that draws zone rectangles and zone and site marks.
- New references `monster_zone:<key>` and `monster_site:<key>` are selectable and in the object catalog, with no drag, edit or delete path.
- Catalog `searchTerms` make a species or variant search return every zone and site that can spawn it.
- A read-only `MonsterSpawnInspector` shows composition, chance and count ranges, plus a stale notice.

Non-goals: activity areas and roaming bounds, live population or any database read, editing spawn data, per-cell eligibility, and any change to game spawn behaviour.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-external-reference-context`: the export gains the monster spawn section, and decoding refuses a malformed section or another schema version.
- `map-editor-service`: the workspace state publishes the decoded section.
- `map-editor-geography`: the continent gains the read-only monster spawn layer.
- `map-editor-interaction`: search, selection, inspection and artifact-state reporting cover monster spawn objects.

## Impact

- Code: `tools/map_reference_context.py`; `packages/map-core/elosern_map_core/reference_context.py`; `tools/map-editor/elosern_map_editor/snapshot.py` and `app.py`; frontend `lib/monster_spawns.js` (new), `lib/layers.js`, `lib/search.js`, `lib/objects.js`, `lib/map_scene.js`, `components/MapSurface.vue`, `components/NavigationPanel.vue`, `components/MonsterSpawnInspector.vue` (new), `App.vue`, `styles/editor.css`.
- Generated artifact: `content/map-reference-context.json`.
- Fixtures that hard-code schema version 1: `tools/map-editor/tests/synthetic_workspace.py`, `tests/test_map_capture_snapshot.py`.
- CI manifest: `.github/browser-shards.json` registers the new browser test methods.
- Docs: `docs/development/map-editor.md`, `docs/development/adding-monsters.md`.
- Dependencies: none added. Game behaviour and the capture pipeline are unchanged.
- Human-reviewed, not test-established: visual legibility of the layer, the site kind words and the ink-and-gold theme fit at 1451x790 and 2560x1440. The review is recorded in the named review document `docs/development/map-editor.md`, section "3.14.3 Human review record".
