# Design

## Context

The service owns guarded manual writes and history. External OMP writes the same files but is started/stopped outside the editor; filesystem silence cannot establish process state.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Use service states inspection, manual, handoff_pending, external, return_pending and paused. Every source/layout/history/generated-output mutation route checks service session/turn/state; UI disabled controls are additional presentation only. Startup/reconnect/restart inspect fresh disk and require explicit manual resume. A service restart creates a new session generation and rejects old tabs/requests. Never restore mutation permission or replay accepted/pending commands from browser storage.

Handoff resolves current drafts by explicit confirm/cancel, closes admission, drains already-admitted saves and flushes before granting external ownership. Failure retains a visible failed/paused manual recovery state and never grants the external turn. History clears at successful handoff. During external turn keep browsing/search/select/inspect/context-copy/viewport/layers useful. Return requires the user to confirm the external writer stopped, rereads actual disk and applies authoring-load gate; it never serializes the pre-AI snapshot. Loadable semantic WIP can resume repair, structural failure stays read-only for external repair.

watchfiles watches directories for create/replace/rename/delete, including newly created documents and layouts. Coalesce briefly, read a coherent candidate and publish only on authoring success; a debounce is no multi-file transaction. Keep the previous preview and view on malformed candidates, label its inspector as stale and expose source file/field/line. With no prior preview show unavailable, never a valid-looking empty world. External index changes invalidate external-check status too. Unexpected manual-mode file changes immediately pause new writes; require explicit reload acknowledging draft/history discard, without merge/diff/replay. Preserve current map/viewport/selection by qualified identity on valid external reload; clear deleted selections with an explanation.

Treat a directory notification as expected service output only when freshly read presence/content matches the writer's committed fingerprint ledger, including expected absence after removal. Reconcile delayed/coalesced notifications against current disk and the latest committed state; never suppress an event just because its path was recently saved. Expected service notifications retain manual ownership and undo history. A differing external fingerprint pauses writes even when it immediately follows a service save at the same path. Test two ordinary saves with real delayed watcher delivery, then a real external replacement at that path.

Observe the external context source closure as invalidation input where available, and independently refresh its full membership/hash evidence before every destructive command. An unchanged exported index file alone cannot establish freshness.

### Exact implementation ownership

elosern_map_editor session state machine/watch coordinator/SSE; frontend connection/preview/turn state and handoff dialogs; all mutation guards; independent real-filesystem tests

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Handoff grants one cooperative writer after persistence | tests/test_map_editor_turns.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class | Flush failure and all negative scenarios in its delta |
| External return adopts loadable disk state without rewriting history | tests/test_map_editor_turns.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class | Semantic repair and all negative scenarios in its delta |
| Watching and reconnect retain truthful preview state | tests/test_map_editor_turns.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class | Real filesystem replacement and all negative scenarios in its delta |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Sequence after writer integration. Generation later adds a state guard to this same state machine; no second watcher, session owner or merge protocol.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; cooperative turn-taking deliberately excludes concurrent writers and automatic merge/retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

tests/test_map_editor_turns.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

