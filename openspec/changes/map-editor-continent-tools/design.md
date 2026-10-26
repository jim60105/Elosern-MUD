# Design

## Context

Continent, locations, districts and settlement footprint/binding sources are YAML. Core terrain and diagnostics are shared. Explicit partition publication is supplied by the later generation slice.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Implement domain modules and named one-document commands for all continent supported geometry: mainland boundary vertices, waterways, forest/terrain boundaries, ridge parameters, passes/fords, region prose/classifier fields and reserved geographic sites. Provide select/add/remove/move vertex/control-point tools and labelled numeric alternatives; separate feature selection from point selection. Recompute geometric/terrain previews through core calculations using current authoring inputs, without running heavy partition generation. Derived national/district boundaries have no editable handles. Unit labels distinguish cell indices, kilometre geometry and metre values.

Locations support create/select/name/description/kind/place/inspect/search even with no local map. IDs are generated/new and confirmed against schema; established IDs cannot be renamed. Navigate to local maps only when settlement location_ref derives one; otherwise show absence. Creating a location and its map are separate completed commands. District editor supports all names/kinds/region membership/stable landmark selectors and WIP reachability diagnostics. Footprint cell-paint/mask controls and an explicit per-cell alternative write only the owning settlement; binding inspector/editor labels local/world anchors without assigning interior metres. All changes route through guarded writer; cross-document cascades remain excluded. Deletion follows current map incoming refs plus current external context absence and explains dependents, with no cascade.

An ordinary geography commit marks dependent partition output stale; do not regenerate per pointer move. Keep old output labelled with its input revision. Every continental surface uses read-only behavior in external/paused/generation state and keeps browse/layer/selection/context useful.

### Exact implementation ownership

frontend geography/location/district/footprint/binding tools and inspectors; service geography command handlers; core terrain-preview endpoint; no second schema or classifier

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Continental authored inputs have direct and explicit editing controls | editor component tests; tests/test_map_editor_geography.py (new service mechanism evidence); standalone browser geography workflows | Move river point and all negative scenarios in its delta |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Geography handlers own separate service/frontend modules; footprint writes intentionally share settlement document serialization with settlement tools. No simultaneous same-document command writers.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; cooperative turn-taking deliberately excludes concurrent writers and automatic merge/retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

editor component tests; tests/test_map_editor_geography.py (new service mechanism evidence); standalone browser geography workflows

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

