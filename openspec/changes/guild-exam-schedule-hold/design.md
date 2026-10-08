## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 4.4 movement deferral and held interval; 6.2 hold query seam; 9 deferral/release; 10 crossed departure. Existing production seams are world/rules/npc_schedules.py or occurrence sibling; world/rules/guild_exams.py; world/rules/combat_session/settlement.py; startup recovery composition root; schedule-hold tests.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

Use predecessor persisted exam start timing/hold marker and authoritative schedule. Active exam holds movement AND schedule-state entries for that host; unrelated NPCs continue. Do not let departure/service state break the battle. Record or derive the held settled-through interval from exam/session timing and clock windows, never a general queue.
Terminal settlement restores normal host before releasing the hold. Consume ordered held occurrences through the same _settle_occurrence and traversal machinery without advancing world time a second time. Preserve due/index ordering, effective_from, silencing and per-entry skip isolation. A weekly departure crossed in combat executes after release; no extra week at the guild. Duplicate terminal/recovery replay cannot traverse twice.
Persist hold boundaries and consumed-through marker atomically with session settlement/release so a crash before or after release is recoverable. For valid resume keep hold; invalid recovery closes simulation and releases after restoration. Startup registers schedule source before any recovery time settlement. Corrupt/indeterminate held state returns unknown to availability rather than fabricating a visit. Clock/combat/release snapshot owners include both storage and caches; no nested advance.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after weekly-npc-schedule-cycles, persistent-guild-exam-lifecycle are present. Read predecessor delta plus live source before editing. This unreleased project has no save migration or backward aliases. Land source, tests, docs and all caller cutovers as one coherent change. Revert the owned implementation commit to roll back deployment; never delete persistent hosts or manufacture data as repair.

## Verification and Ownership

Focused synthetic real-Exit weekly departure test across exam accumulated-time settlement, pass/fail/flee/invalid recovery and duplicate release; assert unchanged final world tick versus one combat settlement and unaffected other NPC ordering.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.
