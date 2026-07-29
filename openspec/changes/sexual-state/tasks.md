## 1. Package layout and dependency verification

- [ ] 1.1 Confirm `world/rules/rulebook/schema.py` (`Rule`, `load_rules`, `evaluate_condition`) and
      `world/rules/buffs.py` (`entity_active_buffs`) are importable from change 6, and
      `world/lore/sexual_vocab.py`'s six tuples are importable from change 4, before writing any code
      in this change.
- [ ] 1.2 Create `world/rules/sexual_state.py` as an empty module with a module docstring referencing
      design doc §6.4 and this change, naming change 6's `schema.py` as the condition engine this
      module imports rather than reimplements.
- [ ] 1.3 Confirm the `evennia.contrib.rpg.traits` `Trait`/`TraitHandler` constructor signature
      (`min`/`max` keyword names, whether a second `TraitHandler` instance can bind to a distinct
      `db_attribute_key` on the same entity) against the installed Evennia 6.1.0, per this project's
      established verify-before-trusting discipline (changes 1–6).

## 2. OrderedLevelTrait (`world/rules/sexual_state.py`)

- [ ] 2.1 Implement `OrderedLevelTrait(Trait)` per design.md D-1: `trait_type = "ordered_level"`,
      constructed with a `levels: tuple[str, ...]` keyword, storing a bounded integer ordinal
      (`min=0`, `max=len(levels) - 1`).
- [ ] 2.2 Implement the `.level` property returning `self.levels[self.value]`.
- [ ] 2.3 Implement `_ordinal_of(other)` and the comparison operators (`__eq__`, `__ge__`, `__gt__`,
      `__le__`, `__lt__`) per design.md D-1: accept a raw vocabulary string (resolved via
      `self.levels.index(other)`, raising `ValueError` naming the invalid level if not found),
      another `OrderedLevelTrait` (compared by ordinal), or a bare int.
- [ ] 2.4 Register `"world.rules.sexual_state.OrderedLevelTrait"` in `settings.TRAIT_CLASS_PATHS`
      (wherever change 1's project skeleton placed it, likely `server/conf/settings.py`).

## 3. SexualState handler (`world/rules/sexual_state.py`)

- [ ] 3.1 Implement `SexualState.__init__(self, entity)` per design.md D-2: mounts a private
      `TraitHandler(entity, db_attribute_key="sexual_traits")`, distinct from `entity.traits`.
- [ ] 3.2 Implement the three-way construction dispatch per design.md D-2/D-7: `entity.db.sexual`
      populated → character path; `entity.db.sexual` absent and `isinstance(entity, Monster)` →
      monster-default baseline with `shame` bounds clamped to `(0, 0)`; otherwise → generic default
      baseline (floor for every field, no clamp).
- [ ] 3.3 Implement `_build_from_baseline(baseline: dict)`: adds `arousal`/`wetness`/`shame`/
      `exposure`/`climax_phase` as `ordered_level` traits on the private handler, each with its
      `levels` tuple from `world.lore.sexual_vocab`; defaults any of `wetness`/`shame`/`exposure`/
      `climax_phase` omitted from `baseline` to its vocabulary's index-0 level (per import-contract's
      D-7 open question, resolved here); adds `climax_today` as a `CounterTrait` (min 0, no max);
      stores `virgin` (bool) and `experience_types` (frozenset) directly via `entity.attributes`
      under a `sexual_state` category, not on the private `TraitHandler`.
- [ ] 3.4 Implement `build_monster_sexual_baseline() -> dict` per design.md D-7: floor level for every
      field, empty `sensitivity` dict, `virgin=True`, empty `experience_types`.
- [ ] 3.5 Implement `_generic_default_baseline() -> dict` for the third dispatch branch (an entity
      with no raw baseline that is not a `Monster`): identical floor-level shape as the monster
      default, but the caller applies no `shame` clamp for this branch.
- [ ] 3.6 Implement `_SensitivityProxy` per design.md D-3: `__getitem__` lazily adds a
      `sensitivity__<part>` `ordered_level` trait (levels=`SENSITIVITY_LEVELS`) on the private
      handler the first time an unseen part is read, defaulting to ordinal 0 (`"普通"`);
      `__setitem__` and `.items()` per design.md's sketch. Mount as `SexualState.sensitivity`
      returning a `_SensitivityProxy` instance.
- [ ] 3.7 Implement `virgin`/`experience_types` accessors on `SexualState`: `virgin` setter refuses to
      set `True` once `False` has been stored (irreversibility enforced at the attribute-write level,
      not only by the rule that calls it); `experience_types` setter/adder only ever unions, never
      replaces or removes.
- [ ] 3.8 Mount `entity.sexual` in `typeclasses/entities.py`, **replacing** change 3's
      `sexual = AttributeProperty(default=None)` with:
      ```python
      @lazy_property
      def sexual(self):
          return SexualState(self)
      ```
      Confirm the diff touches only the `sexual` declaration and no other attribute, method, or base
      class earlier changes authored.

## 4. Decay and daily reset (`world/rules/sexual_state.py`)

- [ ] 4.1 Define a small `DECAY_CONFIG` mapping (field → `{interval_seconds, floor}`) per design.md's
      decay discussion: `arousal` (floor `平靜`), `wetness` (floor `乾燥`), `shame` (floor `無`),
      `climax_phase` (`only_from: 餘韻`, target `未達`) — covering `variable_rule.md`'s "長期無刺激可能
      降低1級" / "未受刺激時逐漸降低" / "獨自在私密場所時緩慢降低" / afterglow-to-未達 decay bullets.
      `sensitivity` and `exposure` have no natural decay per `variable_rule.md` and are not entries in
      this table.
- [ ] 4.2 Implement `decay_tick(entity, elapsed_seconds: int) -> None`: accumulates `elapsed_seconds`
      per configured field in `entity.attributes.sexual_decay_accumulator` (category
      `sexual_state`); when a field's accumulator crosses its configured interval, decrements that
      field by one level toward its floor (routing any `climax_phase` decrement through
      `_apply_climax_phase_set()`, task 5.5, never writing the trait directly) and resets that
      field's accumulator. Invokable directly in a test, no `WorldClock` present.
- [ ] 4.3 Implement `reset_daily_counters(entity) -> None`: sets `climax_today` to `0`. No other field
      changes.
- [ ] 4.4 Confirm neither `decay_tick` nor `reset_daily_counters` references trait-regen scheduling,
      buff-tick scheduling, or imports a `WorldClock` class — a grep-based check mirroring change 6's
      task 5.8 discipline for its own `tick_buffs` seam.

## 5. Rule table and rule application (`world/rules/rulebook/sexual.yaml`, `world/rules/sexual_state.py`)

- [ ] 5.1 Author `world/rules/rulebook/sexual.yaml` with the 25 rules transcribed in design.md D-4,
      grouped by field (`arousal`, `wetness`, `climax_phase`, `climax_today`, `virgin`/
      `experience_types`, `shame`, `exposure`, `sensitivity`), each with a unique `id`, using change
      6's shared `when` grammar and this change's own `then` vocabulary (`field`, `delta`, `set`,
      `add`, `set_from`, `part_from_context`, `irreversible`).
- [ ] 5.2 Implement `FIELD_KINDS` (field name → `"ordered_level"` / `"counter"` / `"flag"` /
      `"append_only_set"` / `"cyclic"`) covering every distinct `field` value appearing anywhere in
      `sexual.yaml`; a regression test (task 8.4) asserts no field is missing from this registry.
- [ ] 5.3 Implement `_parse_delta(delta: str) -> int`: parses a fixed signed offset (`"+1"`, `"-1"`)
      or an inclusive range (`"+1..+2"`) resolved via `random.randint`.
- [ ] 5.4 Implement `_apply_then(entity, then: dict, context: dict) -> str | None` per design.md D-4:
      dispatches on `FIELD_KINDS[then["field"]]`; applies `delta`/`set`/`add`/`set_from`/
      `part_from_context` per the field's kind; enforces `irreversible` for `flag`-kind fields
      (refuses to write back to a truthy-then-falsy — or the reverse — once the irreversible value
      has been stored); returns the direction (`"up"`/`"down"`) the field moved in, or `None` if
      unchanged, for `apply_event()`'s cascade tracking.
- [ ] 5.5 Implement `_apply_climax_phase_set(entity, target_level: str) -> str | None` per design.md
      D-6: the `_VALID_CLIMAX_TRANSITIONS` cycle table and the guard that no-ops any `set` targeting
      an invalid edge (e.g. `進行中 → 接近`). This is the **only** code path permitted to write
      `climax_phase`'s value — `_apply_then` routes every `climax_phase` mutation through it, never
      writing the trait directly.
- [ ] 5.6 Implement `_build_context(entity, event, changed, **event_context) -> dict` per design.md
      D-5: assembles `event`, each ordered-level field (the live `OrderedLevelTrait`, not `.level`),
      `climax_today`, `virgin`, `experience_types`, `active_buffs` (via change 6's
      `entity_active_buffs()`), and `_changed`.
- [ ] 5.7 Implement `apply_event(entity, event: str, **event_context) -> list[str]` per design.md D-5:
      the fixed-point evaluation loop (`_MAX_PASSES = 5`), tracking which rule IDs already fired for
      the initiating event so they do not re-apply on a later pass unless `field_changed`-triggered.
      Returns the ordered list of fired rule IDs.

## 6. Tests

- [ ] 6.1 `world/rules/tests/test_ordered_level_trait.py` — per the `ordered-level-trait` capability:
      construction defaults to ordinal 0; bounds clamp at both ends; `.level` reflects the ordinal;
      `__eq__`/`__ge__`/`__gt__`/`__le__`/`__lt__` each tested against a raw vocabulary string,
      another `OrderedLevelTrait`, and a bare ordinal; a typo'd level string raises `ValueError`; a
      direct test that `evaluate_condition({"field": "arousal", "gte": "高度"}, {"arousal": <trait>})`
      returns the correct boolean with no mock or stub standing in for the trait.
- [ ] 6.2 `world/rules/tests/test_sexual_state.py` — one test function per rule ID in `sexual.yaml`
      (`test_rule_arousal_up_on_stimulus`, `test_rule_wetness_follows_arousal_increase`, ... all 25),
      each constructing the minimal entity/event/context that satisfies exactly that one rule and
      asserting the documented field mutation occurred; a test asserting an unrelated event changes
      nothing; a test asserting a cascading `field_changed` rule fires within one `apply_event()`
      call (`stimulus_applied` → arousal up → `wetness_follows_arousal_increase` also fires); a test
      constructing a deliberately cyclic rule table and asserting `apply_event()` still returns
      within `_MAX_PASSES` iterations rather than hanging.
- [ ] 6.3 `world/rules/tests/test_sexual_state.py` (or a dedicated module) — climax-phase cycle tests
      per design.md D-6: `climax_gate` does not regress `進行中`/`餘韻` back to `接近`;
      `climax_progresses_on_continued_stimulus` does not fire from `未達`; a fabricated rule
      attempting an invalid edge (e.g. `進行中 → 接近` directly) is asserted to no-op via
      `_apply_climax_phase_set()` directly.
- [ ] 6.4 `world/rules/tests/test_sexual_state.py` (or a dedicated module) — virginity/experience
      tests: `virginity_once` and `experience_vaginal_added` both fire from the shared
      `first_vaginal_penetration` event (design.md D-8's resolved contradiction); `virgin` cannot be
      set back to `True` once `False`; `experience_types` only grows, never shrinks, across repeated
      `apply_event()` calls.
- [ ] 6.5 `world/rules/tests/test_monster_sexual_baseline.py` — per the `sexual-state-handler`
      capability: a `Monster` with no `entity.db.sexual` baseline gets floor-level fields, `shame`
      clamped to `無` and unable to move via `apply_event()`; `sensitivity` for an unseen body part
      defaults to `普通`; a non-`Monster` entity with no baseline (the generic-default branch) gets
      floor-level fields with **no** shame clamp, and its `shame` field *can* be raised via
      `apply_event()`.
- [ ] 6.6 `world/rules/tests/test_sexual_decay_and_reset.py` — per the `sexual-state-handler`
      capability: `decay_tick()` invoked directly (no clock) decrements a field by one level once its
      configured interval has accumulated, and does nothing before that; `climax_phase`'s afterglow
      decay (`餘韻` → `未達`) routes through `_apply_climax_phase_set()`; `reset_daily_counters()`
      zeroes `climax_today` and changes nothing else; a source-scan assertion that
      `world/rules/sexual_state.py` contains no reference to a settlement order, trait-regen
      scheduling, or a `WorldClock` import.
- [ ] 6.7 `world/rules/tests/test_sexual_rule_id_test_correspondence.py` — per the
      `sexual-transition-rulebook` capability: walks `sexual.yaml`'s loaded rule IDs via `load_rules()`
      and asserts a `test_rule_<id>` function exists in `test_sexual_state.py` via
      `inspect.getmembers`, mirroring change 6's identical `test_rule_id_test_correspondence.py`
      mechanism exactly. Fails naming any rule ID missing its test.
- [ ] 6.8 A regression test asserting every distinct `field` value appearing in `sexual.yaml` has a
      corresponding entry in `FIELD_KINDS` (task 5.2), failing loudly and naming the unmapped field
      rather than falling through to a default at runtime.

## 7. Cross-change verification

- [ ] 7.1 Run `world/rules/tests/test_combat_modifiers_self_arming.py` in isolation **before**
      writing any code in this change and confirm `test_high_arousal_rule_fires_once_sexual_state_
      exists` still reports **skipped** (baseline sanity check that the guard itself is intact).
- [ ] 7.2 After completing sections 1–6, run the same test again in isolation and confirm it now
      reports **passed**, not skipped and not failed — constructing a real entity whose
      `entity.sexual.arousal` is at or above `高度` and asserting `evaluate_combat_modifiers()`
      returns `high_arousal_agility_accuracy_penalty`'s adjustment bundle against the live object.
- [ ] 7.3 Confirm no edit was made to any file owned by change 6 (`world/rules/rulebook/schema.py`,
      `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/combat_modifiers.py`,
      `world/rules/buffs.py`, `world/rules/rulebook/buffs.yaml`,
      `world/rules/tests/test_combat_modifiers_self_arming.py`) or by change 4
      (`world/lore/sexual_vocab.py`, `world/imports/*`) — this change reads their public seams only.

## 8. Final verification

- [ ] 8.1 Run the full `world/rules/tests/` suite added or extended by this change and confirm every
      test passes.
- [ ] 8.2 Confirm `world/rules/rulebook/sexual.yaml` parses via `load_rules()` with no `id` missing or
      duplicated (task 6.7's mechanical check, run explicitly as part of this verification pass).
- [ ] 8.3 Confirm every rule ID in `sexual.yaml` has exactly one corresponding `test_rule_<id>`
      function (task 6.7's check, run explicitly).
- [ ] 8.4 Confirm every distinct `field` value in `sexual.yaml` has a `FIELD_KINDS` entry (task 6.8's
      check, run explicitly).
- [ ] 8.5 Confirm no function in `world/rules/sexual_state.py` writes `climax_phase`'s value except
      through `_apply_climax_phase_set()` (grep by hand, mirroring change 3's task 7.5 and change 6's
      task 6.2 discipline).
- [ ] 8.6 Run `openspec validate sexual-state --strict` and confirm it passes.
