# Design

## Context

The independent browser and service state exist. The companion frontend brief fixes information/actions/state and accessibility acceptance, while leaving panel arrangement/theme to a subsequent specialist.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

At apply time first commission a frontend/UX visual specialist using the complete companion brief and these concrete service contracts. Deliver annotated continental/settlement/interior and cross-layer designs, content hierarchy/navigation model, component/state specifications, focus/keyboard behavior, all failure states, primary 1280x800/1920x1080 and compact 960x720 layouts, and 200% zoom disclosure. Record decisions and acceptance-scenario mapping in docs/design/map-editor-review.md. This is a mandatory specialist deliverable, not authorization to remove functional tools. Tone, wording quality and visual polish/fidelity are human-reviewed in that document, never requirements established by snapshot/copy/count pins. The current user request authorizes proposals only; it does not declare this specialist work or implementation approved/completed.

Implement shared workspace chrome against service snapshots without choosing a competing domain schema. Provide workspace identity, connection/current turn, draft/in-flight/saved/failed/uncertain state and persistent preview/currentness/index/partition status before a preview can be mistaken for saved. Add domain/map navigation, location-to-map and return context, source owner, search disambiguation with parent/source, readable/copyable IDs and paths. Selection supports none/single/multi and a keyboard/text list alternative; mixed/cross-owner selections inspect but cannot batch mutate.

Diagnostics distinguish structure, semantic WIP, invalid/unavailable external context, stale partition and service/save failure. Locate target objects and reveal/offer hidden layers; source-only parse errors show file/line without a source editor. List incoming/outgoing relationships. Copy OMP context is plain text containing relative paths, domain/map/qualified IDs, units/currentness, ownership and save-before/stop-before-return agreement. It leaks no token/credential/history and starts no task. No selection-file or AI-control protocol.

Use Traditional Chinese interface copy, English IDs and technical units. Desktop Chromium/Firefox, mouse/keyboard, WCAG 2.2 AA, visible focus, non-color distinctions and drag alternatives are required. Scope platform-aware save/undo/redo/Escape shortcuts outside text input; input undo/delete stays local. Field failures restore field focus, closing a dialog restores its trigger, and diagnostics/cross-map navigation retains return context. Confirm only meaningful destructive transitions; disabled actions expose reasons. No game shell styles, chat/source/model/Git/diff/live-state surfaces.

### Exact implementation ownership

editor frontend workspace/navigation/inspection/diagnostics/clipboard/focus modules; docs/design/map-editor-review.md (future specialist deliverable); no game shell imports

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Workspace navigation and diagnostics identify source context | editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/compact/zoom behavior and traceability | Duplicate name and hidden target and all negative scenarios in its delta |
| Selection context is a copy-only external bridge | editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/compact/zoom behavior and traceability | Stale multi-selection and all negative scenarios in its delta |
| Essential workspace operations have keyboard and reflow access | editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/compact/zoom behavior and traceability | Keyboard and focus and all negative scenarios in its delta |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Frontend shell/focus modules are shared with domain editors; keep commands/tools in domain-owned modules. The visual specialist is an apply-time deliverable and never replaces any approved functional requirement.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; cooperative turn-taking deliberately excludes concurrent writers and automatic merge/retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/compact/zoom behavior and traceability

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

