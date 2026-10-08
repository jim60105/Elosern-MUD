## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 4.4 movement deferral and held interval; 6.2 hold query seam; 9 deferral/release; 10 crossed departure. Existing production seams are world/rules/npc_schedules.py or occurrence sibling; world/rules/guild_exams.py; world/rules/combat_session/settlement.py; startup recovery composition root; schedule-hold tests.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

This is the complete scheduler hold/replay core predecessor, independent of production examination starts. Expose rules-owned begin_exam_schedule_hold(npc, exam_id, start_tick), read_exam_schedule_hold(npc), and release_exam_schedule_hold(npc, exam_id, through_tick). Persist host dbref, exam identity, start tick, held-through tick and consumed-through occurrence identity. APIs validate exact ownership, use storage/cache snapshots, and support an outer lifecycle transaction. No general queue is introduced.
The existing schedule source consults this hold before executing movement or state entries; held occurrences remain recoverable and unrelated NPCs settle unchanged. Release consumes ordered occurrences through the same _settle_occurrence and real Exit machinery without another advance. Effective-from, silencing and per-entry failures remain authoritative. A weekly departure executes once after release.
Lifecycle, which depends on this core, owns atomic activation with exam start and release after normal host restoration for every terminal/recovery path. This predecessor tests those API sequences with synthetic examination identities and timing; it does not edit guild_exams or activate an incomplete production cutover. A crash/retry can distinguish pending and consumed release; core snapshot hooks restore location/state/hold/caches on transactional failure.
The read API reports a known hold or named indeterminate state. The availability reader depends on this change and owns its query integration; this core does not depend on or edit a future reader. Startup schedule registration remains before recovery advances.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after weekly-npc-schedule-cycles is present. Persistent-guild-exam-lifecycle is a successor that wires these complete core APIs to production examination start and settlement. This unreleased project has no save migration or backward aliases. Land source, tests, docs and owned caller changes coherently. Revert the owned implementation commit to roll back deployment; never delete persistent hosts as repair.

## Verification and Ownership

Focused synthetic real-Exit weekly departure test across exam accumulated-time settlement, pass/fail/flee/invalid recovery and duplicate release; assert unchanged final world tick versus one combat settlement and unaffected other NPC ordering.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.
