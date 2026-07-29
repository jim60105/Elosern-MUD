## Why

This is roadmap item #7 (design doc §11), depending on change 6 (`buffs-rulebook`, which built the
shared declarative condition grammar in `world/rules/rulebook/schema.py` and left an explicit,
documented handoff for this change to import rather than reinvent) and consuming change 4's
(`import-contract`) frozen `world/lore/sexual_vocab.py` vocabulary and its `entity.db.sexual` raw
baseline storage convention. Design doc §6.4 requires a working `SexualState` state machine — six
ordered-level fields, a daily counter, and two append-only/one-way flags — driven by declarative
transition rules in `rulebook/sexual.yaml`. Two things block every downstream system until this
change lands: change 6's own `combat_modifiers.yaml` has two rules (`high_arousal_agility_accuracy_
penalty`, `climax_in_progress_locks_actions`) sitting inert against a duck-typed stub, self-arming
only once a real `entity.sexual` exists — a dedicated regression test currently asserts this reports
**skipped**, not passed, and change 6's design doc names this change explicitly as the trigger; and
Evennia ships no ordered/enum trait type at all (confirmed against 6.1.0 in change 1's contrib-matrix
verification), so the ordered-level `Trait` subclass itself must be authored from scratch here, with
no existing class to extend.

`tmp/story_settings/variable_rule.md` is the only behavioral specification for how each field
actually transitions — it predates every OpenSpec change and was never written against this
project's rule-table grammar. This change is the first to transcribe it faithfully into change 6's
`when`/`then` shape, and the first to resolve its several internal ambiguities and one direct
self-contradiction (see design.md) into concrete, testable rules.

## What Changes

- Add `world/rules/sexual_state.py`: an `OrderedLevelTrait` class (a from-scratch `Trait` subclass,
  since Evennia 6.1.0 ships no ordered/enum trait type — `CounterTrait`'s numeric-bucket-to-label
  `descs` mapping is the closest built-in precedent, studied but not subclassed, per design doc §4's
  own framing), registered at `world.rules.sexual_state.OrderedLevelTrait` in
  `settings.TRAIT_CLASS_PATHS` — the identical registration mechanism the contrib's own `RageTrait`
  example uses. Internally stores an ordinal index into whichever `world.lore.sexual_vocab` tuple it
  was constructed against, and implements rich comparison (`__eq__`/`__ge__`/etc.) that accepts a raw
  Chinese level string, another `OrderedLevelTrait`, or a bare ordinal — this is what lets change 6's
  `evaluate_condition()`'s `gte`/`equals` comparators work against it with zero code change on change
  6's side, exactly the contract change 6's design doc D-2 left as the caller's responsibility.
- Add the `SexualState` handler class in the same module: mounts a private, second `TraitHandler`
  instance (distinct from `entity.traits`) over the six ordered-level fields plus a dynamically-keyed
  `sensitivity` sub-collection (one `OrderedLevelTrait` per body part named in the baseline data),
  the `climax_today` counter, and the `virgin`/`experience_types` flags. Reads `entity.db.sexual`
  (change 4's raw imported baseline) at construction for `PlayerCharacter`/`NPC`; for `Monster`
  entities (which are never routed through change 4's JSON import pipeline), constructs from this
  change's own monster-default baseline — 普通 sensitivity, `shame` permanently clamped to 無, per
  design doc §6.4's explicit requirement.
- Mount `entity.sexual` as `@lazy_property: SexualState(self)` on `LivingEntity`
  (`typeclasses/entities.py`), replacing change 3's `None`-defaulting placeholder — the same
  handler-mount replacement pattern changes 5 and 6 already used for `skills`/`equipment`/`buffs`.
  `entity.sexual` **is** the handler; the raw baseline stays at `entity.db.sexual`, never confused
  with the bare name — this convention was corrected across changes 4 and 5 and must not regress.
- Add `world/rules/rulebook/sexual.yaml`: every event/field-triggered transition rule transcribed
  from `variable_rule.md`, each with a unique `id`, using change 6's shared `when` grammar
  (`event` / `field`+`equals`/`gte` / `field_changed`+`direction`) unmodified, with `then` clauses in
  a vocabulary this change defines and owns (`field`+`delta`/`set`/`add`/`set_from`,
  `irreversible: true`) — mirroring exactly the "shared matcher, table owns its own effect
  vocabulary" split change 6's design doc D-1 established, not a second condition evaluator.
- Add a small, separate per-field decay/clamp configuration (not a `when`/`then` rule table, for the
  same reason change 6's `buffs.yaml` is not one either — decay is clock-triggered, not
  condition-triggered) and two plain callables change 11 (`world-clock`) is expected to invoke at its
  own chosen point in the fixed settlement order: `decay_tick(entity)` and
  `reset_daily_counters(entity)`. Neither invents or assumes any ordering relative to trait regen or
  buff ticks.
- Add `world/rules/tests/test_sexual_state.py` (and companions): one unit test per rule ID in
  `sexual.yaml`, a mechanical rule-ID-to-test-name correspondence check (mirroring change 6's D-7
  discipline exactly), and tests for `OrderedLevelTrait`'s comparison contract, the monster-baseline
  path, `decay_tick`, and `reset_daily_counters`.
- **Flips change 6's self-arming test.** `world/rules/tests/test_combat_modifiers_self_arming.py`'s
  `test_high_arousal_rule_fires_once_sexual_state_exists`, guarded by
  `pytest.importorskip("world.rules.sexual_state")`, currently reports skipped. After this change
  lands, the module exists and `entity.sexual` is a real `SexualState` object whose `.arousal`
  compares correctly against `高度` via the ordered-level trait's own `__ge__` — the test must run
  and pass. A verification task confirms this transition explicitly, since a change that leaves it
  still skipped would mean the mount or the comparison contract is broken, not that the feature is
  done.

## Capabilities

### New Capabilities
- `ordered-level-trait`: the from-scratch `Trait` subclass, its `TRAIT_CLASS_PATHS` registration, and
  its comparison contract against raw vocabulary strings, ordinals, and other instances of itself.
- `sexual-state-handler`: `entity.sexual` mounted as the real `SexualState` handler, its field model
  (six ordered levels, `sensitivity` dict, `climax_today`, `virgin`, `experience_types`), the
  character-baseline-from-`entity.db.sexual` construction path, and the distinct monster-baseline
  construction path (普通 sensitivity, `shame` clamped to 無).
- `sexual-transition-rulebook`: `rulebook/sexual.yaml`'s transition rules sharing change 6's condition
  engine with a sexual-state-owned `then` vocabulary, the rule-ID-to-test-name correspondence
  discipline, and the `decay_tick`/`reset_daily_counters` plain callables exposed for change 11.

### Modified Capabilities
- None. `openspec/specs/` is currently empty (changes 1–6 have not been archived yet). Change 6's
  `combat-modifier-table` capability already documents the self-arming scenario this change satisfies
  — no requirement text changes, the scenario simply starts being exercised for real.

## Impact

- **New files**: `world/rules/sexual_state.py`, `world/rules/rulebook/sexual.yaml`,
  `world/rules/tests/test_sexual_state.py`, `world/rules/tests/test_ordered_level_trait.py`,
  `world/rules/tests/test_sexual_rule_id_test_correspondence.py`,
  `world/rules/tests/test_monster_sexual_baseline.py`.
- **Modified files**: `typeclasses/entities.py` — replaces the `sexual` placeholder
  `AttributeProperty` (change 3, D-10) with a real handler mount, the identical replacement pattern
  changes 5/6 already used for `skills`/`equipment`/`buffs`. `server/conf/settings.py` (or wherever
  change 1 placed `TRAIT_CLASS_PATHS`) — adds `world.rules.sexual_state.OrderedLevelTrait`'s dotted
  path. `world/rules/tests/test_combat_modifiers_self_arming.py` is not edited, but its one test's
  reported outcome changes from skipped to passed as a direct consequence of this change existing.
- **Depends on**: change 6 (`buffs-rulebook`) for `world/rules/rulebook/schema.py`'s
  `Rule`/`load_rules()`/`evaluate_condition()`, and for `entity.buffs`/`entity_active_buffs()` as the
  read-only seam a future buff could use to modify a sexual field's rate/bounds/decay. Change 4
  (`import-contract`) for `world/lore/sexual_vocab.py`'s six frozen tuples (consumed, never
  redefined) and for `entity.db.sexual`'s raw-baseline storage convention. Change 3 (`entity-traits`)
  for `LivingEntity`, `Monster`, and the `sexual` placeholder attribute being replaced.
- **Consumers deferred to later changes**: change 8 (`action-resolver`) is expected to call
  `SexualState.apply_event(...)` from its effect-resolution step and to author any sexual-magic buff
  instances targeting a sexual field's rate/bounds/decay; change 11 (`world-clock`) is expected to
  invoke `decay_tick()`/`reset_daily_counters()` at its own fixed settlement-order position; change 9
  (`dice-combat`) already has a concrete `entity.sexual` to read via change 6's
  `evaluate_combat_modifiers()` the moment this change lands.
