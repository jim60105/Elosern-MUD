# Design

## Context

map_data.py currently assembles altoria_capital.py and village_ciaran.py at import. NODE_IDS/ROADS/PROTOTYPES/XYMAP_DATA, anchor_placement, LOCAL_FRAME_ANCHOR_REGISTRY, wilderness_entry and city_gates still own authored settlement data.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Move all authored settlements, not a sample, to content/maps/settlements/<map_id>.yaml. Each owns location_ref, binding, nodes/prototypes, directed roads with explicit direction/bends/options/exit prototypes, footprint, wilderness entry gates, starting-room entry and node scene/art associations. Remove Python authored map modules/rosters and competing placement/footprint/gate/art tables. Read-only game views are composed from validated values as domain contracts, with no compatibility re-exports.

Derive location-to-local-map navigation from location_ref. A new local map for an existing location changes only its new settlement document; do not author a reverse location list. Entrance records store both endpoints/labels once. Runtime adapter resolution retains concealed point entries and irregular footprints, outward approaches, one-way Limbo entry/pruning, CostedXYZExit and idempotent identity-preserving persistent sync. Preserve exact current direction choices during conversion rather than recomputing compass directions from metric deltas. Replace map_data import-time global assembly with explicit candidate load and immutable publication for the settlement domain. Complete all game/contrib, command, presenter, route, test-factory and lore mirror callers in this change; no Python-map path remains.

### Exact implementation ownership

content/maps/settlements/*.yaml; world/maps/{map_data,altoria_capital,village_ciaran,bootstrap,city_gates,room_art}.py; world/lore/{anchor_placement,anchors,wilderness_entry,sync}.py; typeclasses/exits.py; grid provider/route/knowledge/presenter consumers

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Settlement documents own complete local map declarations | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Discover another local map and all negative scenarios in its delta |
| anchor-placement: AnchorPlacement is a frozen dataclass separate from Anchor | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| anchor-placement: Every placement's anchor_key resolves against ANCHOR_REGISTRY | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| anchor-placement: ANCHOR_PLACEMENT_REGISTRY is intentionally partial | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| limbo-one-way-gates: The city-gate registry is the sole authored source of 虛境 city gates | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| limbo-one-way-gates: Adding a city means adding a registry row, with no bootstrap code change | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| wilderness-gateway: WILDERNESS_ENTRY_REGISTRY links a grid-placed anchor to an authored wilderness footprint and gates | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| sample-city-altoria: The sample city has the declared rooms in a connected sparse topology | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| sample-city-altoria: The sample city's declared intra-city exits spawn as CostedXYZExit | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| sample-city-altoria: Altoria uses approved metric outdoor positions | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| village-ciaran-map: The village is a small connected grid with one anchor | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| village-ciaran-map: Ciaran uses metric skylit underground geography | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| grid-room-sync: sync_grid() is idempotent across repeated calls and server starts | world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Follows qualified references to avoid half-migrated targets. Serialize bootstrap, lore sync, source-contract tests and manifests with interiors/districts; preserve active webclient movement and settlement publication facts.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; cooperative turn-taking deliberately excludes concurrent writers and automatic merge/retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

world/maps/tests/test_settlement_sources.py (new); test_bootstrap, test_sparse_graph, test_city_movement_cost; world/lore/tests/test_wilderness_entry.py; tests/test_map_settlement_contract.py

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

