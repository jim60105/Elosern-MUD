## ADDED Requirements

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
