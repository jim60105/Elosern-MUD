# Proposal

## Why

A continent-location drag saves `locations.yaml` while the settlement repeats the old world-cell and local-anchor values and retains an absolute wilderness origin. Remove those duplicate authorities so a single saved gesture moves the settlement and its wilderness entrances consistently, including after reload and game adoption.

## What Changes

- **BREAKING** Remove the settlement `binding` object, `BindingDeclaration` and `set_binding` command, including frontend payload builders and inspector fields. Derive the geographic anchor from `locations[location_ref].cell` and the local anchor from the unique `anchor_room` node.
- **BREAKING** Replace `wilderness_entry.origin` with signed integer cell `offset: {dx, dy}` relative to the referenced location. Convert both settlement documents and every consumer in the same cutover, without legacy parsing or migrations.
- Keep location drag as one command/undo entry writing only `locations.yaml`; every node's world metres, mask and approach cell translate by that delta. Keep anchor-node drags settlement-owned, with the location fixed and other nodes' world positions shifted by the negative local-anchor delta.
- Preserve absolute-cell footprint editing APIs. Make midpoint/location disagreement a saveable advisory semantic warning, independent of actual blocking geometry diagnostics.
- Remove binding arguments from settlement creation, retain empty-map WIP behavior, and use a zero-offset point entry when the first wilderness gate is created.
- Extend synthetic process/browser and committed game-adoption tests. Convert the two authored documents with temporary derived-output comparison, then regenerate the partition from final sources.
- Refresh `content/map-reference-context.json` after final core/lore changes and check its freshness, preserving the editor's external-reference and deletion/history gates.
- Update the handoff's developer docs and map-authoring skill recipes. Preserve the user's live location and node edits during implementation recovery; never reuse the partial partition JSON.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-settlement-sources`: derived local/world frame and location-relative wilderness mask ownership.
- `map-editor-geography`: one-document location dragging and absolute-cell footprint edits without binding controls.
- `map-editor-settlement-graphs`: binding-free creation and explicit anchor-node movement semantics.
- `map-runtime-adoption`: occupied anchor and exit preservation when only a location moves.
- `map-authoring-documents`: midpoint mismatch is advisory and does not independently block runtime acceptance.

## Impact

Core schema/documents, references, partition and authoring; editor geography/settlements/relationships/snapshot and minimal frontend caller removal; game map/lore adapters and partition producer; both settlement YAMLs, regenerated partition and reference context; affected fixtures and shard declarations. No new UI controls, multi-document drag writes, topology/prose edits, release bump, compatibility layer or persistent-state migration.

Human review of documentation and the reduced inspector uses `tmp/map-editor-location-move-handoff.md`, `docs/superpowers/specs/2026-10-26-map-editor-design.md`, and `docs/superpowers/specs/2026-10-26-map-editor-frontend-design.md`. Wording and visual polish are human-reviewed rather than tested; executable contracts have behavioral tests.

## Batch:

depends-on: map-core-settlement-diagnostics

Code-conflicts: shared `authoring.py`, game map adapters, core/game/editor fixtures, the skill checker, generated reference context and map docs require serial application after the prerequisite. Both changes modify the same existing authoring-gates requirement; this delta contains its complete post-prerequisite form.

## Scope and evidence boundary

One engineer-day for the coordinated schema/caller conversion and focused regression coverage, after shared diagnostics land. Handoff criteria 1, 2 and 4-8 belong here; criterion 3 is rechecked against the new schema. For unchanged geography, derived geometry bytes and partition payload must equal the committed baseline. Raw source fingerprints necessarily change on conversion, so the partition's source-signature metadata must refresh; whole-file partition byte equality cannot coexist with the existing freshness contract.

## Confirmed recovery decision

The user confirmed that Ciaran stays at `(1366, 554)`. Keep Fionnen at `(1465, 1237)` and retain the Ciaran node edits. Carry the committed location-relative offset of the centered Ciaran point entry into the converted document; do not derive an offset from its stale absolute origin. Recompute the local anchor from the edited anchor node and regenerate the whole partition from final YAML, never from the partial dirty JSON. Do not apply or drop a stash. Require clean core map diagnostics at the chosen cell before final adoption; a genuine terrain/collision failure requires user input rather than an invented replacement cell. Planning leaves the three dirty files untouched.
