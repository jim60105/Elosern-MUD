# Design

## Context

The three domain editors exist. Relationships are settlement- or interior-owned once; source authority forbids manually mirrored reverse declarations.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Implement qualified endpoint selection across location/wilderness/settlement/permanent-interior domains supported by the core schema. Expose settlement wilderness entrances and starting-room entry as settlement-owned tools; expose exterior/interior and special interior-to-interior links in the owning interior. Persist endpoints, each applicable directional label/aliases and explicit one-way/two-way meaning in one record. Show computed current coordinates for spatial endpoints read-only when helpful, never accept an unlabelled coordinate string or display-name target.

Both endpoints are inspectable/navigable with map/domain/qualified ID/source owner. Follow a relationship and retain useful return map/view/selection context. Editing one relationship writes only its owner; a bidirectional meaning is not a second file operation. Do not change Limbo's one-way invariant. Invalid/wrong-domain/absent endpoints identify the relationship and field. Refuse deletion of referenced objects with navigable incoming refs, shown inline in the inspector without a modal (frontend design §5.4); missing/stale context refuses destructive deletion with that reason without blocking placement/property edits. The relationship inspector, 前往另一端, breadcrumb return button/Alt+← and qualified-ID selector follow frontend design §4.4. Removing a reference and later deleting the target are explicit separate complete commands, never a cross-document cascade.

### Exact implementation ownership

frontend qualified selector/entrance inspectors/cross-map navigation; service settlement/interior relationship handlers; existing core reference rules; no new persistent game writer

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Cross-layer relationships edit one owner and expose both meanings | tests/test_map_editor_relationships.py (new); relationship component tests; real browser cross-map navigation/edit/deletion cases | Edit an entrance and all negative scenarios in its delta |
| Deletion requires established absence of incoming static references | tests/test_map_editor_relationships.py (new); relationship component tests; real browser cross-map navigation/edit/deletion cases | Referenced deletion and all negative scenarios in its delta |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Relationship handlers extend settlement/interior domain modules after those slices; serialize these edits and shared selector/navigation modules. No mirrored reverse owner or second deletion validator.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; continuous file following with the fingerprint guard deliberately excludes concurrent-writer merging and automatic retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

tests/test_map_editor_relationships.py (new); relationship component tests; real browser cross-map navigation/edit/deletion cases

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

