# Design

## Context

See `proposal.md` for motivation. `load_authoring_world` already separates schema/structure rejection from saveable semantic diagnostics. `compile_runtime` rejects semantic map failures. Additional checks live in `map_data._compose_document`, `validate_wilderness_entries`, `interiors._validate` and the skill checker's `game_rules`. The game adapters currently raise text exceptions rather than providing a separate diagnostic-category taxonomy.

The approved engine design keeps persistent writes in `world/maps/`; the approved editor design §6.1 requires a shared map-rule implementation, and §7.1 permits one document per operation. This slice does not alter writer/history behavior or the current settlement schema.

## Goals / Non-Goals

**Goals:** one framework-neutral implementation for the former game-only settlement/interior rules, with explicit category parity between authoring and game rejection. Preserve all existing wilderness rejection cases and empty-map editing.

**Non-Goals:** changing terrain rules, adding new geography/district policies, removing binding fields early, repairing live data, changing lore/service/scene/quest checks, UI redesign or compatibility facades.

## Decisions

### D1. Extract rules into candidate-scoped core diagnostics

Add core diagnostic functions in `elosern_map_core/authoring.py`, taking candidate documents, locations, frame and terrain inputs explicitly. Reuse core mask, reference, terrain and gate-approach calculations. Aggregate stable codes in deterministic order, with `relative_path`, `field_path` and object identity; cross-owner collisions identify both owners in the diagnostic message. Do not import game modules, registries or ORM state.

Invoke these functions from authoring structure/semantic phases and from game candidate construction. Partial-domain builders may call the same functions with their explicitly available domain inputs; they must not substitute published terrain or assume every cell is walkable to claim full readiness. Full adoption checks the complete candidate before composition can publish anything. Startup lore mirroring validates the candidate through this shared boundary before persistence.

Remove the game-local `validate_wilderness_entries` rule implementation and migrate its callers in `world/maps/map_data.py`, `geography.py` and `world/lore/sync.py`. Remove obsolete validator tests or move their independent cases to core tests; retain game boundary tests establishing rejected adoption/mirroring. Keep runtime geometry carriers and traversal helpers that have real consumers. Remove duplicate map checks from `interiors._validate`, retaining composition and genuine external checks. Delete corresponding skill `game_rules` branches; the script consumes core diagnostics and retains its unrelated external/district checks.

Alternative rejected: copy the skill checks into the editor. It retains multiple authorities and would miss hand-authored and game-consumed candidates.

### D2. Category and rejection matrix

The game consumes these core categories without recategorizing them. Existing schema errors keep their current category/code; proposed names below are stable codes for newly shared rules. A zero-gate sequence already fails schema bounds and remains a structure error. Do not duplicate schema diagnostics.

| Rule / proposed code | Authoring category and effect | Game effect |
| --- | --- | --- |
| Missing anchor, including an empty/new graph / `missing_anchor_room` | Semantic WIP; saved document stays editable | Reject |
| Multiple anchor nodes / `multiple_anchor_rooms` | Structure; reject mutation/load | Reject |
| Anchor key differs from location_ref / `anchor_location_mismatch` | Structure | Reject |
| Two settlements bind one location / `duplicate_location_binding` | Structure | Reject |
| Duplicate interior room ID / `duplicate_interior_room` | Structure; identify both documents | Reject |
| Duplicate doorway key at `(settlement,node)` / `duplicate_doorway` | Structure | Reject |
| Gate destinations duplicate one room / `duplicate_gate_destination` | Structure; one exit slot per room | Reject |
| Disconnected non-point mask / `disconnected_footprint` | Semantic WIP | Reject |
| Non-point midpoint is not a hash / `invalid_footprint_anchor` | Semantic WIP | Reject |
| Mask hash cell outside frame or impassable / `invalid_footprint_cell` | Semantic WIP, including point mask hash cells | Reject |
| Footprint overlaps footprint or contains another point / `overlapping_footprint` | Semantic WIP | Reject |
| Point mask has multiple gates / `point_gate_count` | Semantic WIP | Reject |
| Approach ray undefined or leaves frame / `invalid_gate_approach` | Semantic WIP | Reject |
| Approach terrain blocked / existing `blocked_approach` | Semantic WIP | Reject |
| Approach inside another footprint or equal to another point / `gate_approach_collision` | Semantic WIP | Reject |
| Duplicate `(approach,direction)` / `duplicate_gate_approach` | Semantic WIP | Reject |
| Point entry's authored-direction neighbor invalid / `blocked_point_neighbor` | Semantic WIP | Reject |

Mask grammar, valid directions, duplicate directions, known destination nodes, references and existing road rules remain core schema/structure checks. Point masks own no obstacle cells but still have hash/anchor terrain and collision checks. Preserve the distinction in all global comparisons. A missing anchor produces unavailable placement/world-geometry projections, never an invented `(0,0)` binding. Multiple anchors are rejected before selecting one.

Binding coordinate equalities remain existing game-only checks for this bounded intermediate slice. The dependent change deletes the fields and checks together. Adding a temporary equality requirement here would make a normal location drag fail authoring before that cutover and introduce a soon-retired contract.

### D3. Requirement and test mapping

All deltas modify existing requirement headings, retaining canonical IDs. IDs below were obtained from `tools.spec_traceability list`; do not invent new IDs. Annotate discoverable tests with `covers_requirement` imported from `tools.spec_traceability` and retain only claims their assertions establish.

| Requirement ID | Discoverable evidence to extend | Assertions |
| --- | --- | --- |
| `map-authoring-documents::authoring-diagnostics-and-runtime-acceptance-have-distinct-gates` | `packages/map-core/tests/test_authoring.py`; `tests/test_map_authoring_contract.py`; `world/maps/tests/test_settlement_sources.py` and `test_interior_sources.py` | Independent fault per matrix row; expected code/category/owner; editable missing-anchor WIP; invalid structures refused; game rejects through shared rule and preserves publication |
| `wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence` | Existing `world/lore/tests/test_wilderness_entry.py` boundary coverage, migrated pure cases in core tests, and `tests/test_map_authoring_contract.py` | Same malformed masks, frame/terrain faults, point/gate collisions and valid controls; no lore records on failure; checker/core decision agreement |

Use synthetic sources for mechanics. A single parameterized agreement test may iterate the matrix, with one independently invalid world per case and a valid control. Do not let an earlier defect, absent external context or stale partition satisfy the expected rejection. Where schema makes a defect unrepresentable, assert its schema diagnostic rather than attempting to fabricate an accepted world. Core tests alone do not establish the game delegation boundary, so include game composition and lore-mirroring assertions.

Update shard manifests only if new test modules/classes/methods require it. Existing module extension avoids unnecessary shard changes. Run `tools.spec_traceability check` before implementation handoff and after eventual spec synchronization; these are existing IDs.

### D4. Documentation and review

Update `docs/development/map-authoring-documents.md` validation ownership and `.agents/skills/map-data-authoring/SKILL.md`'s invariant table and check descriptions. Mark moved rules core-owned; retain binding repair advice until the next change removes those fields. Update skill `scripts/check_map_sources.py` with the delegation. Human reviewers use `tmp/map-editor-location-move-handoff.md` and `docs/superpowers/specs/2026-10-26-map-editor-design.md` to review completeness and prose. No new requirement pins a document's wording or a shipped-data roster.

### D5. Refresh the external-reference context with each slice

`tools/map_reference_context.py` discovers and hashes `packages/map-core/elosern_map_core/**/*.py` and `world/lore/**/*.py`, including files changed here. Coordinate-only edits do not invalidate that context, but implementation edits do. Regenerate and commit `content/map-reference-context.json` after this slice's final core/lore changes, then run `uv run --locked python -m tools.map_reference_context --check`. The dependent change regenerates it again after its own code cutover. Do not remove dependencies or weaken freshness checks to avoid regeneration.

The exporter bootstraps through `runtime.compose()` and has no source-root CLI argument. The protected live reproduction still violates binding equalities at this intermediate stage. Generate/check in a temporary repository copy containing this slice's final implementation and valid committed pre-change authored geography; run the module from that copy so module `__file__` roots and imports agree. Do not restore files over the user's sources. Copy back only the generated reference-context artifact and verify its source manifest matches the actual changed core/lore code; editable map YAML is excluded from that manifest. Use the same valid copy for the broader contract gate while the root remains the unresolved reproduction. Its result is evidence for the isolated candidate, never a claim that the dirty live world was adopted.

This necessary generated index is the only artifact refresh in this slice. The partition remains untouched. Existing reference-context freshness/deletion tests establish the unchanged mechanism; no new data-pinning requirement is introduced.

## Risks / Trade-offs

- Game validation previously short-circuits while core aggregates. Mitigation: deterministic codes and independently invalid inputs prevent message-order coupling.
- Global gate checks can be lost during extraction. Mitigation: include collisions between entries, point entries and shared destination rooms in the agreement matrix.
- Rejecting all zero-anchor maps would break creation. Mitigation: missing anchor remains semantic WIP and renderers show geometry as unavailable until an anchor exists.
- The user's current worktree is already inconsistent. Mitigation: do not edit or use it as a valid baseline; tests use temporary synthetic candidates. Recovery belongs to the dependent change.

## Migration Plan

No data or compatibility migration. Land shared rules, switch every game/checker caller, delete the former implementations and refresh the generated reference context in the same implementation change. No schema or authored sources change here. Rollback is a normal source change before release, with no persisted map-state conversion.

## Verification plan

During implementation, run the focused core authoring tests, `tests.test_map_authoring_contract`, affected settlement/interior/lore game tests with the guarded Evennia env-file command, the skill checker on an independently valid workspace, reference-context generation/check and `tools.contract_gate` in the valid isolated candidate described in D5, and `openspec validate map-core-settlement-diagnostics --strict`. An expected error from the live reproduction is not a successful world-validation claim. Proposal creation runs only OpenSpec artifact validation.
