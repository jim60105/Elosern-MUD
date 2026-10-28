# Design

## Context

Core generation is independent; the editor service owns session permission and atomic artifact writer boundaries. The standalone generation extra must be installed independently.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Install the core generation extra in the editor project lock without root game dependencies. A service-owned single job runner executes generation outside HTTP/SSE event loop, taking a captured snapshot/input signature. Only one job is admitted at a time. During generation reject all world-data mutations at service admission while keeping browse/inspect/viewport/status/cancel useful; there is no handoff to block (frontend design D3). Layout-only commands may remain allowed through the existing single-document guard since they cannot change generation input; document that distinction rather than silently disabling browsing. A write pause or stale preview also refuses publication.

Cancel/failure leaves the prior artifact unchanged. External file notifications invalidate captured inputs; before output publication, recheck the session, write pause and the full current source signature, then use the existing confined atomic artifact replacement path. An invalidated result is rejected and never labelled current. No ordinary drag/game action triggers regeneration. Expose current/stale/generating/cancelled/failed status through the header 分區 chip (regenerate when stale, cancel while generating), the represented input revision and actionable diagnostics. Old partition geometry may remain inspectable only with persistent older-input labels; source saved state is separate from output freshness. Cancellation after publication has already completed is reported as completed, never promises rollback of a replaced artifact.

### Exact implementation ownership

editor background job runner/status routes and partition frontend controls; editor uv generation extra; existing session mutation guard and artifact writer

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Explicit generation isolates inputs and guards publication | tests/test_map_editor_generation.py (new); independent job tests with real small generation inputs; focused browser partition state/cancel/stale case | Changed source and all negative scenarios in its delta |
| Partition status distinguishes source persistence from output freshness | tests/test_map_editor_generation.py (new); independent job tests with real small generation inputs; focused browser partition state/cancel/stale case | Old output and all negative scenarios in its delta |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Extends the same state machine/writer from workspace slices; serialize those files rather than add a job-specific mutation authority. Partition artifact remains generated/read-only.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; continuous file following with the fingerprint guard deliberately excludes concurrent-writer merging and automatic retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

tests/test_map_editor_generation.py (new); independent job tests with real small generation inputs; focused browser partition state/cancel/stale case

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

