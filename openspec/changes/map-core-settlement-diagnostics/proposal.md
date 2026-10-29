# Proposal

## Why

The map editor accepts settlement edits that the game rejects because settlement and interior rejection rules remain in game adapters and a skill checker. This first one-day change makes those rules core diagnostics so editor reload and game adoption use the same decision before the placement-schema cutover.

## What Changes

- Move settlement anchor, footprint/gate and interior-identity checks into framework-neutral `elosern_map_core/authoring.py`, with deterministic diagnostic codes, source fields and the existing structure/semantic categories.
- Keep empty maps saveable as unfinished work; block invalid identities/references and diagnose terrain or accessibility failures without claiming game readiness.
- Route game composition, startup lore synchronization and the map-authoring checker through those core rules. Delete their duplicate rule implementations.
- Cover each former game-only rejection with an independently invalid synthetic world and a core-versus-game agreement test. The current binding equalities remain game checks until the dependent change removes their fields; this slice does not add a temporary equality requirement or prevent the eventual one-document drag.
- Update the developer validation documentation and skill invariant table to distinguish core-owned rules from remaining external checks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-authoring-documents`: shared settlement/interior diagnostic categories and acceptance gates.
- `wilderness-gateway`: pre-persistence map validation is core-owned, with unchanged gate and point-entry rejection semantics.

## Impact

Touches map-core authoring/tests, `world/maps/map_data.py`, `geography.py`, `interiors.py`, `runtime.py`, `world/lore/wilderness_entry.py` and `sync.py`, the skill checker and validation documentation. No schema/content conversion, editor UI, dependencies, persistent-state migration or generated-artifact writes belong to this slice. The engine's deterministic ownership and map-editor design §7.1 stay intact.

Documentation clarity is human-reviewed against `tmp/map-editor-location-move-handoff.md` and the map-editor architectural design; tests establish the mechanisms, without asserting documentation wording.

## Batch:

depends-on: none

Code-conflicts: `map-location-relative-placement` shares core authoring/geometry consumers, game map composition, the skill checker, fixtures and map documentation. Land this change first; the dependent change consumes the shared diagnostics and removes the obsolete equality checks. Do not apply these changes concurrently.

## Scope and review

One engineer-day, bounded to extracting existing rejection mechanisms and their tests. Acceptance criterion 3 from the handoff belongs here; the dependent change completes criteria 1, 2 and 4-8. This change alone does not repair the drag bug. Proposal work never edits the user's three dirty data files.
