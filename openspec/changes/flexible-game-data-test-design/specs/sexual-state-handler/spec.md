# Spec Delta

## MODIFIED Requirements

### Requirement: pleasure is constructed from an imported baseline's arousal level at that level's band floor
`SexualState`'s construction SHALL read `entity.db.sexual["arousal"]` (the import contract's existing
level-string field, unchanged by this capability) and initialize the `pleasure` counter trait
(`0..100`) at that level's configured band floor from `sexual_pleasure.yaml`, defaulting to
`AROUSAL_LEVELS[0]`'s floor (`0`) when the baseline omits `arousal`.

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

#### Scenario: No-baseline construction paths default arousal to the first level
- **WHEN** no baseline is present and construction goes through the existing
  `_generic_default_baseline()` / `build_monster_sexual_baseline()` paths
- **THEN** both paths already default `arousal` to `AROUSAL_LEVELS[0]`, so `pleasure`
  initializes at that floor (`0`)

#### Scenario: Authored tuning is distinct from mechanism examples
- **WHEN** tests exercise exact numerical band, delta, duration, bias or multiplier examples in this requirement
- **THEN** scoped fixed synthetic rulebook rows provide those numbers and independently known outcomes; production rows receive valid-shape/reference/intentional-invariant checks without a copied expected balance table


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

#### Scenario: Authored tuning is distinct from mechanism examples
- **WHEN** tests exercise exact numerical band, delta, duration, bias or multiplier examples in this requirement
- **THEN** scoped fixed synthetic rulebook rows provide those numbers and independently known outcomes; production rows receive valid-shape/reference/intentional-invariant checks without a copied expected balance table


### Requirement: decay_tick decays pleasure by crossing exactly one band per configured interval
`decay_tick()`'s handling of the `pleasure` field (renamed from `arousal` in `DECAY_CONFIG`) SHALL,
once its configured interval has accumulated, move `pleasure` to one point below its current band's
floor (clamped at `0`), guaranteeing the derived `arousal` level steps down by exactly one level
regardless of where within the current band `pleasure` started ;  preserving decay's "at most one
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

#### Scenario: Authored tuning is distinct from mechanism examples
- **WHEN** tests exercise exact numerical band, delta, duration, bias or multiplier examples in this requirement
- **THEN** scoped fixed synthetic rulebook rows provide those numbers and independently known outcomes; production rows receive valid-shape/reference/intentional-invariant checks without a copied expected balance table


### Requirement: Equipment exposure bias never touches stored state

Equipment bias SHALL be an overlay at read time only: stored exposure
traits, act-driven transitions, transition rule matching, snapshots, and
persistence SHALL operate on the stored ordinal alone, and bias SHALL never
raise an exposure field-change event. Every player-facing read surface
(status read model and the status web payload alike) SHALL render the same
effective ordinal with unchanged row/payload schemas.

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

#### Scenario: Every shipped consumer is classified

- **WHEN** the structural allowlist test audits the shipped consumers of stored exposure
- **THEN** every one of them is classified (stored vs effective) in the allowlist

#### Scenario: Declaration-only vocabulary modules are exempted per-module

- **WHEN** the structural allowlist enumerates modules that name `exposure` only as
  preset-declaration vocabulary ;  authored baseline card keywords and the validator's level
  table in `world/lore/player_presets.py`
- **THEN** they are enumerated in the same structural allowlist as declaration-only exemptions:
  they construct baseline records and SHALL NOT read `entity.sexual`, stored `sexual_traits`
  state, or an effective overlay

#### Scenario: The exemption is per-module and auditable

- **WHEN** a live-state read is added to an exempt declaration-only module
- **THEN** it SHALL still be classified as a consumer

#### Scenario: Authored tuning is distinct from mechanism examples
- **WHEN** tests exercise exact numerical band, delta, duration, bias or multiplier examples in this requirement
- **THEN** scoped fixed synthetic rulebook rows provide those numbers and independently known outcomes; production rows receive valid-shape/reference/intentional-invariant checks without a copied expected balance table

