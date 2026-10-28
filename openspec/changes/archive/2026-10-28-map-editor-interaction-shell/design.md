# Design

## Context

The independent browser and service state exist. The companion frontend brief fixes information/actions/state and accessibility acceptance; the approved frontend design fixes panel arrangement, theme, state presentation and the keyboard contract.

Observed repository evidence came from root-correct CodeGraph queries and current main/active specs, not an archive-only contract. See proposal.md for authorization and scope.

## Goals / Non-Goals

Deliver this prerequisite-bounded slice completely. Preserve the architectural D9 map-only amendment and deterministic subsystem ownership. Keep external AI execution outside the editor and non-map lore outside YAML. All other approved editor capabilities remain mandatory in dependent changes; this slice does not redefine the product as a viewer.

## Decisions

Implement the approved frontend specialist deliverable, `docs/superpowers/specs/2026-10-26-map-editor-frontend-design.md`, with the `docs/design/map-editor/` Storybook prototype (`Design/MapEditor`) as the visual reference. The specialist design is complete and approved; this slice does not commission another one. Record the per-scenario fidelity check in `docs/design/map-editor-review.md` (one row per design §8 scenario with its disposition). Tone, wording quality and visual polish are human-reviewed there, never requirements established by snapshot/copy/count pins.

Layout and visual language follow design §2-§3: the three-column workbench (navigation, canvas, inspector) with the diagnostics strip, the map-drawer-style header with domain pill tabs on keys 1/2/3, the game's ink-night tokens, serif gold headings, gold focus and seal red reserved for errors. Use only the allowlisted game tokens/fonts/ui-scale (map-editor-standalone-service). Support 1451x790 and 2560x1440 with the game's `--ui-scale` and 16 px floor; at 200 % zoom or when both side columns cannot fit, the columns become header-toggled drawers.

Implement shared workspace chrome against service snapshots without choosing a competing domain schema. Workspace state is the four header status chips (save, file sync, index, partition; design §5.1) plus one priority banner showing the single highest-priority condition with its one action (design §5.2: disconnected, save failed/uncertain, external change held by a draft, stale preview). There is no turn, ownership or handoff indicator (design D3). The frontend does not pre-disable controls per state (design D4); service rejections appear in the banner slot. Add domain/map navigation, location-to-map and return context (breadcrumb return button and Alt+←), source owner, search disambiguation with parent/source, readable/copyable IDs and paths. Selection supports none/single/multi and the object list as the keyboard/text alternative; mixed/cross-owner selections inspect/copy only, with the reason shown in place of mutation actions.

Diagnostics distinguish structure, semantic WIP, invalid/unavailable external context, stale partition and service/save failure. Locate target objects and offer 顯示圖層並前往 for hidden layers; source-only parse errors show file/line without a source editor. List incoming/outgoing relationships. Copy OMP context is plain text containing relative paths, domain/map/qualified IDs, coordinate frames/units and whether it came from current files or a stale preview. It states no turn ownership or handoff agreement, leaks no token/credential/history and starts no task. No selection-file or AI-control protocol.

Use Traditional Chinese interface copy, English IDs and technical units. Desktop Chromium/Firefox, mouse/keyboard, WCAG 2.2 AA, visible focus, non-color distinctions and drag alternatives are required. Implement the keyboard contract of design §6: F6 region cycling, 1/2/3 domains, tool keys, canvas arrow-key object walking with Enter into the inspector, Shift+arrow nudging, platform-aware undo/redo, Ctrl/⌘+C context copy, Delete, ordered Escape cancellation, Alt+← return and / or Ctrl/⌘+K search. Single-key shortcuts never act in text inputs, selectors or IME composition; input undo/delete stays local. Field failures keep field focus, closing a drawer or selector restores its trigger, and diagnostics/cross-map navigation keeps return context. No editor operation uses a confirmation dialog (design §5.4). No game shell styles, chat/source/model/Git/diff/live-state surfaces.

### Exact implementation ownership

editor frontend workspace/navigation/inspection/diagnostics/clipboard/focus modules; docs/design/map-editor-review.md (per-scenario fidelity review of the approved design); no game shell imports

Use worker-contract.md for fixed producer/consumer interfaces and command ordering. All paths not present today are proposed additions, not observed implementations. No open product decisions are delegated to the implementation worker.

### Requirement-to-evidence plan

| Requirement | Discoverable test owners | Observable defect/effect |
| --- | --- | --- |
| Workspace navigation and diagnostics identify source context | editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/viewport/zoom behavior and traceability | Duplicate name and hidden target and all negative scenarios in its delta |
| Selection context is a copy-only external bridge | editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/viewport/zoom behavior and traceability | Stale multi-selection and all negative scenarios in its delta |
| Essential workspace operations have keyboard and reflow access | editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/viewport/zoom behavior and traceability | Keyboard and focus and all negative scenarios in its delta |

Each row must become substantive discoverable tests. For pure refactors and data conversions, preserve behavior claims already established and add only mechanism evidence warranted by the new boundary. Human interpretation of names/prose/visual fidelity stays in `docs/design/map-editor-review.md`. Temporary conversion comparison establishes no incidental geography/prose change; do not retain a second approval corpus.

## Risks / Trade-offs

Frontend shell/focus modules are shared with domain editors; keep commands/tools in domain-owned modules. The approved frontend design governs layout and states and never replaces any approved functional requirement.

Independent environments and immutable snapshots require explicit adapters. Keep a failed candidate out of published state and test the prior baseline. One-document atomic replacement avoids claiming multi-file filesystem transactions; continuous file following with the fingerprint guard deliberately excludes concurrent-writer merging and automatic retry.

## Migration Plan

Pre-release clean cutover only. Complete producer and every consumer in this change, delete the obsolete authority, and update relevant tests/docs in the same tasks. Existing source domains stay solely with their current owner until their named coherent cutover; never read a converted domain from both Python and YAML. Final complete-world publication belongs to map-interior-runtime-cutover after all map sources and partition inputs are converted. No release migration or old-format fallback is added.

## Focused implementation checks

editor frontend tests for workspace/search/diagnostics/context/focus; proposed web/tests/browser/test_map_editor_accessibility.py for real keyboard/viewport/zoom behavior and traceability

Select the smallest corresponding package/component/test class at apply time using existing project commands. Core/service package checks use their own uv project locks; game checks use root uv and the guarded test settings. Real browser checks use a standalone service rather than the game fixture. Run the contract gate once after all slice edits land. These are future checks, not evidence that implementation exists now.

## Worker execution contract

This is a proposed one-engineer-day slice, not implementation approval. Use the listed prerequisites as completed contracts. Each implementation task below is a bounded 60-90 minute unit including its own tests/docs, not an invitation to redesign architecture. Do not replace a hard boundary with a mock, empty package, fake fallback, TODO or deferred caller. Introduce the real package consumer in the same task as its producer. Keep every listed caller category and negative case. No new branches/worktrees, implementation or archive is authorized by this planning run.

During a later apply assignment, preserve existing project file conventions and follow the assigned apply branch/worktree mechanics. Source of truth is one owner per domain. Delete replaced declarations/algorithms/imports and migrate every caller without aliases, re-export shims, generated Python, compatibility readers or release migrations. Do not rename established IDs, rewrite canonical prose, rebalance data or add concurrent merge machinery. The editor never hosts AI/chat/source editing, starts OMP, writes live game state or commits Git.

Use independent package tests for core/service mechanisms and repository-discoverable Python wrappers or real browser tests for substantive requirement evidence. Root traceability currently scans test_*.py and does not infer evidence from a JS filename. A wrapper must invoke actual code/browser behavior and assert its effect; an assertion-free subprocess success is insufficient. Tests inside independent packages must not add game runtime dependencies. Obtain canonical IDs with tools.spec_traceability list against the effective merged spec tree; do not guess IDs. Before archive, every added/changed requirement must have a discoverable substantive association; none has a waiver. Preserve existing consumer-visible checks, use synthetic mechanism fixtures and temporary conversion comparisons, and never add shipped prose/count/coordinate approval tables.

Register changed non-browser game modules in .github/evennia-shards.json and browser methods in .github/browser-shards.json. Extend existing CI execution for the independent package environment when needed; do not change the exact five-root game aggregate coverage scope or weaken evidence gates. Run only the named focused checks after the slice is finished, then uv run --locked python -m tools.contract_gate and openspec validate <change> --strict. Full managed browser and complete verify --evidence remain CI-owned. Every failure-path test must inspect the unchanged baseline or explicitly committed new effect, not just an error return.

