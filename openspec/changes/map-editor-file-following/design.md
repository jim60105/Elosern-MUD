# Design

## Context

The service owns guarded manual writes and history. External OMP writes the same files but is started/stopped outside the editor; filesystem silence cannot establish process state. The approved frontend design (`docs/superpowers/specs/2026-10-26-map-editor-frontend-design.md` D3, §1.1) removes the explicit handoff: manual and AI editing alternate routinely, the operator knows when OMP was asked to act, and the document fingerprint guard is the only overwrite protection.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

There is no turn state machine, ownership state, handoff, external turn or return action, and no resume/handoff/return route. The service has two orthogonal conditions besides normal operation: a write pause and a stale preview. Every source/layout/history/generated-output mutation route checks the launch token, session generation, write pause, stale preview and the target document's expected fingerprint; the frontend does not pre-disable controls per state (design D4) and shows the service rejection in the priority banner.

watchfiles watches the source, layout and artifact roots for create/replace/rename/delete, including newly created documents and layouts. Coalesce briefly, read a coherent candidate and publish only on authoring-load success; a debounce is no multi-file transaction.

Treat a directory notification as the service's own output only when freshly read presence/content matches the writer's committed fingerprint ledger, including expected absence after removal. Reconcile delayed/coalesced notifications against current disk and the latest committed state; never suppress an event just because its path was recently saved. Own notifications keep undo history.

A differing external fingerprint whose candidate loads is adopted automatically as the new snapshot: clear the undo/redo history (it covers only the uninterrupted manual segment since the last adopted external change), preserve current map/viewport/selection by qualified identity and clear deleted selections with an explanation. Semantic work-in-progress simply loads with its diagnostics. If the client holds an uncommitted field draft, it does not adopt silently: it shows the "file changed externally" banner naming the document and the draft/history that will be discarded, and adopts only on the explicit 載入新版 action. A draft submitted against the old snapshot is rejected by the fingerprint guard.

A candidate that does not load keeps the previous preview and view, labels the snapshot and its inspector as stale, exposes source file/field/line and rejects world-data and layout writes until a loadable candidate is adopted; recovery is automatic on the next loadable change, never a rewrite of external files. With no prior preview show unavailable, never a valid-looking empty world. External index changes invalidate external-check status too.

A service start or restart creates a new session generation and invalidates the launch token; a tab from an old session is rejected and must reconnect and reread before any write. Startup reads current disk and is immediately writable when the world loads. Uncertain post-replacement durability sets the write pause until an explicit reread. Never restore write permission or replay accepted/pending commands from browser storage.

The remaining race is documented, not hidden: if OMP and the editor write the same document within one settle interval, the guard rejects the editor's write and the editor reloads; the operator is responsible for not editing in both places at once. The editor never labels OMP as running or finished.

Observe the external context source closure as invalidation input where available, and independently refresh its full membership/hash evidence before every destructive command. An unchanged exported index file alone cannot establish freshness.

### Exact implementation ownership

elosern_map_editor watch coordinator/write-pause state/SSE; frontend connection/preview state, priority banner conditions and draft-held adoption; all mutation guards; independent real-filesystem tests

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| External changes are followed without overwriting them | tests/test_map_editor_file_following.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class | Loadable external change and all negative scenarios in its delta |
| Watching and reconnect retain truthful preview state | tests/test_map_editor_file_following.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class | Real filesystem replacement and all negative scenarios in its delta |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Sequence after writer integration. Generation later adds its mutation guard beside this write-pause state; no second watcher, session owner, turn state machine or merge protocol.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; continuous file following with the fingerprint guard deliberately excludes concurrent-writer merging and automatic retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

tests/test_map_editor_file_following.py, test_map_editor_watching.py (new discoverable wrappers); standalone service tests; focused standalone browser recovery class

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

