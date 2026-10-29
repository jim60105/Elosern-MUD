# Design

## Context

The prerequisite `map-core-settlement-diagnostics` supplies shared settlement/interior rejection rules. See `proposal.md` for motivation and the handoff for reproduction. The engine design's YAML exception and deterministic persistence boundary remain unchanged. Editor design §7.1 continues to require one document per operation. The frontend design's continuous following and fingerprint guard remain in force; this fix adds no handoff/turn UI.

Current callers mix `locations[location_ref].cell`, `document.binding.anchor_cell` and the wilderness mask midpoint as frame anchors. `wilderness_destination.settlement_world_position_m` currently uses the entry midpoint, while `world/lore/anchors.world_position_m` uses the location cell. Both must use the location authority even when a legitimate asymmetric mask has another midpoint.

## Goals / Non-Goals

**Goals:** derive all placement from one location cell and one anchor node, retain rigid location-relative mask geometry, and prove single-owner editing and occupied-room adoption end to end.

**Non-Goals:** multi-document transactions, new inspector controls, terrain/topology/prose changes, a general command redesign, automatic re-centering of edited masks, compatibility parsers, migration tooling or a release bump.

## Decisions

### D1. Remove binding completely

Delete `BindingDeclaration`, the settlement `binding` schema/data field and all serialization/projection input paths. Keep schema version 1 because this is an unreleased clean cutover; old fields fail the existing unknown-field policy. Runtime view objects may retain derived local-anchor tuples or absolute entry origins where real consumers need them. Those values are recomputed from the candidate and never accepted as authored alternatives or compatibility aliases.

For settlement S, let L be `locations[S.location_ref].cell`, A be its unique `anchor_room` local `(x_m,y_m)`, and P be a node position. The sole transform is:

```
world_m(P) = (1000*L.x + 500, 1000*L.y + 500) + P - A
```

Reuse `local_to_world_m`; do not copy its calculation into adapters. A missing anchor remains diagnosed WIP with unavailable world-position/partition-seed projections. There is no default zero anchor or first-node lookup in arbitrary mappings. Multiple anchors or a wrong anchor key are rejected by the prerequisite's core rules. Local coordinates and qualified references remain available for unfinished editing.

Delete `map_data.py`'s old local-anchor and geographic-anchor equality checks with the fields. Retain only candidate composition and shared diagnostics. Runtime `LocalFrameAnchor` becomes a derived view populated from A. `ReferenceIndex` continues to expose stable local node positions and location cells; audit its helpers and dependents so any world projection resolves this frame from the same candidate rather than storing another authored binding.

Anchor-node drag changes A and the dragged node's P together. The anchor stays at L's cell centre, untouched nodes shift by negative local delta, and L/mask/gates do not move. A group drag that includes the anchor shifts each moved P and A together, so selected nodes keep their world positions while untouched nodes shift. Stable identities, roads, interiors and compass directions are unaffected. Document these consequences in the editor and metric-settlement guides.

Alternative rejected: update duplicated values alongside the drag. A cross-document update violates §7.1, and a second frontend command creates an intermediate invalid world and extra undo entry. Merely adding equalities to the gate would refuse the intended gesture.

### D2. Location-relative wilderness entry and absolute editing boundary

The authored entry retains shape and gate relationships and replaces origin with:

```
wilderness_entry:
  shape: ['#']
  offset: {dx: 0, dy: 0}
  gates: [{return_direction: n, destination_node: entrance}]
```

`dx`/`dy` are signed integer cell deltas using core integer bounds, excluding booleans, strings, fractions and unknown keys. Absolute geometry is resolved only with an explicit candidate location:

```
origin_cell = L + offset
hash_cell(row, column) = origin_cell + (column, row)
```

Row zero is the southern row and row indices grow north, preserving existing conventions. Midpoint remains the floor-divided bounding box of hash cells. Point shapes retain no obstacle cells, yet their single hash/anchor cell participates in terrain, gate and collision validation. `gate_approach_cell` and entry geometry access receive L explicitly or a candidate-derived immutable absolute geometry view. No helper reads global/published locations or silently treats offset as an origin.

Keep `set_footprint_cell`'s absolute `cell` payload and `toggled_mask`'s absolute selected-cell contract. Give the latter explicit current location context at the service boundary. Resolve the prior absolute origin, apply the existing grow/set/clear algorithm, and save `new_offset = new_absolute_origin - L`; existing hash cells remain at their absolute positions while the mask grows west/south. A location move changes L alone, translating hash/obstacle cells, midpoint and approaches rigidly. An anchor-node move leaves L and entry offset unchanged.

The game entry carrier may expose `origin_xy` as derived absolute geometry. Its mask/ray calculations delegate to the same core geometry used by diagnostics and previews. Runtime gate identity and the absolute-cell traversal APIs remain unchanged.

### D3. Commands, projection and minimal UI

Remove `SetBinding`, registry/export entries, the frontend `binding` payload builder and `ContinentInspector.vue` binding fields and handlers. Requests named `set_binding` are unknown and write nothing. Keep the existing `App.vue` location drag emitting one `locationField(id, 'cell', cell)`; do not add a settlement request, auto-shift command, regeneration-on-drag or a second history entry.

`create_settlement` retains `settlement_id`, `location_id` and current `options`; remove `anchor_cell` and `local_anchor_m` arguments from every caller. The only frame-selection input is `location_id`. Creation writes an empty graph without binding, preserving existing diagnosed WIP and no fabricated room. The first `create_node` in an empty graph sets `prototype_parent: anchor_room` and `anchor_key: location_ref`, retaining the entered node ID, position and other fields. Subsequent nodes use their existing authored prototypes. If an anchor is later deleted from a non-empty graph, do not silently promote another node; report missing-anchor WIP until the user supplies one through existing prototype fields. The core rejects a second anchor.

`relationships.py` creates a first wilderness entry as a single-hash mask at offset `(0,0)`, with the selected node/direction. It needs no geographic coordinate in the settlement document. `snapshot.py` projects derived world frame and absolute footprint cells from the current world; remove editable binding data. Existing read-only map/footprint displays remain. No controls or panels are added.

### D4. Midpoint mismatch is advisory

The prerequisite's invalid-mask and collision diagnostics remain blocking. A valid mask midpoint different from L gets code `footprint_location_offset`, category `semantic`, severity `warning`. It does not trigger a structure error, re-center the mask or independently prevent adoption. This also avoids making a previously unenforced midpoint equality a new game rejection.

`Diagnostic` currently has no severity and `compile_runtime` rejects any diagnostic. Add an explicit severity field defaulting to error, serialize it, and filter only blocking diagnostics at readiness/rejection boundaries. Update core compile, game adapter checks, checker exit status, regeneration admission and editor readiness calculations that currently treat any diagnostic as a blocker. The existing diagnostics strip can show the warning with its existing warning treatment; no new editor UI is introduced. Tests pair a warning-only accepted world with warning-plus-blocking-fault rejection to prevent weakening existing gates.

### D5. Consumer cutover inventory

| Owner | Cutover |
| --- | --- |
| Core `schema.py`, `documents.py` | Remove binding/origin declarations and parsing; type signed offset; explicit location-context geometry |
| Core `authoring.py`, `diagnostics.py` | Resolve entry/frame once per candidate where practical; pass location to gate approach checks; advisory warning semantics; retain prerequisite rules |
| Core `references.py`, `partition.py` and geometry callers | Derive frame/entry cells from current location and anchor node; refuse unavailable WIP seeds without fabricated placement |
| Editor `geography.py`, `snapshot.py` | Delete binding command/projection; absolute footprint API converts offset at the owning boundary; current-world geometry |
| Editor `settlements.py`, `relationships.py` | Binding-free creation/first-anchor behavior; zero-offset default gate entry |
| Frontend `lib/continent.js`, `lib/settlement.js`, `ContinentInspector.vue`, command tests and synthetic workspace | Remove binding and creation arguments; retain one drag request; fixtures use relative offsets |
| Game `world/maps/map_data.py`, `geography.py`, `wilderness_destination.py` | Remove old equality checks; compose derived absolute entries/frames; world positioning always uses L/A, even for asymmetric masks |
| Game `world/lore/anchors.py`, `wilderness_entry.py` | Derived local-frame and absolute entry views; traversal/core geometry agreement |
| `tools/map_district_partition.py` district seeds and core partition snapshot | Same new frame in both producers; unchanged geometry gives unchanged seeds, ownership and outlines |
| `tools/map_reference_context.py` and `content/map-reference-context.json` | Regenerate after final core/lore edits because implementation files belong to the hashed source closure; keep discovery/freshness rules unchanged |
| Content and fixtures | Both settlement documents convert with schema; all core/editor/game and synthetic-data fixtures stop supplying old fields; retain real room IDs and authored topology |

No legacy schema branches, deprecated commands, re-exports, second transforms or temporary comparison scripts remain. Search exact removed-field usages during apply to classify retained derived runtime attributes versus obsolete authored accesses.

### D6. Conversion evidence and live-data recovery are separate inputs

First record a temporary, read-only baseline from committed pre-change sources, excluding the three live dirty files. For `capital_altoria.yaml` and `village_ciaran.yaml`, convert `offset = old_origin - committed_location_cell`; A comes from the committed anchor node. Capture sorted canonical bytes for every node's world metres, hash/obstacle cells, midpoint and gate approaches before and after. Require byte-identical derived bytes for both documents. Do not install permanent tests pinning shipped coordinate tables or content counts.

For unchanged committed geography, regenerate from the converted candidate and compare the complete serialized partition after excluding only `source_signature`; the geometric input fingerprint, owner data, outlines and all other fields must match the committed artifact. `partition_codec.partition_source_signature` hashes raw file fingerprints, so schema-only edits necessarily change that metadata. Do not spoof the old signature or weaken freshness to obtain whole-file equality. Run both the skill regeneration `--check` and `tools.map_district_partition --check` against the newly generated artifact.

Then recover the current live session deliberately. It has already been applied by another process and the stash is empty according to the assignment; do not apply/drop a stash or replace any source from HEAD. Preserve Ciaran node positions, Ciaran location `(1366,554)` pending confirmation, and Fionnen `(1465,1237)`. The stale Ciaran absolute origin is evidence of the bug, so subtracting its old origin from the already-moved location would encode the bug as a nonzero offset. Instead carry the committed location-relative offset established above (currently a centered point entry) into the live document, preserving its intended moved entrance. Recompute local anchor from the edited anchor node, never from stale binding.

Before the recovery write, confirm the other process is no longer writing these owners and ask the Ciaran question below. If the user confirms the move, keep it; if they give another intended cell, apply only that instructed cell before regeneration. No arbitrary relocation or terrain change is authorized. Regenerate the entire partition from the recovered final YAML; the partial dirty JSON is never a regeneration input or accepted baseline. Core diagnostics must report any genuine terrain/collision failure at the chosen destination; obtain a valid intended cell from the user if it is not game-ready. Do not suppress those diagnostics or invent a fallback cell.

Refresh `content/map-reference-context.json` again after this slice's final core/lore implementation changes, using `uv run --locked python -m tools.map_reference_context`, and run the same command with `--check`. Its discovery closure hashes core/lore source bytes, so even schema-only implementation changes require this refresh. Run from the final valid recovered world; before recovery is resolved, the isolated valid conversion candidate can establish exporter/freshness evidence without touching the live files. Commit the refreshed index with this cutover, preserving incoming-reference semantics and the existing dependency closure. A stale index must not silently disable deletion or object-removing undo after the fix.

This recovery happens during implementation, never while preparing this proposal. A temporary conversion report records the captured baseline revision, compared outputs and regeneration results. Remove scratch exporters/comparators after recording evidence in the apply handoff.

### D7. Test traceability and acceptance ownership

Every modified requirement keeps its exact heading and existing canonical ID. IDs below were read from `tools.spec_traceability list`. Add `covers_requirement` imported from `tools.spec_traceability` only to discoverable test functions whose assertions establish the claim; obtain IDs from the tool again at apply/sync time.

| Requirement ID | Planned discoverable tests | Proof |
| --- | --- | --- |
| `map-settlement-sources::settlement-documents-own-complete-local-map-declarations` | `packages/map-core/tests/test_authoring.py`, `test_yaml_codec.py`, `test_partition.py`, `test_settlement_preview.py`; `tests/test_map_settlement_contract.py` | New schema rejects old authorities; independent L/A/offset arithmetic; asymmetric-mask game/core transform agreement; rigid translation and current-world reload |
| `map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls` | `tests/test_map_editor_geography.py`; `tools/map-editor/tests/test_geography.py`; `web/tests/browser/test_map_editor_workflows.py` | One command/history entry, only location owner changes, absolute footprint growth, undo/redo and service restart; old command refused |
| `map-editor-settlement-graphs::settlement-tools-preserve-stable-graph-identity-and-explicit-direction` | `tests/test_map_editor_settlements.py`; editor settlement/relationship unit tests | No binding args; empty WIP, first anchor, second-anchor rejection, local/group movement semantics and zero-offset default gate |
| `map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world` | `world/maps/tests/test_editor_final_yaml_adoption.py`, affected settlement-source and wilderness-destination tests | Final-YAML moved location, occupied anchor/exit identity and double synchronization; centered point marker/entrance equality; reject stale partition |
| `map-authoring-documents::authoring-diagnostics-and-runtime-acceptance-have-distinct-gates` | Core authoring tests and `tests/test_map_authoring_contract.py`, game candidate tests | Prerequisite invalid-world matrix on new schema; advisory-only adoption and warning-plus-error rejection; no obsolete equality rule |

The existing final-YAML test helper only re-signs artifact metadata and does not regenerate geometry. The moved-location case must use a genuinely regenerated candidate artifact (or the real generator over a small synthetic candidate), publish/read that artifact in the test, and assert actual moved geometry. A metadata-only replacement is insufficient evidence for adoption after geographic movement.

Extend the real browser workflow with a synthetic settlement-backed location drag. Capture POST count and changed-file digests, independently reload core world geometry, exercise one undo and redo, then restart the service and compare persisted geometry. Reuse `step`/`core`/`tree_digest` harness behavior. Register every new browser test method/class in `.github/browser-shards.json`, including inherited methods under existing concrete classes; update `.github/evennia-shards.json` only if new game test modules are introduced.

Use independent synthetic arithmetic such as the spec's `(10,20)` L and `(100,200)` A case. Do not use the implementation helper to compute the expected transform. Shipped conversion comparison is temporary acceptance evidence, separate from permanent synthetic mechanism tests and existing tagged data contracts.

| Handoff criterion | Owner / evidence |
| --- | --- |
| 1 | EDIT-DRAG / EDIT-HISTORY and PLACE-LOCATION, process plus real browser |
| 2 | GRAPH-ANCHOR / PLACE-ANCHOR, independent arithmetic and documented group semantics |
| 3 | Prerequisite DIAG scenarios rerun under final schema; PLACE-SCHEMA removes equality defects |
| 4 | D6 temporary comparison of both documents plus full partition payload comparison and both check commands |
| 5 | ADOPT-LOCATION / ADOPT-POINT in final-YAML occupied-room test with real regeneration |
| 6 | EDIT-BROWSER in the named browser workflow file and shard manifest |
| 7 | D8's exact documentation inventory, human review of wording |
| 8 | D6 live recovery, explicit Ciaran answer and full partition regeneration |

### D8. Required documentation changes

Update `docs/development/map-authoring-documents.md` settlement fields and diagnostic severity; `docs/development/map-editor.md` §3.8 to remove `set_binding` and explain absolute footprint controls, and §3.9 for binding-free creation/anchor-node semantics; `docs/development/continental-geography.md`; `docs/development/metric-settlements.md`. Update `.agents/skills/map-data-authoring/SKILL.md` invariant table and movement recipe, `references/settlements.md`, `references/locations-and-districts.md`, and `scripts/check_map_sources.py`. Remove impossible binding-equality repair advice and copied core rejection rules. Align affected coordinate-ownership text in the approved map-editor architectural design, especially §§4.1/4.3/5, while leaving §7.1 intact.

Human review uses `tmp/map-editor-location-move-handoff.md` and the approved editor frontend design/prototype at `docs/design/map-editor/`. Review reduced inspector scope and document clarity without automated copy/markup pinning. No requirement is added solely for prose, authored document values, counts or visual polish.

## Risks / Trade-offs

- Source conversion and caller changes must land together. Mitigation: one schema/caller/content cutover with all old fields refused, after shared diagnostics have landed.
- A warning-only candidate could accidentally bypass real gates. Mitigation: explicit error severity defaults and paired warning-plus-error, stale-artifact and external-invalid tests at every readiness boundary.
- Stale Ciaran values could become a persistent relative offset. Mitigation: conversion-only committed baseline first, recovery offset preserved across the user's location drag second.
- Location drags legitimately stale the partition and can expose invalid terrain. Mitigation: retain visible diagnostics and explicit regeneration, with no hidden second document write.

## Migration Plan

There is no compatibility or persistent-data migration. Convert the two authored settlement documents and every fixture/caller with the schema change. Prepare byte-comparison evidence from isolated committed inputs, retain user edits according to D6, then regenerate from the final intended YAML. Rollback before release is an ordinary coordinated source reversal; never restore over user edits or accept a partially generated artifact.

## Open Questions

Is Ciaran's live target `(1366, 554)` intended? This is unresolved. Record the answer before final data recovery/adoption. It changes the chosen authored location, not the schema, command contract or task breakdown. Planning preserves the three dirty files unchanged.

## Verification plan

During apply, use uv-managed focused core/editor suites, the top-level map contracts, the skill checker and both partition check commands, reference-context generation and `tools.map_reference_context --check`, the final-YAML adoption test with `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb world.maps.tests.test_editor_final_yaml_adoption` and `MUD_TEST_SETTINGS=1` in the file, and the specific changed browser methods through `web.tests.browser.unittest_driver`. Finish with `tools.spec_traceability check`, `tools.contract_gate` and strict OpenSpec validation. Full browser/evidence suites remain CI-owned. Proposal work runs artifact validation only, with no map recovery, generator or game tests.
