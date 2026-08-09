# spawn-named-portraits Tasks

## 1. Spawn application

- [ ] 1.1 Extend `_spawn_npc` in `world/quests/scene_builder.py` to apply characterization
      per-field inside the existing materialization transaction: `display_name` when present;
      paired `age`/`apparent_age` when present; and, when a portrait `stable_key` is present,
      `db.portrait_policy = {"mode": "named", "stable_key": ...}` plus the baseline
      `db.age = db.apparent_age = 25` when ages are absent — before the existing
      `_schedule_occupant_portraits` loop runs
- [ ] 1.2 Add the deterministic adult baseline constant (25) with a documented rationale: always
      within the adult-to-lifespan-maximum validation range for every race
- [ ] 1.3 Add scene-builder unit/integration tests for every input shape: full characterization
      applied; portrait-only receives baseline; name-only is named but portrait-less; ages-only
      sets ages but no policy; role-based occupant untouched (no name, no ages, no policy, no job)

## 2. End-to-end portrait pipeline

- [ ] 2.1 Add an integration test materializing a quest scene with a named occupant (template
      quest from `blueprint-portrait-policy`), executing commit callbacks explicitly around the
      materialization (`captureOnCommitCallbacks(execute=True)`), then draining with the injected
      fake worker (`drain_synchronous()`); assert the queued job subject
      `portrait:character:<stable_key>` and the adult story-driven description (display name +
      declared age or baseline 25)
- [ ] 2.2 Add a baseline-for-elf test: a portrait-bearing `elven_civilian` occupant without ages
      is spawned with ages 25 and passes the adult gate
- [ ] 2.3 Add a shared-key test: two scenes with the same `stable_key` resolve to one subject,
      settle to one completed asset, and the first materialized description wins
- [ ] 2.4 Add a rollback test: a rolled-back materialization emits no post-commit portrait job

## 3. Repository guards and verification

- [ ] 3.1 Add a guard test asserting a portrait-bearing occupant always carries canonical adult
      ages before the policy is set (the adult gate's inputs are guaranteed present)
- [ ] 3.2 Confirm no art-layer files changed (subjects, adult gate, queue, worker, presenter stay
      read-only) and existing art-assets / scene-builder suites stay green
- [ ] 3.3 Run the affected Evennia test domains
      (`uv run --locked evennia test --settings settings.py world.quests.tests.test_scene_builder
      world.art.tests ...`) and the repository-wide contract tests
- [ ] 3.4 Run `uv run --locked python -m tools.spec_traceability check` and confirm the new main
      requirements carry `covers_requirement` annotations
- [ ] 3.5 Run `openspec validate spawn-named-portraits --strict` and confirm the change is
      apply-ready
