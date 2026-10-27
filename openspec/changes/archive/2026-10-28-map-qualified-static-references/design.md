# Design

## Context

city_gates.py stores gate_xyz; places.py stores exterior_xy; map_districts.py stores grid wire IDs; room_art.py maps coordinates. Quest/presenter adapters derive grid and room wire identities. Active NPC proposals also edit places and their host contracts.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Use core qualified references at every authored static map-target boundary. Settlement node identity remains existing NODE_IDS; permanent room identity remains the existing place key. Introduce no coordinate-to-ID alias table as a runtime fallback. Convert existing gates, placement anchors, wilderness entry endpoints, place exterior targets, interior links, district settlement landmarks, static quest/service targets and grid art associations together. Wilderness cell references remain explicitly typed cells; game wire IDs stay coordinate/dbref based at their existing boundaries. Keep these domains' current Python source ownership until their own YAML cutover, never duplicate a declaration in two formats.

Adapters resolve references through the current validated graph into locator/scene/knowledge/runtime forms. Move a node once and resolve all families at the new coordinate without editing targets. Runtime coordinate synchronization still uses existing stable node tags, reference/knowledge owners and transactions; no stored-save migration or shim. This change follows the final active NPC title/direct-capability cutover; preserve its canonical profile identity, per-component bindings, zero-capability and hostless cases. Do not restore profession expansion, titles or old host recreation semantics.

### Exact implementation ownership

world/maps/{city_gates,room_art,bootstrap}.py; world/lore/{anchor_placement,wilderness_entry,map_districts}.py; world/lore/settlements/places*.py and _hosts.py; static quest/service declarations; web/webclient/presentation/map_quest_destinations.py; scene-address/locator adapters

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Static references resolve by authored identity | world/maps/tests/test_static_map_references.py (new); existing test_bootstrap, test_room_art_metadata; world/rules/tests/test_map_knowledge.py and map quest destination tests; synthetic factories | Identity movement and all negative scenarios in its delta |
| map-districts: Every map district has one canonical reachable landmark | world/maps/tests/test_static_map_references.py (new); existing test_bootstrap, test_room_art_metadata; world/rules/tests/test_map_knowledge.py and map quest destination tests; synthetic factories | Retain unaffected scenario effects; establish new source/identity/gate behavior, not incidental source text |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Hard dependency on npc-title-authoring-removal (transitively direct-capability-declarations, host-identity and plain-name); this resolves overlapping place edits and their settlement-place-registry deltas. Serialize bootstrap/exit/presenter and knowledge-test edits with webclient-movement-alignment, without changing settlement receipts or publication ownership.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; cooperative turn-taking deliberately excludes concurrent writers and automatic merge/retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

world/maps/tests/test_static_map_references.py (new); existing test_bootstrap, test_room_art_metadata; world/rules/tests/test_map_knowledge.py and map quest destination tests; synthetic factories

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

