# sexual-state-handler Specification

## Purpose

Define persistent sexual-state handling, guarded transitions, decay, and integration seams.

## Requirements

### Requirement: entity.sexual is mounted as the real SexualState handler, replacing the change-3 placeholder
`LivingEntity` SHALL mount `SexualState` as a read-only computed property named `entity.sexual`,
replacing change 3's `None`-defaulting placeholder attribute. The raw imported baseline SHALL remain
at `entity.db.sexual` (change 4's loader convention), never confused with or overwritten by the bare
`entity.sexual` name.

#### Scenario: entity.sexual returns a SexualState instance
- **WHEN** `entity.sexual` is read on any `LivingEntity` instance
- **THEN** it returns a `SexualState` instance bound to that entity, not `None` and not a raw dict

#### Scenario: entity.db.sexual remains the raw baseline, untouched by the handler mount
- **WHEN** a `PlayerCharacter` constructed via change 4's loader has `entity.db.sexual` populated with
  an imported baseline dict
- **THEN** `entity.db.sexual` still equals that original dict after `entity.sexual` has been read one
  or more times, and `entity.sexual` itself is never a dict

### Requirement: SexualState is constructed from entity.db.sexual when a raw baseline is present
When `entity.db.sexual` is a populated dict (change 4's import path), `SexualState`'s construction
SHALL derive every field's initial value from that dict, defaulting any optional field the dict omits
(`wetness`, `shame`, `exposure`, `climax_phase`) to its vocabulary's first (lowest) level.

#### Scenario: A fully-specified baseline is used verbatim
- **WHEN** `entity.db.sexual` is `{"arousal": "微興奮", "virgin": true, "sensitivity": {}}`
- **THEN** the constructed `entity.sexual.arousal.level` equals `"微興奮"` and `entity.sexual.virgin`
  is `True`

#### Scenario: An omitted optional field defaults to its vocabulary's lowest level
- **WHEN** `entity.db.sexual` omits `wetness` entirely
- **THEN** the constructed `entity.sexual.wetness.level` equals `"乾燥"` (`WETNESS_LEVELS[0]`)

### Requirement: Monster entities without an imported baseline default to 普通 sensitivity with shame clamped to 無
When `entity.db.sexual` is absent and the entity is a `Monster`, `SexualState`'s construction SHALL
build every field at its vocabulary's floor level, and SHALL clamp `shame`'s bounds so that it can
never move away from `無`. Every other field (`arousal`, `wetness`, `exposure`, `climax_phase`,
`sensitivity`) SHALL retain its full, unclamped range.

#### Scenario: A monster's shame is permanently pinned to 無
- **WHEN** a `Monster` entity with no `entity.db.sexual` baseline has `entity.sexual` read, and a
  direct attempt is made to raise its `shame` field (bypassing any rule or event — this change
  authors no rule table, so the attempt is a direct trait-value write in a test)
- **THEN** `entity.sexual.shame.level` remains `"無"`, unchanged by the attempt, because `shame`'s
  bounds were clamped to a single point at construction

#### Scenario: A monster's other fields are not clamped
- **WHEN** a `Monster` entity's `arousal` field is directly raised (via the trait's own `.value`
  setter, in a test)
- **THEN** `entity.sexual.arousal` changes exactly as it would for a non-monster entity with the same
  starting value

#### Scenario: A monster defaults to 普通 sensitivity for any body part
- **WHEN** `entity.sexual.sensitivity["尾巴"]` is read on a `Monster` for a body part never explicitly
  seeded
- **THEN** it returns an `OrderedLevelTrait` at `SENSITIVITY_LEVELS[0]` (`"普通"`)

### Requirement: sensitivity is a lazily-populated dict keyed by body part, defaulting unseen parts to 普通
`SexualState.sensitivity` SHALL behave as a mapping from body-part name to `OrderedLevelTrait`. Parts
present in an imported baseline's `sensitivity` dict SHALL be seeded at construction with their given
level; any part accessed afterward that was never seeded SHALL default to `SENSITIVITY_LEVELS[0]`
(`"普通"`) rather than raising `KeyError`.

#### Scenario: An explicitly imported part uses its given level
- **WHEN** `entity.db.sexual["sensitivity"]` is `{"私處": "極高"}`
- **THEN** `entity.sexual.sensitivity["私處"].level` equals `"極高"`

#### Scenario: An unseen part defaults to 普通 rather than raising
- **WHEN** `entity.sexual.sensitivity["耳朵"]` is read for a body part absent from the imported
  baseline
- **THEN** it returns an `OrderedLevelTrait` at level `"普通"`, and no exception is raised

### Requirement: virgin is a one-way flag; experience_types is an append-only set
`SexualState.virgin` SHALL start `True` unless the baseline explicitly sets it `False`, and once the
`SexualState` public setter sets it `False`, no later mutation through that public setter SHALL be
able to set it back to `True`.
`SexualState.experience_types` SHALL start as the baseline's given set (or empty), and SHALL only
ever grow through its public API — the handler SHALL expose no replacement or removal method.

#### Scenario: virgin cannot be reversed once false
- **WHEN** `entity.sexual.virgin` has been set to `False` through its public setter
- **THEN** every subsequent read of `entity.sexual.virgin` returns `False`, regardless of what any
  later caller or future rule attempts through the same setter

#### Scenario: experience_types only grows
- **WHEN** `"陰道性交"` has been added to `entity.sexual.experience_types`
- **THEN** it remains present in `entity.sexual.experience_types`, and no public method on
  `SexualState` replaces or removes an entry from this set

### Requirement: climax_phase can only move along its valid cycle, enforced by one guarded function
`world/rules/sexual_state.py` SHALL provide `_apply_climax_phase_set(entity, target_level)`, the sole
permitted write path for `climax_phase`'s value. It SHALL apply the mutation only when `target_level`
is a valid edge from the entity's current `climax_phase` level in the cycle
未達→接近→進行中→餘韻→未達 (plus 餘韻→接近), and SHALL no-op (leave `climax_phase` unchanged) for
any other requested target. No other function in this change's scope SHALL write `climax_phase`'s
value directly.

#### Scenario: A valid cycle transition applies
- **WHEN** `_apply_climax_phase_set(entity, "接近")` is called on an entity whose `climax_phase` is
  currently `"未達"`
- **THEN** `entity.sexual.climax_phase.level` becomes `"接近"`

#### Scenario: An invalid transition no-ops rather than applying
- **WHEN** `_apply_climax_phase_set(entity, "接近")` is called on an entity whose `climax_phase` is
  currently `"進行中"`
- **THEN** `entity.sexual.climax_phase.level` remains `"進行中"`, unchanged

#### Scenario: The afterglow-to-未達 edge and the 餘韻-to-接近 edge are both valid
- **WHEN** `_apply_climax_phase_set(entity, "未達")` or `_apply_climax_phase_set(entity, "接近")` is
  called on an entity whose `climax_phase` is currently `"餘韻"`
- **THEN** either call succeeds, changing `climax_phase` to the requested level

### Requirement: decay_tick and reset_daily_counters are exposed as plain callables with no settlement order invented
`world/rules/sexual_state.py` SHALL expose `decay_tick(entity, elapsed_seconds)` and
`reset_daily_counters(entity)` as plain callables invokable directly, with no `WorldClock` or
scheduler present. Neither function SHALL hardcode, assume, or invent any ordering between sexual
decay, trait regen, and buff ticks — that fixed settlement order remains design doc §6.5's and change
11's exclusive concern.

#### Scenario: decay_tick is invokable independently of any clock
- **WHEN** `decay_tick(entity, elapsed_seconds=3600)` is called directly in a test, with no
  `WorldClock` or scheduler present
- **THEN** it applies at most one level of decay to each configured field whose accumulated elapsed
  time has crossed its configured interval, and completes without requiring any other module to exist

#### Scenario: climax_phase's afterglow decay routes through the cycle guard
- **WHEN** `decay_tick()` decrements an entity's `climax_phase` from `"餘韻"` after its configured
  interval has accumulated
- **THEN** the mutation is applied via `_apply_climax_phase_set(entity, "未達")`, not by writing
  `climax_phase`'s underlying trait value directly

#### Scenario: reset_daily_counters resets climax_today to zero
- **WHEN** `reset_daily_counters(entity)` is called on an entity whose `climax_today` is greater than
  zero
- **THEN** `entity.sexual.climax_today` becomes `0`, and no other field changes as a result

#### Scenario: No settlement-order policy is encoded in this module
- **WHEN** `world/rules/sexual_state.py` is inspected
- **THEN** it contains no reference to trait regen scheduling or buff-tick scheduling ordering, and
  does not import or assume the existence of a `WorldClock` class

### Requirement: Change 6's self-arming combat-modifier test fires once entity.sexual is real
Once this change lands, `entity.sexual` SHALL be a live `SexualState` object whose `arousal` field
compares correctly against the vocabulary via `OrderedLevelTrait`'s operators, satisfying change 6's
`combat-modifier-table` capability's self-arming scenario without any modification to change 6's own
files.

#### Scenario: The self-arming integration test passes, not skips
- **WHEN** `world/rules/tests/test_combat_modifiers_self_arming.py::test_high_arousal_rule_fires_
  once_sexual_state_exists` is run after this change lands
- **THEN** it reports **passed**, not skipped, constructing a real entity whose `entity.sexual.
  arousal` is at or above `高度` and asserting `evaluate_combat_modifiers()` returns `high_arousal_
  agility_accuracy_penalty`'s adjustment bundle
