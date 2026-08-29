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

### Requirement: pleasure is constructed from an imported baseline's arousal level at that level's band floor
`SexualState`'s construction SHALL read `entity.db.sexual["arousal"]` (the import contract's existing
level-string field, unchanged by this capability) and initialize the `pleasure` counter trait
(`0..100`) at that level's configured band floor from `sexual_pleasure.yaml`, defaulting to
`AROUSAL_LEVELS[0]`'s floor (`0`) when the baseline omits `arousal` or when no baseline is present
(the existing `_generic_default_baseline()` / `build_monster_sexual_baseline()` paths, both of which
already default `arousal` to `AROUSAL_LEVELS[0]`).

#### Scenario: An imported arousal level resolves to its band floor
- **WHEN** `entity.db.sexual` is `{"arousal": "微興奮", "virgin": true, "sensitivity": {}}`
- **THEN** the constructed `entity.sexual.pleasure.value` equals `15` (`微興奮`'s configured band
  floor), and `entity.sexual.arousal.level` equals `"微興奮"`

#### Scenario: An omitted arousal defaults to the floor level's pleasure floor
- **WHEN** `entity.db.sexual` omits `arousal` entirely
- **THEN** the constructed `entity.sexual.pleasure.value` equals `0`

#### Scenario: A Monster with no imported baseline starts at pleasure 0
- **WHEN** a `Monster` entity with no `entity.db.sexual` baseline has `entity.sexual` read
- **THEN** `entity.sexual.pleasure.value` equals `0`, and `entity.sexual.arousal.level` equals
  `"平靜"`

### Requirement: pleasure is bounded 0 to 100 and every mutation clamps at those bounds
`SexualState.pleasure` SHALL be a counter trait bounded `min=0, max=100`. No mutation path — decay,
a rule's `delta` or `set` effect, or any future direct write — SHALL be able to move it outside that
range; the trait's own bound enforcement SHALL be the sole clamping mechanism, with no additional
clamping logic duplicated elsewhere.

#### Scenario: A delta that would exceed 100 clamps at 100
- **WHEN** `entity.sexual.pleasure.value` is `95` and a mutation applies a `delta` of `+14`
- **THEN** `entity.sexual.pleasure.value` becomes exactly `100`, not `109`

#### Scenario: A delta that would go below 0 clamps at 0
- **WHEN** `entity.sexual.pleasure.value` is `5` and a mutation applies a `delta` of `-20`
- **THEN** `entity.sexual.pleasure.value` becomes exactly `0`, not a negative number

### Requirement: arousal is a derived, read-only view over pleasure, comparable exactly as before
`SexualState.arousal` SHALL be a read-only property computed from `pleasure.value` via
`sexual_pleasure.yaml`'s five-band lookup table, exposing the same comparison surface
`OrderedLevelTrait` exposes (`.value`, `.level`, `.levels`, `==`, `>=`, `>`, `<=`, `<`) so that every
existing reader of `entity.sexual.arousal` continues to receive correct answers with no change to
that reader. Direct assignment to `entity.sexual.arousal.value` SHALL raise rather than silently
succeeding or no-op'ing.

#### Scenario: arousal reads the correct level for a mid-band pleasure value
- **WHEN** `entity.sexual.pleasure.value` is `72`
- **THEN** `entity.sexual.arousal.level` equals `"高度"` (the band covering `60..84`)

#### Scenario: arousal comparisons against the vocabulary work exactly as before
- **WHEN** `entity.sexual.pleasure.value` is `90`
- **THEN** `entity.sexual.arousal >= "高度"` is `True` and `entity.sexual.arousal == "極限"` is `True`,
  matching the comparisons a live `OrderedLevelTrait` at the same conceptual level would have
  returned

#### Scenario: Direct assignment to arousal raises
- **WHEN** `entity.sexual.arousal.value = 3` is attempted
- **THEN** it raises `AttributeError`, rather than silently succeeding or leaving `pleasure`
  unaffected

### Requirement: decay_tick decays pleasure by crossing exactly one band per configured interval
`decay_tick()`'s handling of the `pleasure` field (renamed from `arousal` in `DECAY_CONFIG`) SHALL,
once its configured interval has accumulated, move `pleasure` to one point below its current band's
floor (clamped at `0`), guaranteeing the derived `arousal` level steps down by exactly one level
regardless of where within the current band `pleasure` started — preserving decay's "at most one
level of decay per configured field" behaviour as an observable arousal-level effect.

#### Scenario: Decay from the middle of a band crosses to the band below
- **WHEN** `decay_tick(entity, elapsed_seconds=1800)` is called once on an entity whose `pleasure` is
  `72` (mid-`高度` band, `60..84`)
- **THEN** `entity.sexual.pleasure.value` becomes `59` (one below `高度`'s floor of `60`), and
  `entity.sexual.arousal.level` becomes `"中等"`

#### Scenario: Decay at the floor band clamps at pleasure 0
- **WHEN** `decay_tick(entity, elapsed_seconds=1800)` is called on an entity whose `pleasure` is
  already within `平靜`'s band (`0..14`)
- **THEN** `entity.sexual.pleasure.value` becomes `0`, not negative

#### Scenario: Decay never crosses more than one band per interval, regardless of elapsed time
- **WHEN** `decay_tick(entity, elapsed_seconds=1800)` is called exactly once (one interval's worth of
  accumulated time) on an entity whose `pleasure` is `85` (`極限` band)
- **THEN** `entity.sexual.arousal.level` becomes `"高度"`, not `"中等"` or lower, even though `85`
  crossing to `84` numerically also crosses into a band whose own floor is far below `85`

### Requirement: SexualState exposes eleven independent, unbounded, lifetime behaviour counters, each with exactly one sanctioned mutator
`SexualState` SHALL expose exactly the eleven counter fields below, each an unbounded (`min=0`, no
`max`) counter starting at `0` for every entity regardless of any imported baseline, each readable
through its own property, and each mutable **only** through its own named method, which SHALL
increment it by exactly `1`. No rule, effect handler, or other caller SHALL be able to increment,
decrement, or reset any of the eleven through any path other than its named mutator. None of the
eleven SHALL be reset by `reset_daily_counters()`.

| Field | Mutator |
|---|---|
| `masturbation_count` | `record_masturbation()` |
| `toy_use_count` | `record_toy_use()` |
| `exposure_act_count` | `record_exposure_act()` |
| `watched_count` | `record_watched()` |
| `duo_act_count` | `record_duo_act()` |
| `group_act_count` | `record_group_act()` |
| `hostile_act_count` | `record_hostile_act()` |
| `restraint_count` | `record_restraint()` |
| `interspecies_act_count` | `record_interspecies_act()` |
| `climax_count` | `record_climax_count()` |
| `climax_extension_count` | `record_climax_extension()` |

#### Scenario: Every counter starts at zero regardless of baseline
- **WHEN** `entity.sexual` is read for the first time on any entity, imported or not, `Monster` or
  not
- **THEN** all eleven counter properties above equal `0`

#### Scenario: A mutator increments only its own counter by exactly one
- **WHEN** `entity.sexual.record_masturbation()` is called once
- **THEN** `entity.sexual.masturbation_count` equals `1`, and every one of the other ten counters is
  unchanged

#### Scenario: Repeated calls accumulate linearly
- **WHEN** `entity.sexual.record_hostile_act()` is called five times in sequence
- **THEN** `entity.sexual.hostile_act_count` equals exactly `5`

#### Scenario: No counter is reset by reset_daily_counters
- **WHEN** `reset_daily_counters(entity)` is called on an entity whose `climax_count` is `3` and
  whose `restraint_count` is `7`
- **THEN** `entity.sexual.climax_count` remains `3` and `entity.sexual.restraint_count` remains `7`
  afterward — only `climax_today` (unchanged by this capability) is affected

#### Scenario: climax_count is independent of the existing daily climax_today counter
- **WHEN** `entity.sexual.record_climax()` (the existing, unmodified mutator) is called, without also
  calling `entity.sexual.record_climax_count()`
- **THEN** `entity.sexual.climax_today` increases as it already did before this capability, and
  `entity.sexual.climax_count` is unaffected — the two counters are mutated independently, and no
  call to either mutator has a side effect on the other's field

#### Scenario: No counter is reachable through SexualState's private TraitHandler
- **WHEN** any module outside `world/rules/sexual_state.py` is inspected
- **THEN** no line references `entity.sexual._traits` (or any other leading-underscore attribute of
  `SexualState`) to read or write any of the eleven counters — every access goes through the named
  property or mutator

### Requirement: SexualState.unlocked_act_keys() gates the sexual act catalogue by counter thresholds, or unlocks it entirely for a mastery holder
`SexualState` SHALL expose `unlocked_act_keys() -> frozenset[str]`, returning every key in
`SEXUAL_ACT_REGISTRY` whose `unlock` mapping's thresholds are all met by the entity's own lifetime
counters, **or** the entire `SEXUAL_ACT_REGISTRY` keyset **minus every act whose paired `SkillDef`
declares `requires_divine_arts=True`** when the entity directly owns any skill whose parsed effects
include a `SexualMasteryEffect`. The mastery check SHALL consult `entity.skills.base_owned_keys()`,
never `entity.skills.owned_keys()` and never `entity.skills.conferred_grants()`.

#### Scenario: An act unlocks when every one of its thresholds is met
- **WHEN** `unlocked_act_keys()` is read on an entity whose counters meet every threshold in one
  act's `unlock` mapping
- **THEN** that act's key is present in the returned set

#### Scenario: An act stays locked when any one threshold is unmet
- **WHEN** `unlocked_act_keys()` is read on an entity whose counters meet every threshold in one
  act's `unlock` mapping except one
- **THEN** that act's key is absent from the returned set

#### Scenario: A seed act with an empty unlock mapping is always present
- **WHEN** `unlocked_act_keys()` is read on an entity with every counter at zero
- **THEN** every act whose `unlock` mapping is empty is present in the returned set

#### Scenario: Direct ownership of a SexualMasteryEffect-bearing skill unlocks the entire catalogue except divine acts
- **WHEN** `unlocked_act_keys()` is read on an entity whose `entity.skills.base_owned_keys()` includes
  a skill carrying `SexualMasteryEffect`, regardless of that entity's counter values
- **THEN** the returned set equals the full `SEXUAL_ACT_REGISTRY` keyset minus every act whose paired
  `SkillDef` declares `requires_divine_arts=True`

#### Scenario: A conferred, not directly owned, mastery grant does not unlock the catalogue
- **WHEN** an entity's `entity.skills.conferred_grants()` includes a fractional grant of a
  `SexualMasteryEffect`-bearing skill, but that skill's key is absent from
  `entity.skills.base_owned_keys()`
- **THEN** `unlocked_act_keys()` does not apply the blanket unlock, and returns only the acts whose
  counter thresholds are independently met

#### Scenario: The mastery check does not read owned_keys()
- **WHEN** `unlocked_act_keys()`'s implementation is inspected
- **THEN** its mastery-ownership check calls `entity.skills.base_owned_keys()`, and no line in that
  check calls `entity.skills.owned_keys()`

### Requirement: saturate_sensitivity() pins every resolvable body part to the top sensitivity level
`SexualState.saturate_sensitivity()` SHALL set every `world.lore.sexual_vocab.BODY_PARTS` member's
sensitivity to `SENSITIVITY_LEVELS[-1]` (`敏感異常`) for a non-`Monster` entity. For a `Monster`
entity, it SHALL set only the `GENERIC_BODY_PART` sensitivity entry, matching `resolve_part`'s
existing unconditional collapse of every `Monster` target to that one channel.

#### Scenario: Every named body part reaches the top sensitivity level
- **WHEN** `entity.sexual.saturate_sensitivity()` is called on a non-`Monster` entity
- **THEN** `entity.sexual.sensitivity[part].level` equals `"敏感異常"` for every `part` in
  `BODY_PARTS`

#### Scenario: A Monster entity gains only the generic channel
- **WHEN** `entity.sexual.saturate_sensitivity()` is called on a `Monster` entity
- **THEN** `entity.sexual.sensitivity[GENERIC_BODY_PART].level` equals `"敏感異常"`, and no named
  `BODY_PARTS` member is present in that entity's `sensitivity.items()`

### Requirement: clamp_shame_to(level) permanently pins shame's bounds and current value to one level, rejecting a Monster target
`SexualState.clamp_shame_to(level)` SHALL set `shame`'s `min`, `max`, and current `value` all to
`level`'s ordinal, using the same `OrderedLevelTrait` bound-setter mechanism `SexualState.__init__`
already uses to pin a `Monster`'s `shame` at the floor. It SHALL raise `ValueError` without mutating
any state when called on a `Monster` entity, whose `shame` bounds are already permanently pinned to
the floor by construction.

#### Scenario: shame is pinned at the target level and cannot subsequently move
- **WHEN** `entity.sexual.clamp_shame_to("成癮")` is called on a non-`Monster` entity, followed by any
  attempt to change `entity.sexual.shame.value` (directly, or via `decay_tick`)
- **THEN** `entity.sexual.shame.level` reads `"成癮"` both immediately after the call and after the
  subsequent attempt, unchanged

#### Scenario: Calling clamp_shame_to on a Monster is rejected, not silently applied
- **WHEN** `entity.sexual.clamp_shame_to("成癮")` is called on a `Monster` entity
- **THEN** it raises `ValueError` and that entity's `shame` bounds remain `min=max=0` (`"無"`),
  unchanged from construction

### Requirement: mark_submission(caster_key) grows an append-only submission_marks set, defaulting to empty
`SexualState.mark_submission(caster_key)` SHALL add `caster_key` to a `submission_marks` frozenset
stored in the existing `sexual_state` attribute category, without removing any previously-added key.
An entity with no prior `mark_submission()` call SHALL read `submission_marks` as an empty frozenset,
with no baseline-import seeding required.

#### Scenario: Marking adds the caster's key without removing any other
- **WHEN** `entity.sexual.mark_submission("alice")` is called, followed by
  `entity.sexual.mark_submission("bob")`
- **THEN** `entity.sexual.submission_marks` equals `frozenset({"alice", "bob"})`

#### Scenario: An unmarked entity reads an empty set
- **WHEN** `entity.sexual.submission_marks` is read on an entity that has never had `mark_submission()`
  called
- **THEN** it returns `frozenset()`

### Requirement: restore_purity() bypasses the public virgin setter without weakening its one-way contract
`SexualState.restore_purity()` SHALL set `virgin` to `True` by writing the underlying attribute
directly, bypassing the public `virgin` property's setter (which is unconditionally a no-op once
`virgin` is `False`). It SHALL NOT modify `experience_types`. Calling it on an entity whose `virgin` is
already `True` SHALL be a no-op producing no error.

#### Scenario: restore_purity reverses a False virgin flag
- **WHEN** `entity.sexual.virgin` has been set to `False` through the public setter, and
  `entity.sexual.restore_purity()` is then called
- **THEN** `entity.sexual.virgin` reads `True` afterward

#### Scenario: experience_types is unaffected by restore_purity
- **WHEN** `entity.sexual.experience_types` contains `"陰道性交"` and `entity.sexual.restore_purity()`
  is called
- **THEN** `entity.sexual.experience_types` still contains `"陰道性交"`, unchanged

#### Scenario: The public setter's one-way guarantee still holds after restore_purity exists
- **WHEN** `entity.sexual.virgin` is set to `False` through the public setter, `restore_purity()` is
  called (setting it back to `True`), and then the public setter is used to attempt setting it `False`
  and then `True` again
- **THEN** the public setter's own existing scenario still holds unmodified: once the public setter
  itself sets `virgin` to `False`, no later mutation through that same public setter can set it back to
  `True` — `restore_purity()` is a separate path and does not change this

#### Scenario: restore_purity on an already-virgin entity is a no-op, not an error
- **WHEN** `entity.sexual.restore_purity()` is called on an entity whose `virgin` is already `True`
- **THEN** `entity.sexual.virgin` remains `True` and no exception is raised

### Requirement: Equipment exposure bias never touches stored state

Equipment bias SHALL be an overlay at read time only: stored exposure
traits, act-driven transitions, transition rule matching, snapshots, and
persistence SHALL operate on the stored ordinal alone, and bias SHALL never
raise an exposure field-change event. Every player-facing read surface
(status read model and the status web payload alike) SHALL render the same
effective ordinal with unchanged row/payload schemas. Every shipped consumer
of stored exposure SHALL be classified (stored vs effective) in a structural
allowlist test, and a new raw consumer outside the allowlist SHALL fail it.

#### Scenario: Progression ignores what is worn

- **WHEN** an exposure-raising act resolves for an actor wearing a bias +2
  item and then the item is removed
- **THEN** the stored ordinal advanced exactly as with no equipment, no
  exposure field-change event was raised by equipping or unequipping, and
  effective exposure drops back to the stored value

#### Scenario: Status row and web payload agree on the effective band

- **WHEN** the status read model and the web status payload render an actor
  wearing bias-granting equipment
- **THEN** both show the same effective ordinal, schemas unchanged, while
  the stored trait remains as-is

#### Scenario: New raw consumer is rejected by the allowlist

- **WHEN** a new module reads the stored exposure trait outside the
  stored-classified allowlist
- **THEN** the structural test fails until it is classified
