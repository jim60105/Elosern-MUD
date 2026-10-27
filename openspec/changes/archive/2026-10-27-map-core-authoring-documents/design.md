# Design

## Context

There is no current map YAML loader. Current graph construction rejects empty graphs, while the approved editor permits loadable unfinished worlds. New codec/model ownership must precede source conversion.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Own schema version 1 and a machine-readable schema in the core. Describe every supported nested field, including prototypes/options, scene references, footprint masks, continent classifier inputs, locations, districts, settlements, coordinate-free interiors and separately typed layout documents. Use ruamel.yaml with YAML 1.2 core scalars, reject aliases/anchors/merge keys/tags/timestamps, duplicate keys before constructing mappings, non-finite values and unsupported types. Integer fields reject bool, numeric strings and fractions; never stringify names or IDs. Bound input bytes/depth/collections before expensive work. Retain source field/line provenance and round-trip trees next to typed values.

Sorted discovery is exactly content/maps/{continent,locations,districts}.yaml plus settlements/*.yaml and interiors/*.yaml. Kind/version/file-stem identity agree, and duplicates/unknown kinds fail the whole authoring load. Layouts at content/map-editor-layouts/*.yaml remain outside world snapshot inputs; partition and reference outputs are never scanned as sources. The codec round-trips readable multiline prose, #/. masks, bends and retained stable-object comments; normalization of whitespace is allowed. Unsupported candidates never authorize a lossy rewrite.

AuthoringWorld holds semantic WIP diagnostics but requires typed complete document structure. RuntimeMapSnapshot is only constructed after map validation, authoritative external validation supplied as explicit data and required artifact freshness. Empty graph, inaccessible landmark, blocked approach and stale partition are saveable diagnostics; duplicate outgoing direction is structural. Route/provider objects are constructed only when their invariants hold. Qualified references use domain/map/object identities. New IDs match [a-z][a-z0-9_]*; existing IDs are retained without rename aliases.

### Exact implementation ownership

packages/map-core schema/codec/discovery/validation; proposed authoring inspection CLI used on synthetic and converted documents; no game source-format cutover in this slice

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Map documents are discovered and schema checked as a complete candidate | packages/map-core/tests/test_authoring.py, test_yaml_codec.py; tests/test_map_authoring_contract.py | Discovery and identity and all negative scenarios in its delta |
| Restricted YAML preserves supported authored information | packages/map-core/tests/test_authoring.py, test_yaml_codec.py; tests/test_map_authoring_contract.py | Unsafe constructs and all negative scenarios in its delta |
| Authoring diagnostics and runtime acceptance have distinct gates | packages/map-core/tests/test_authoring.py, test_yaml_codec.py; tests/test_map_authoring_contract.py | Saveable unfinished world and all negative scenarios in its delta |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Core schema changes serialize with every domain cutover. No temporary Python/YAML fallback reader is introduced.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; cooperative turn-taking deliberately excludes concurrent writers and automatic merge/retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

packages/map-core/tests/test_authoring.py, test_yaml_codec.py; tests/test_map_authoring_contract.py

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

