# Proposal

## Why

After `retire-limbo-city-gates`, no game code reads a settlement document's `city_gate`
block. The block is still declared by the map-core schema, written by the map editor and
the settlement synthesis tools, and present in every one of the 338 settlement documents.
That is authored data nothing consumes. The project is unreleased and forbids
compatibility leftovers, so the field is removed.

## What Changes

- **BREAKING (document schema)**: the settlement schema
  (`packages/map-core/elosern_map_core/schema.py`) drops the `city_gate` field. A
  settlement document that still carries the key is rejected with `unknown_field`, as
  any unsupported field already is. `CityGateDeclaration` and
  `SettlementDocument.city_gate` (`documents.py`) and the authoring check on
  `city_gate.node` (`authoring.py`) are deleted.
- Data: the `city_gate:` key is deleted from all 338 `content/maps/settlements/*.yaml`.
  334 of them hold an empty key (one line each). Four hold a populated row of three to
  four lines: `capital_altoria`, `elven_village_ciaran`, `elven_village_eolas` and
  `elven_village_fionnen`. The deletion is done by one throwaway scratchpad script,
  checked with the map-core loader. The script is not committed.
- Map editor (`tools/map-editor/`): the `set_city_gate` command, the `city_gate`
  relationship kind and reference (`city_gate:<settlement>`), the "起始房間入口" option
  in `EntranceForm.vue`, and the relation, scene, diagnostics and inspector rows for it
  are removed, together with their backend and frontend tests.
- Settlement synthesis (`tools/settlement_synthesis/generate.py`, `rework.py`) stops
  writing the key. `rework.py` no longer protects the city-gate node.
- Docs and the map-data-authoring skill stop describing the field.

## Batch:

- depends-on: retire-limbo-city-gates (the game must stop reading the block first)
- Transitively depends on subrace-start-settlements.
- Conflict notes: touches all 338 settlement YAML files with a one-key deletion. Any
  in-flight change that edits settlement documents (for example the elven village
  documents) must be merged or rebased first, and this change's apply must start from
  current master. It overlaps `retire-limbo-city-gates` only in docs
  (`docs/development/metric-settlements.md`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-settlement-sources`: schema rejection now lists a `city_gate` block among the
  removed authorities.
- `settlement-map-rework`: the city gate is no longer a protected node in a settlement
  replace.
- `map-editor-relationships`: the entrance tool offers no starting-room entry kind.

## Impact

- Code: `packages/map-core/elosern_map_core/{schema,documents,authoring}.py`,
  `tools/map-editor/elosern_map_editor/{commands,relationships,settlements,snapshot}.py`,
  `tools/map-editor/frontend/src/{components/EntranceForm.vue,components/RelationshipInspector.vue,lib/relationships.js,lib/relationship_refs.js,lib/relations.js,lib/settlement.js,lib/map_scene.js,lib/objects.js,lib/diagnostics.js}`,
  `tools/settlement_synthesis/{generate,rework}.py`.
- Data: `content/maps/settlements/*.yaml` (338 files). Regenerated
  `content/map-reference-context.json` if its digest changes.
- Tests: the map-core, map-editor (Python and node) and top-level map tests listed in
  tasks.md, and the inline YAML in `world/maps/tests/test_settlement_{reload,sources}.py`.
- Docs: `docs/development/{map-authoring-documents,map-editor,metric-settlements,settlement-synthesis,sparse-settlement-graphs}.md`,
  `docs/lore/settlement-locations.md`,
  `.agents/skills/map-data-authoring/{SKILL.md,references/settlements.md}`.
- No human-reviewed document.
