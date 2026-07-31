## 1. Package layout and dependency verification

- [x] 1.1 Confirm `world/rules/rulebook/schema.py` (`Rule`, `load_rules`, `evaluate_condition`) and
      `world/rules/buffs.py` (`entity_active_buffs`) are importable from change 6, and
      `world/lore/sexual_vocab.py`'s six tuples are importable from change 4, before writing any code
      in this change. This change only needs `schema.py`/`entity_active_buffs()` importable for the
      self-arming test (section 7) — it does not call `load_rules()`/`evaluate_condition()` itself,
      since it authors no rule table.
- [x] 1.2 Create `world/rules/sexual_state.py` as an empty module with a module docstring referencing
      design doc §6.4 and this change, stating explicitly that `rulebook/sexual.yaml`,
      `apply_event()`, and their per-rule tests are change 7b's (`sexual-transition-rules`) scope, not
      this module's.
- [x] 1.3 Confirm the `evennia.contrib.rpg.traits` `Trait`/`TraitHandler` constructor signature
      (`min`/`max` keyword names, whether a second `TraitHandler` instance can bind to a distinct
      `db_attribute_key` on the same entity) against the installed Evennia 6.1.0, per this project's
      established verify-before-trusting discipline (changes 1–6).

## 2. OrderedLevelTrait (`world/rules/sexual_state.py`)

- [x] 2.1 Implement `OrderedLevelTrait(Trait)` per design.md D-1: `trait_type = "ordered_level"`,
      constructed with a `levels: tuple[str, ...]` keyword, storing a bounded integer ordinal
      (`min=0`, `max=len(levels) - 1`).
- [x] 2.2 Implement the `.level` property returning `self.levels[self.value]`.
- [x] 2.3 Implement `_ordinal_of(other)` and the comparison operators (`__eq__`, `__ge__`, `__gt__`,
      `__le__`, `__lt__`) per design.md D-1: accept a raw vocabulary string (resolved via
      `self.levels.index(other)`, raising `ValueError` naming the invalid level if not found),
      another `OrderedLevelTrait` (compared by ordinal), or a bare int.
- [x] 2.4 Register `"world.rules.sexual_state.OrderedLevelTrait"` in `settings.TRAIT_CLASS_PATHS`
      (wherever change 1's project skeleton placed it, likely `server/conf/settings.py`).

## 3. SexualState handler (`world/rules/sexual_state.py`)

- [x] 3.1 Implement `SexualState.__init__(self, entity)` per design.md D-2: mounts a private
      `TraitHandler(entity, db_attribute_key="sexual_traits")`, distinct from `entity.traits`.
- [x] 3.2 Implement the three-way construction dispatch per design.md D-2/D-5: `entity.db.sexual`
      populated → character path; `entity.db.sexual` absent and `isinstance(entity, Monster)` →
      monster-default baseline with `shame` bounds clamped to `(0, 0)`; otherwise → generic default
      baseline (floor for every field, no clamp).
- [x] 3.3 Implement `_build_from_baseline(baseline: dict)`: adds `arousal`/`wetness`/`shame`/
      `exposure`/`climax_phase` as `ordered_level` traits on the private handler, each with its
      `levels` tuple from `world.lore.sexual_vocab`; defaults any of `wetness`/`shame`/`exposure`/
      `climax_phase` omitted from `baseline` to its vocabulary's index-0 level (per import-contract's
      D-7 open question, resolved here); adds `climax_today` as a `CounterTrait` (min 0, no max);
      stores `virgin` (bool) and `experience_types` (frozenset) directly via `entity.attributes`
      under a `sexual_state` category, not on the private `TraitHandler`.
- [x] 3.4 Implement `build_monster_sexual_baseline() -> dict` per design.md D-5: floor level for every
      field, empty `sensitivity` dict, `virgin=True`, empty `experience_types`.
- [x] 3.5 Implement `_generic_default_baseline() -> dict` for the third dispatch branch (an entity
      with no raw baseline that is not a `Monster`): identical floor-level shape as the monster
      default, but the caller applies no `shame` clamp for this branch.
- [x] 3.6 Implement `_SensitivityProxy` per design.md D-3: `__getitem__` lazily adds a
      `sensitivity__<part>` `ordered_level` trait (levels=`SENSITIVITY_LEVELS`) on the private
      handler the first time an unseen part is read, defaulting to ordinal 0 (`"普通"`);
      `__setitem__` and `.items()` per design.md's sketch. Mount as `SexualState.sensitivity`
      returning a `_SensitivityProxy` instance.
- [x] 3.7 Implement the public property surface on `SexualState` per design.md D-2: `.arousal`,
      `.wetness`, `.shame`, `.exposure`, `.climax_phase` (each delegating to the private
      `TraitHandler`), `.climax_today` (int), `.sensitivity` (the `_SensitivityProxy`). This is the
      entire surface change 7b and change 9 are expected to read — no consumer outside this module
      should need `entity.sexual._traits`.
- [x] 3.7a Implement `record_climax() -> None`, incrementing `climax_today` by one. `climax_today` is
      the only field exposed as a plain value rather than a live trait object, so without this method
      change 7b's `climax_today_increment_on_climax` rule has no legal write path and would be forced
      to reach into `_traits`. Surfaced by change 7b's author as a cross-change coordination point.
      Add a test asserting two consecutive calls yield `2` and that no other field changes.
- [x] 3.8 Implement `virgin`/`experience_types` accessors on `SexualState` per design.md D-2: `virgin`
      getter/setter refuses to set `True` once `False` has been stored (irreversibility enforced at
      the public handler API used by future rules); `experience_types` getter plus
      `add_experience_type(key)` — the handler's only mutator, always a union, never a replacement or
      removal. Direct writes through Evennia's public low-level `entity.attributes` handler are
      outside this API contract and the deterministic core's sanctioned write path.
- [x] 3.9 Mount `entity.sexual` in `typeclasses/entities.py`, **replacing** change 3's
      `sexual = AttributeProperty(default=None)` with:
      ```python
      @lazy_property
      def sexual(self):
          return SexualState(self)
      ```
      Confirm the diff touches only the `sexual` declaration and no other attribute, method, or base
      class earlier changes authored.

## 4. climax_phase cycle guard (`world/rules/sexual_state.py`)

- [x] 4.1 Define `_VALID_CLIMAX_TRANSITIONS` per design.md D-4: the cycle
      `未達→接近`, `接近→{進行中, 未達}`, `進行中→餘韻`, `餘韻→{未達, 接近}`.
- [x] 4.2 Implement `_apply_climax_phase_set(entity, target_level: str) -> str | None`: no-ops
      (returns `None`) when `target_level` is not a valid edge from the current level; otherwise
      writes the new ordinal via the private `TraitHandler` and returns a truthy marker. This SHALL
      be the only function in this module (or any future module) permitted to write
      `climax_phase`'s value.

## 5. Decay and daily reset (`world/rules/sexual_state.py`)

- [x] 5.1 Define `DECAY_CONFIG` per design.md D-6: `arousal` (interval 1800s, floor `平靜`),
      `wetness` (interval 900s, floor `乾燥`), `shame` (interval 1800s, floor `無`), `climax_phase`
      (interval 300s, `only_from: 餘韻`, target `未達`). `sensitivity` and `exposure` have no entry —
      per `variable_rule.md`, neither decays naturally.
- [x] 5.2 Implement `decay_tick(entity, elapsed_seconds: int) -> None`: accumulates
      `elapsed_seconds` per configured field in `entity.attributes` (category `sexual_state`); when a
      field's accumulator crosses its configured interval, decrements that field by one level toward
      its floor (routing any `climax_phase` decrement through `_apply_climax_phase_set()`, task 4.2,
      never writing the trait directly) and resets that field's accumulator. Invokable directly in a
      test, no `WorldClock` present.
- [x] 5.3 Implement `reset_daily_counters(entity) -> None`: sets `climax_today` to `0`. No other
      field changes.
- [x] 5.4 Confirm neither `decay_tick` nor `reset_daily_counters` references trait-regen scheduling,
      buff-tick scheduling, or imports a `WorldClock` class — a grep-based check mirroring change 6's
      task 5.8 discipline for its own `tick_buffs` seam.
- [x] 5.5 Document, in `decay_tick()`'s own docstring, the target-field naming convention a future
      buff (change 6's `buffs.yaml`, not authored by this change) would use to modify a sexual
      field's rate/bounds/decay — per design.md D-6's buff-lever seam, documented but not filled.

## 6. Tests

- [x] 6.1 `world/rules/tests/test_ordered_level_trait.py` — per the `ordered-level-trait` capability:
      construction defaults to ordinal 0; bounds clamp at both ends; `.level` reflects the ordinal;
      `__eq__`/`__ge__`/`__gt__`/`__le__`/`__lt__` each tested against a raw vocabulary string,
      another `OrderedLevelTrait`, and a bare ordinal; a typo'd level string raises `ValueError`; a
      direct test that `evaluate_condition({"field": "arousal", "gte": "高度"}, {"arousal": <trait>})`
      returns the correct boolean with no mock or stub standing in for the trait.
- [x] 6.2 `world/rules/tests/test_climax_phase_cycle.py` — per the `sexual-state-handler` capability:
      `_apply_climax_phase_set()` tested directly (no rule, no `apply_event()`) for every valid edge
      in `_VALID_CLIMAX_TRANSITIONS` and at least one invalid edge (e.g. a direct
      `進行中 → 接近` attempt) asserted to no-op, leaving the current level unchanged.
- [x] 6.3 `world/rules/tests/test_sexual_state.py` — handler-level tests for `virgin`/
      `experience_types` per design.md D-2, exercised directly against the public property/method
      surface, with no rule or event involved: setting `virgin = False` then attempting
      `virgin = True` leaves it `False`; `add_experience_type("陰道性交")` followed by a repeated call
      with the same key leaves the set unchanged (idempotent), and the set never loses a
      previously-added entry.
- [x] 6.4 `world/rules/tests/test_monster_sexual_baseline.py` — per the `sexual-state-handler`
      capability: a `Monster` with no `entity.db.sexual` baseline gets floor-level fields; `shame`
      clamped to `無` and unable to move even via a direct attempt to raise its underlying trait
      value; `sensitivity` for an unseen body part defaults to `普通`; a non-`Monster` entity with no
      baseline (the generic-default branch) gets floor-level fields with **no** shame clamp, and its
      `shame` field *can* be raised via a direct trait-value write.
- [x] 6.5 `world/rules/tests/test_sexual_decay_and_reset.py` — per the `sexual-state-handler`
      capability: `decay_tick()` invoked directly (no clock) decrements a field by one level once its
      configured interval has accumulated, and does nothing before that; `climax_phase`'s afterglow
      decay (`餘韻` → `未達`) routes through `_apply_climax_phase_set()`; `reset_daily_counters()`
      zeroes `climax_today` and changes nothing else; a source-scan assertion that
      `world/rules/sexual_state.py` contains no reference to a settlement order, trait-regen
      scheduling, or a `WorldClock` import.
- [x] 6.6 `world/rules/tests/test_sexual_state.py` (or a dedicated module) — construction-path tests:
      a character-path entity with a fully-specified `entity.db.sexual` baseline uses every value
      verbatim; a character-path entity whose baseline omits an optional field (e.g. `wetness`)
      defaults that field to its vocabulary's index-0 level; `entity.db.sexual` itself remains
      untouched (still the original dict) after `entity.sexual` has been read.

## 7. Cross-change verification

- [x] 7.1 Run `world/rules/tests/test_combat_modifiers_self_arming.py` in isolation **before**
      writing any code in this change and confirm `test_high_arousal_rule_fires_once_sexual_state_
      exists` still reports **skipped** (baseline sanity check that the guard itself is intact).
- [x] 7.2 After completing sections 1–6, run the same test again in isolation and confirm it now
      reports **passed**, not skipped and not failed — constructing a real entity whose
      `entity.sexual.arousal` is set (directly, via the trait's own setter — no rule is involved) to
      or above `高度` and asserting `evaluate_combat_modifiers()` returns `high_arousal_agility_
      accuracy_penalty`'s adjustment bundle against the live object.
- [x] 7.3 Confirm no edit was made to any production file owned by change 6 (`world/rules/rulebook/schema.py`,
      `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/combat_modifiers.py`,
      `world/rules/buffs.py`, `world/rules/rulebook/buffs.yaml`,
      `world/rules/tests/test_combat_modifiers_self_arming.py`) or by change 4
      (`world/lore/sexual_vocab.py`, `world/imports/*`) — this change reads their public seams only.
      Change 6's `test_combat_modifiers.py` may replace its temporary stand-in and placeholder
      overwrite with assertions against the live handler, as declared in proposal.md's Impact.

## 8. Final verification

- [x] 8.1 Run the full `world/rules/tests/` suite added or extended by this change and confirm every
      test passes.
- [x] 8.2 Confirm no function in `world/rules/sexual_state.py` writes `climax_phase`'s value except
      through `_apply_climax_phase_set()` (grep by hand, mirroring change 3's task 7.5 and change 6's
      task 6.2 discipline).
- [x] 8.3 Confirm `world/rules/sexual_state.py` contains no import or implementation of
      `rulebook/sexual.yaml`, no `apply_event()` definition, and no per-rule test naming convention.
      The scope-boundary docstring required by task 1.2 may name those deferred artifacts; a plain
      read-through must confirm this change does not anticipate or partially implement change 7b's
      rule table.
- [x] 8.4 Confirm `design.md`'s D-7 (the `variable_rule.md` ambiguity/self-contradiction analysis) is
      present and unedited from the original pass, so change 7b's author has it to start from.
- [x] 8.5 Run `openspec validate sexual-state --strict` and confirm it passes.
