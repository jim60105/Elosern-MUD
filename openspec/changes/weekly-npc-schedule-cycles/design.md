## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 6.1; 9 occurrence arithmetic; 10 cycle coverage. Existing production seams are world/rules/npc_schedules.py; world/rules/rulebook/npc_schedules.yaml; world/rules/tests/test_npc_schedules.py; world/rules/tests/test_npc_schedule_runtime.py.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

Retain schema_version 1. Templates and custom schedules accept optional cycle_days exactly 1 or 7 (reject booleans), default 1. Template references inherit the template cycle, with no reference or per-entry cycle override. Offset validity uses cycle_days times configured day seconds. Current weekly period is 604800 ticks.
Extract focused pure occurrence arithmetic if needed, shared by _due_occurrences, settlement, later availability and held-interval release. Absolute phase is tick zero, with no spawn/calendar/reload reset. Preserve effective_from_tick and the special start-boundary assignment occurrence, stable (due_tick,npc_id,entry_index) order, MAX_ENTRIES, tags, existing default_state behavior and per-entry failure isolation.
Movement still traverses actual Exits under locks/vetoes. Clock stage ownership, companion/service silencing and no-extra-clock-charge behavior remain unchanged. This slice authors no guild visits and introduces no second scheduler.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after the current main contracts are present. Read predecessor delta plus live source before editing. This unreleased project has no save migration or backward aliases. Land source, tests, docs and all caller cutovers as one coherent change. Revert the owned implementation commit to roll back deployment; never delete persistent hosts or manufacture data as repair.

## Verification and Ownership

Focused existing schedule model/runtime modules with synthetic cycles 1 and 7, offsets 0/end-1/end, same-tick ordering, multi-cycle jumps, failed Exit and companion-silencing cases.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.
