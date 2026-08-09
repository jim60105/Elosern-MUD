# Tasks: npc-schedule-model

## 1. Rulebook data

- [ ] 1.1 Create `world/rules/rulebook/npc_schedules.yaml` with `schema_version: 1` and role
  templates for at least `guard`, `storekeeper`, and `resident`; each template is an ordered list
  of `{tick_offset, kind: move|state, target?|state?}` entries; document the bounded `state`
  vocabulary (e.g. `duty`, `resting`, `busy`) and declare a `default_state` on templates that
  need one
- [ ] 1.2 Add a rulebook load test: the shipped YAML validates (schema version, template keys,
  entry shapes, per-kind field presence, `tick_offset` in `[0, day_seconds)`, `default_state`
  vocabulary)

## 2. Parsing, validation, and assignment module

- [ ] 2.1 Implement `world/rules/npc_schedules.py` entry validation: named errors for unknown
  `kind`, missing/extra per-kind fields, non-integer or out-of-day `tick_offset`, oversized
  entries, out-of-vocabulary `default_state`
- [ ] 2.2 Implement template resolution with shallow per-entry-index override merge; overrides
  referencing a missing index reject with a named error
- [ ] 2.3 Implement `set_npc_schedule(npc, schedule)`, the sole writer of `npc.db.schedule`:
  validates both storage shapes (`schema_version`/`template`/`overrides` or full `entries`),
  rejects both-shapes-present / unknown schema version / non-dict / unknown template key /
  over-limit entry counts, records `effective_from_tick` (current world tick), and maintains the
  persistent `schedule` tag (removed on `None`)
- [ ] 2.4 Implement the consumer-side parser used by startup sync and the runtime: malformed
  stored values resolve to "no schedule" with a named diagnostic
- [ ] 2.5 Declare the `npc.db.schedule_state` contract in the module docstring/public surface with
  no writer (guard with a source-inspection test)

## 3. Startup synchronization

- [ ] 3.1 Implement `sync_npc_schedules()` in `world/rules/npc_schedules.py`: load and validate
  the rulebook, confirm every NPC's stored schedule shape, confirm the `schedule` tag on every
  schedule-bearing NPC, treat validation failures as "no schedule" with a bounded diagnostic,
  never block startup; idempotent on re-run
- [ ] 3.2 Wire `sync_npc_schedules()` into `server/conf/at_server_startstop.py` and update the
  sync-ordering guard test (`test_guild_economy_guards.py`) for the new call position

## 4. Tests

- [ ] 4.1 Pure `unittest.TestCase` per validation rule (one test per named error; mirror the
  spec scenarios): entry shape, per-kind fields, tick bounds, `default_state` vocabulary,
  template resolution, override merge, override-missing-index, storage shapes, malformed storage
- [ ] 4.2 Assignment API tests: valid template ref / full custom list parse and set the tag and
  `effective_from_tick`; malformed shapes reject; `None` clears schedule and tag
- [ ] 4.3 Startup sync tests: valid schedules confirmed with tags, broken schedule degrades to
  no-schedule without blocking, re-run is a no-op
- [ ] 4.4 No-writer guard: `npc.db.schedule_state` is documented and never assigned by this
  change's code

## 5. Verification

- [ ] 5.1 Run `openspec validate npc-schedule-model --strict`
- [ ] 5.2 Run the affected package tests (`world/rules` pure suites and the startup-wiring
  guard test); keep `git diff --check` clean
- [ ] 5.3 Record canonical requirement IDs (`tools.spec_traceability list` after sync) and add
  `covers_requirement` annotations on the tests that establish the new requirements; run
  `spec_traceability check`
