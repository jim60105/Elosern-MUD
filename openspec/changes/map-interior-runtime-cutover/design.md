# Design

## Context

places.py owns permanent room prose, exterior coordinates and doorway fields. bootstrap.py iterates services and owns special interior links. Active NPC prerequisites now own host/profile/components and goods. All other map source domains have already cut over to YAML.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Convert every permanent interior to content/maps/interiors/<interior_id>.yaml, with stable room identities, names/descriptions, scene references, internal connections and one-owned exterior/interior relationships. Preserve existing place keys as room identities/tags and service joins, including special permanent links formerly hard-coded in bootstrap. Delete duplicate room/exterior/doorway fields from service records and all bootstrap-authored topology. Service/economy/NPC records retain only a qualified room reference plus their non-map fields. A standalone interior requires no service record. Region/node scene associations already moved in earlier source cutovers; remove the final place-scene table here while keeping actual scene/art catalogs game-owned.

Create one explicit game load/adopt entry point over the complete YAML source set. Build AuthoringWorld, perform full core map checks, actual static game registry checks and required partition freshness, then construct RuntimeMapSnapshot and atomically replace the complete composed read-only registry bundle. Never publish a valid subset on failure. Persistent synchronization runs only after candidate preflight under existing world/maps transaction, unsafe deletion, knowledge/reference and observability owners. If publication is tied to a sync failure, keep the prior registry bundle and persistent baseline; restore in-process caches through the existing transaction boundary. No import-time game assembly, generated Python, old-format loader, release migration or re-export shim remains.

Map-facing service location labels are resolved from room values, while service kind/host/goods ownership stays Python. Preserve host identity and direct-capability semantics from the active prerequisites. Every current map caller must use the final bundle or explicit snapshot argument; migrate commands, GM map readers, lore mirroring, presenters, quests, services, gates, district lighting, artwork and offline tools. Generated instances/TTL remain game-owned and never enter static YAML.

### Exact implementation ownership

content/maps/interiors/*.yaml; world/maps/{bootstrap,map_data,room_art}.py and new runtime adapter; world/lore/settlements/{places,places_*,_hosts}.py; world/rules/guild_economy.py; server/conf/at_server_startstop.py; quest/service/art/GM/presenter consumers

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Runtime adoption publishes one complete validated world | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Rejected world and all negative scenarios in its delta |
| Permanent interiors are map-owned independently of services | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Standalone and service interiors and all negative scenarios in its delta |
| settlement-place-registry: A place is the single authored record of one service location | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| settlement-place-registry: A settlement declares its archetype and coordinate space | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| place-driven-service-sync: One place record yields a complete working location | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| place-driven-service-sync: Interiors are created by iterating the place registry | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| room-art-metadata: Room official references are explicit authored keys | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| authored-registry-references: Cached bidirectional integrity model | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |
| sample-city-altoria: The sample city's declared exterior topology remains unchanged while permanent service interiors are attached | world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Qualified references already follows npc-title-authoring-removal, so this change owns the final amendment of settlement-place-registry and place-driven-service-sync, superseding only their geometry/prose/topology ownership. Preserve active NPC component/profile/host reuse contracts. Serialize guild_economy/bootstrap and static checks with NPC synchronization; serialize source/caller contracts and manifests with webclient movement/publication changes.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; cooperative turn-taking deliberately excludes concurrent writers and automatic merge/retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

world/maps/tests/test_interior_sources.py and test_runtime_adoption.py (new); test_bootstrap and test_room_art_metadata; world/rules/tests/test_guild_economy_sync.py, test_service_binding_persistence.py; tests/test_map_runtime_contract.py

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

