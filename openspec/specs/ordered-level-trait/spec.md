# ordered-level-trait Specification

## Purpose

Define the reusable ordered-level trait used by deterministic sexual-state mechanics.

## Requirements

### Requirement: OrderedLevelTrait is a from-scratch Trait subclass storing a bounded ordinal into a fixed vocabulary tuple
`world/rules/sexual_state.py` SHALL define `OrderedLevelTrait(Trait)`, registered at
`world.rules.sexual_state.OrderedLevelTrait` in `settings.TRAIT_CLASS_PATHS`. Each instance SHALL be
constructed with a `levels: tuple[str, ...]` keyword naming one of `world.lore.sexual_vocab`'s six
frozen tuples, and SHALL store its current position as an integer ordinal bounded to
`[0, len(levels) - 1]`. No `OrderedLevelTrait` instance SHALL redefine or hardcode a vocabulary of its
own — the tuple always comes from `world.lore.sexual_vocab`.

#### Scenario: A freshly constructed trait starts at the vocabulary's first level
- **WHEN** an `OrderedLevelTrait` is constructed with `levels=AROUSAL_LEVELS` and no explicit initial
  value
- **THEN** its ordinal is `0` and its `.level` property returns `"平靜"`

#### Scenario: The ordinal cannot move outside the vocabulary's bounds
- **WHEN** an `OrderedLevelTrait`'s value is set below `0` or above `len(levels) - 1`
- **THEN** it is clamped to the nearest valid bound, never raising and never storing an out-of-range
  ordinal

#### Scenario: The trait is registered in TRAIT_CLASS_PATHS
- **WHEN** `settings.TRAIT_CLASS_PATHS` is inspected
- **THEN** it contains `"world.rules.sexual_state.OrderedLevelTrait"`, the same registration
  mechanism the contrib's own `RageTrait` example uses

### Requirement: OrderedLevelTrait's .level property returns the current Chinese label
`OrderedLevelTrait` SHALL expose a `.level` property returning `self.levels[self.value]` — the
Chinese label at the trait's current ordinal.

#### Scenario: .level reflects the current ordinal
- **WHEN** an `OrderedLevelTrait` constructed with `levels=AROUSAL_LEVELS` has its value set to the
  ordinal for `"高度"`
- **THEN** `.level` returns exactly `"高度"`

### Requirement: Comparison operators accept a raw vocabulary string, another OrderedLevelTrait, or a bare ordinal
`OrderedLevelTrait` SHALL implement `__eq__`, `__ge__`, `__gt__`, `__le__`, and `__lt__` such that
comparing against a Chinese level string (resolved via the trait's own `levels` tuple), another
`OrderedLevelTrait` instance (compared by ordinal), or a bare integer ordinal all produce the correct
boolean result using Python's native comparison operators — with no special-casing required by any
caller, including `world/rules/rulebook/schema.py`'s `evaluate_condition()`.

#### Scenario: Comparison against a raw vocabulary string
- **WHEN** an `OrderedLevelTrait` at level `"高度"` is compared with `trait >= "高度"`
- **THEN** it returns `True`; comparing the same trait with `trait >= "極限"` returns `False`

#### Scenario: Comparison against another OrderedLevelTrait
- **WHEN** two `OrderedLevelTrait` instances sharing the same `levels` tuple are compared with `>=`
- **THEN** the comparison resolves by ordinal, matching what comparing their `.level` strings'
  vocabulary positions would produce

#### Scenario: Comparison against a bare ordinal
- **WHEN** an `OrderedLevelTrait` at ordinal `2` is compared with `trait >= 2`
- **THEN** it returns `True`; comparing with `trait >= 3` returns `False`

#### Scenario: evaluate_condition()'s gte comparator works against a live OrderedLevelTrait with no code change on schema.py's side
- **WHEN** `world.rules.rulebook.schema.evaluate_condition({"field": "arousal", "gte": "高度"},
  {"arousal": <OrderedLevelTrait at 高度>})` is called
- **THEN** it returns `True`, resolved entirely through Python's own `>=` operator falling through to
  `OrderedLevelTrait.__ge__`, with no branch in `schema.py` aware that `arousal` is anything but an
  orderable value

### Requirement: An unrecognized level string raises rather than silently failing
`OrderedLevelTrait`'s comparison and level-resolution methods SHALL raise when given a string that is
not a member of the trait's own `levels` tuple, rather than treating it as never-equal or
silently returning a default ordinal.

#### Scenario: Comparing against a typo'd level name raises
- **WHEN** an `OrderedLevelTrait` constructed with `levels=AROUSAL_LEVELS` is compared against the
  string `"高渡"` (a typo of `"高度"`, not a member of `AROUSAL_LEVELS`)
- **THEN** it raises `ValueError`, naming the invalid level, rather than returning `False` or `None`
