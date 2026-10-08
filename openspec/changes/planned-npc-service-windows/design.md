## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 6.2; 9 reader; 10 availability coverage. Existing production seams are world/rules/npc_schedules.py or focused sibling reader; world/rules/service_gate.py; world/rules/clock.py read seam; schedule reader tests.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

Provide a pure rules-core reader taking persistent NPC, destination room and current authoritative tick. Return a frozen interval with absolute start_tick/end_tick or a named unavailable reason. Reuse parsed schedule and predecessor occurrence iterator. Never obtain a clock by a materializing getter; missing clock is unavailable.
Project movement and state entries from actual location/state, honoring effective-from, same-tick index order and service-guild blocking states. Intervals are [start,end). A move into the guild followed at the same tick by busy is unusable until service state opens. Existing actual presence takes priority over projected arrival; an arrival due at now remains planned until location confirms it. A missed earlier arrival while NPC remains absent cannot provide the remaining interval.
Use a deterministic bound of the remaining current cycle plus one complete future cycle (at most 2*MAX_ENTRIES occurrences); if that cannot establish an arrival and service-capable end, return unconfirmable, not a fabricated endpoint. Indeterminate holds or schedule_silenced return unavailable; a known hold projects only after its authoritative release constraint. Unresolved targets/invalid schedule/clock/destination produce named reasons. Prediction is planned and may be invalidated by travel locks or later activities.
Expose guild attendance only; caller adds host/branch/target and formats via existing game calendar. Do not leak residences/full schedule or mutate attributes, tags, clock, movement, schedules, attempts, resources or affinity.
Capture one current authoritative tick and immutable parsed schedule/state/location snapshot for the read. A changed schedule between menu and submission is re-read by coordinator/start, never treated as reservation authority.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after weekly-npc-schedule-cycles are present. Read predecessor delta plus live source before editing. This unreleased project has no save migration or backward aliases. Land source, tests, docs and all caller cutovers as one coherent change. Revert the owned implementation commit to roll back deployment; never delete persistent hosts or manufacture data as repair.

## Verification and Ownership

Focused new synthetic Evennia reader module, fixed absolute ticks, real room/Exit settlement comparisons and complete before/after attribute/location/clock snapshots; no private-route output.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.
