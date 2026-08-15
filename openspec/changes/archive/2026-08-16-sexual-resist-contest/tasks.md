## 1. Confirm the dependency surface this change reads

- [x] 1.1 Confirm `world/rules/sexual_state.py::SexualState` currently exposes `climax_phase` (an
  `OrderedLevelTrait`) and `climax_turns` (a read-only `int` property), both landed by
  `climax-settlement`. If either is absent or renamed, stop and coordinate — this change is not
  implementable ahead of it.
- [x] 1.2 Confirm `world/rules/disengage.py::_adjusted_agility` and `_attempt_flee` still have their
  documented shape (`roll_d100() + actor_agility >= COMBAT_YAML["to_hit"]["defender_constant"] +
  pursuer_agility`, agility read through `evaluate_combat_modifiers()` and
  `combat._apply_percent_mod`). Do not import from `disengage.py` — this change reuses the *shape*,
  not the module, to avoid a real dependency on flee-specific machinery (design.md Decision 1).
- [x] 1.2a Confirm `world/rules/combat.py::_adjusted_attack` still adds `atk_phys` as a flat addend
  (`float(attack) + evaluate_combat_modifiers(entity).get("atk_phys", 0)`, never through
  `_apply_percent_mod`), and confirm every current `atk_phys`-producing row in `combat_modifiers.yaml`
  (`retainer_martial_training_atk_phys_bonus`, `dual_wield_style_atk_phys_bonus`) still authors a
  flat integer, not a percentage string. **This asymmetry with `agility` (percentage-only) is
  load-bearing for task 3.2 — do not skip this check.**
- [x] 1.3 Confirm `world/rules/affinity_config.py::get_config().stages` still returns exactly the
  seven stages `acquaintance/familiar/warm/trusted/bonded/beloved/absolute_bond` with floors
  `0/10/30/50/70/90/100`, and that `RelationHandler.stage_for(player)` is reachable as
  `entity.relations.stage_for(player)` via `typeclasses/entities.py::LivingEntity.relations`.
- [x] 1.4 Confirm `typeclasses/npcs.py::NPC` and `typeclasses/monsters.py::Monster` are both
  importable without circular-import issues from a new `world/rules/sexual_resist.py` module (check
  how `world/rules/sexual_state.py` already imports `Monster` lazily inside a function body, and
  follow the same lazy-import pattern here if a module-level import would cycle).

## 2. `world/rules/rulebook/sexual_resist.yaml`

- [x] 2.1 Create the YAML file with `agility_weight`, `atk_phys_weight`,
  `climax_turn_auto_comply_limit`, and `affinity_resist_modifier` (seven entries keyed by the stage
  `id`s from task 1.3; five numeric values, two `{auto_comply: true}` entries for `beloved` and
  `absolute_bond`), per design.md Decision 3.
- [x] 2.2 Write the loader in `world/rules/sexual_resist.py` (or a small private helper it calls)
  following the fail-closed validation style of `world/rules/affinity_config.py`'s own loader:
  - `agility_weight + atk_phys_weight` must equal exactly `1.0` (spec scenario: malformed weight
    pair fails closed).
  - Both `agility_weight` and `atk_phys_weight` must be non-negative (spec scenario: a negative
    weight fails closed even when the pair still sums to `1.0` — e.g. `1.5` / `-0.5` must raise, not
    load, since a negative weight would invert that stat's contribution).
  - `climax_turn_auto_comply_limit` must be a positive `int`.
  - `affinity_resist_modifier`'s key set must equal exactly `{stage.id for stage in
    get_config().stages}` — no missing, no extra (spec scenario: missing/extra stage key fails
    closed).
  - Each value must be either a finite number or the single-key mapping `{auto_comply: true}`; any
    other shape raises, naming the offending key.
- [x] 2.3 Load the YAML exactly once through a module-level singleton
  (`get_resist_config()`), mirroring `affinity_config.py`'s own `get_config()`
  lazy-cache pattern — NOT an import-time eager load: `load_sexual_resist_config()`
  validates against `get_config()`, whose loader requires the quest definition
  registry (`cap_breaks` validation) that only server startup or test setup
  populates, so an import-time load would crash every non-bootstrapped import
  (e.g. test collection). The singleton loads on first access, never per call.

## 3. `world/rules/sexual_resist.py`: the verdict type and blended score

- [x] 3.1 Define `ResistVerdict` as a frozen dataclass: `resisted: bool`, `auto_comply: bool`,
  `roll: int | None`, `actor_score: float`, `resister_score: float` (design.md Decision 6).
- [x] 3.2 Implement a private `_blended_score(entity) -> float` helper, giving each stat **its own**
  adjustment treatment — do not reuse one helper for both (per task 1.2a's confirmed asymmetry):
  ```python
  modifiers = evaluate_combat_modifiers_no_create(entity)
  agility_component = combat._apply_percent_mod(
      float(entity.skills.effective_value("agility")), modifiers.get("agility")
  )
  atk_phys_component = (
      float(entity.skills.effective_value("atk_phys")) + modifiers.get("atk_phys", 0)
  )
  return agility_component * agility_weight + atk_phys_component * atk_phys_weight
  ```
  `agility_component` mirrors `disengage._adjusted_agility` exactly (percentage string via
  `combat._apply_percent_mod`). `atk_phys_component` mirrors `combat._adjusted_attack` exactly (flat
  integer added directly). Passing `modifiers.get("atk_phys")` into `_apply_percent_mod` would raise
  `TypeError` the first time this runs against an entity owning `retainer_martial_training` or
  dual-wielding `dual_wield_style` — do not do this (this was flagged by rubber-duck review as a
  blocking bug in an earlier draft of this task). The bundle MUST come from
  `evaluate_combat_modifiers_no_create()`, never the live `evaluate_combat_modifiers()`: the live
  variant materializes the `sexual` handler, persisting traits on first access and breaking
  `resist_verdict()`'s no-mutation contract (rubber-duck review finding; pinned by the
  "never materializes sexual state" integration test).
- [x] 3.3 Implement a private `_affinity_term(actor, resister) -> tuple[float, bool]` returning
  `(modifier_or_zero, auto_comply)`:
  - `isinstance(resister, NPC)` (from `typeclasses.npcs`) and `isinstance(actor,
    typeclasses.characters.PlayerCharacter)` both true: look up
    `resister.relations.stage_for(actor).id` in `affinity_resist_modifier`; return its numeric value
    (or `0.0`) and whether the entry is `{auto_comply: true}`.
  - Otherwise (a `Monster` resister, an `NPC` resister paired with a non-player `actor`, or any other
    shape): return `(0.0, False)` unconditionally — no `.relations` read (design.md Decision 4; spec
    scenario: an NPC resister still receives no affinity term against a non-player actor).
- [x] 3.4 Implement a private `_climax_turn_short_circuit(resister) -> bool`: `True` when
  the resister's *stored* climax state reads as `climax_phase` level `進行中` with `climax_turns
  <= climax_turn_auto_comply_limit`. Both facts MUST be read without materializing the `sexual`
  handler — `SexualState.__init__` persists traits on first access, which would break
  `resist_verdict()`'s no-mutation contract (rubber-duck review finding) — using
  `combat_modifiers.build_no_create_condition_context` for the phase level (an unmaterialized
  entity reads as not-in-進行中) and the stored `sexual_state` attribute category for
  `climax_turns`.

## 4. `resist_verdict()` itself

- [x] 4.1 Implement `resist_verdict(actor, resister, *, rng=roll_d100) -> ResistVerdict`:
  1. Compute `actor_score = _blended_score(actor)` and `resister_score = _blended_score(resister)`.
  2. Compute `affinity_modifier, affinity_auto_comply = _affinity_term(actor, resister)`.
  3. `resister_score += affinity_modifier`.
  4. If `affinity_auto_comply` or `_climax_turn_short_circuit(resister)`: return
     `ResistVerdict(resisted=False, auto_comply=True, roll=None, actor_score=actor_score,
     resister_score=resister_score)` without calling `rng()`.
  5. Otherwise: `roll = rng()`; `resisted = roll + resister_score >=
     COMBAT_YAML["to_hit"]["defender_constant"] + actor_score`; return the populated
     `ResistVerdict(resisted=resisted, auto_comply=False, roll=roll, ...)`.
- [x] 4.2 Import `roll_d100` from `world.rules.dice` as the default `rng` (spec scenario: default RNG
  is the shipped dice roller, not a private reimplementation).
- [x] 4.3 Import `COMBAT_YAML` from `world.rules.combat` for `defender_constant` — do not hardcode
  `51` locally.
- [x] 4.4 Add `resist_verdict`, `ResistVerdict` to this module's `__all__`.

## 5. Tests

- [x] 5.1 `world/rules/tests/test_sexual_resist.py` (pure `unittest.TestCase`, no Evennia database
  needed unless entity fixtures require it — check whether `PlayerCharacter`/`NPC`/`Monster`
  construction requires `EvenniaTest`; if so, use it per `AGENTS.md`'s testing conventions).
- [x] 5.2 One test per spec scenario in `specs/sexual-resist-contest/spec.md` — enumerate them
  explicitly rather than writing ad hoc tests, so every scenario has a traceable match. Apply
  `covers_requirement` per `AGENTS.md`'s OpenSpec test traceability section, obtaining the exact
  requirement IDs via `uv run --locked python -m tools.spec_traceability list` after this spec is
  merged into `openspec/specs/` (not available until archive; if IDs cannot yet be resolved, annotate
  after archiving per that workflow's own instructions — do not guess an ID).
- [x] 5.3 A dedicated asymmetry test: construct a fixture where swapping `actor`/`resister` changes
  which side gets the affinity or climax-turn short circuit, and assert the verdict actually flips
  (design.md Risk 1).
- [x] 5.4 A monotonicity test across the five numeric affinity stages (`acquaintance` through
  `bonded`): iterating them in ascending affinity order, each stage's resulting `resister_score` is
  non-increasing relative to the previous stage (spec scenario, design.md Decision 3 rationale).
- [x] 5.5 A test asserting `_affinity_term` never reads `.relations` for a `Monster` resister — patch
  or spy on the handler and assert it is untouched, not merely that the numeric result happens to be
  zero (design.md Decision 4 — the type check is load-bearing, not incidentally correct).
- [x] 5.6 A test constructing a participant owning `retainer_martial_training` or dual-wielding with
  `dual_wield_style` and asserting `_blended_score()` applies that flat `atk_phys` bonus additively
  with no error — the regression test for the blocking bug fixed in tasks 1.2a/3.2.
- [x] 5.7 A test asserting a negative-weight `sexual_resist.yaml` (summing to `1.0`) raises at load
  time, distinct from the sum-mismatch case already covered by 5.2's scenario enumeration.
- [x] 5.8 A test asserting an `NPC` resister paired with a non-player `actor` (another `NPC`, or a
  `Monster`) receives affinity contribution `0` and never reads `.relations` — the branch of Decision
  4 not covered by 5.5's Monster-resister test.

## 6. Validation

- [x] 6.1 Run `uv run --locked python -m compileall -q world` to catch syntax errors early.
- [x] 6.2 Run the new test module directly:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world.rules.tests.test_sexual_resist`.
- [x] 6.3 Run `uv run --locked python -m tools.spec_traceability check` and address any reported gap
  before finishing.
- [x] 6.4 Run `openspec validate sexual-resist-contest --strict` and resolve every finding.
- [x] 6.5 Run `uv run --locked -m unittest discover -s tests -t .` to confirm no repository-wide
  contract regressed (e.g. import-boundary tests that enumerate `world/rules/` modules).
