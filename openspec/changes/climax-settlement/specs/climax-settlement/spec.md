## ADDED Requirements

### Requirement: An entity whose climax_phase reaches 進行中 always resolves within finite settlement time
`world/rules/sexual_state.py` SHALL provide `climax_settlement_action(entity) -> str | None`, a pure
decision function returning `"extend"`, `"end"`, or `None`. Every settlement point that already calls
`world.rules.sexual_state.decay_tick()` SHALL call `climax_settlement_action(entity)` immediately
afterward and, when it returns `"extend"` or `"end"`, SHALL emit the correspondingly named event
(`climax_extended` or `climax_ends`) through `world.rules.sexual_transitions.apply_event()`. No entity
whose `climax_phase` reaches `進行中` SHALL remain there beyond the next settlement point unless an
external caller has staged an extension (see the extension-staging requirement below); absent a staged
extension, `climax_ends` SHALL fire and `climax_phase` SHALL move to `餘韻` via the existing guarded
cycle.

#### Scenario: A combat round resolves an entity that entered 進行中 with no staged extension
- **WHEN** a living, non-fled roster member's `climax_phase` is `進行中` at the start of
  `world.rules.combat.py`'s per-round upkeep, and no extension is staged
- **THEN** `climax_ends` fires for that entity during that round's upkeep, and `climax_phase` becomes
  `餘韻` by the end of the round

#### Scenario: An out-of-combat settlement quantum resolves an entity in 進行中
- **WHEN** `world.rules.clock.py`'s settlement loop processes a quantum for an entity whose
  `climax_phase` is `進行中` with no extension staged
- **THEN** `climax_ends` fires within that quantum and `climax_phase` becomes `餘韻`

#### Scenario: A long time-skip does not strand an entity in 進行中 even after every other field decays to its floor
- **WHEN** `advance()` is called with an elapsed duration spanning many settlement quanta for an entity
  whose `climax_phase` is `進行中`, and every other `DECAY_CONFIG`-tracked field (`arousal`/`pleasure`,
  `wetness`, `shame`) has already reached its configured floor before climax settlement is reached
- **THEN** the settlement loop does not exit early — `climax_settlement_action()` is still invoked for
  a subsequent quantum, and the entity's `climax_phase` resolves to `餘韻` within that same `advance()`
  call

#### Scenario: climax_settlement_action returns None and resets bookkeeping when the entity is not in 進行中
- **WHEN** `climax_settlement_action(entity)` is called on an entity whose `climax_phase` is any level
  other than `進行中`
- **THEN** it returns `None`, performs no `apply_event()`-worthy action, and leaves both `climax_turns`
  and `pending_climax_extension` at `0` (resetting either that was nonzero)

#### Scenario: climax_settlement_action is a no-op for an entity without sexual state
- **WHEN** `climax_settlement_action(entity)` is called on an entity with no sexual state handler
  (a test seam or a future non-sexual entity)
- **THEN** it returns `None` and writes nothing, so settlement paths that legitimately process such
  entities stay safe (mirroring `_has_settlement_work`'s `sexual is None` contract)

### Requirement: climax_turns counts consecutive settlement points spent in 進行中, reset on leaving it
`SexualState.climax_turns` SHALL be a read-only `int` property, incremented by exactly `1` each time
`climax_settlement_action()` is called while `climax_phase` is `進行中`, and reset to `0` the moment
`climax_phase` is observed to be anything else.

#### Scenario: climax_turns increments once per settlement point spent in 進行中
- **WHEN** `climax_settlement_action(entity)` is called three times in succession while the entity
  remains in `進行中` for all three (via staged extensions)
- **THEN** `entity.sexual.climax_turns` equals `3` after the third call

#### Scenario: climax_turns resets to zero once the entity leaves 進行中
- **WHEN** `entity.sexual.climax_turns` is nonzero and `climax_settlement_action()` is subsequently
  called after the entity's `climax_phase` has moved to `餘韻`
- **THEN** `entity.sexual.climax_turns` equals `0`

### Requirement: pending_climax_extension is staged additively through one sole mutator and consumed one at a time
`SexualState` SHALL provide `stage_climax_extension(count: int = 1) -> None` as the sole write path
for a new `pending_climax_extension` counter, adding `count` to its current value; `count` SHALL be a
positive `int` (`>= 1`), and any other value SHALL raise `ValueError` without changing the counter.
`SexualState` SHALL expose `pending_climax_extension` as a read-only `int` property. Each call to
`climax_settlement_action()` that observes `climax_phase == 進行中` and `pending_climax_extension > 0`
SHALL decrement it by exactly `1`, return `"extend"`, and leave the entity in `進行中` (no
`climax_phase` transition); a zero value SHALL instead yield `"end"`. Whenever a settlement transaction
is rolled back, `pending_climax_extension`, `climax_turns`, and the two lifetime counters SHALL be
restored to their pre-transaction values exactly as the existing sexual surfaces are.

#### Scenario: A single staged extension is consumed on the next settlement point
- **WHEN** `stage_climax_extension()` is called once while the entity's `climax_phase` is `進行中`, and
  `climax_settlement_action(entity)` is then called
- **THEN** it returns `"extend"`, `entity.sexual.pending_climax_extension` becomes `0`, and
  `climax_phase` remains `進行中`

#### Scenario: Multiple staged extensions are consumed one settlement point at a time
- **WHEN** `stage_climax_extension(count=3)` is called once while the entity's `climax_phase` is
  `進行中`, and `climax_settlement_action(entity)` is then called three times in succession (with the
  entity remaining in `進行中` throughout)
- **THEN** each of the three calls returns `"extend"`, and a fourth call (with no further staging)
  returns `"end"`

#### Scenario: A stage made while not in 進行中 does not silently carry forward
- **WHEN** `stage_climax_extension()` is called while the entity's `climax_phase` is `接近` (not yet
  `進行中`), and `climax_settlement_action(entity)` is subsequently called while the phase is still not
  `進行中`
- **THEN** `entity.sexual.pending_climax_extension` is reset to `0` by that call, not carried forward
  to a later entry into `進行中`

#### Scenario: A non-positive or non-integral stage count fails loudly
- **WHEN** `stage_climax_extension()` is called with `count` of `0`, a negative value, or a
  non-integer
- **THEN** it raises `ValueError` and `pending_climax_extension` is left unchanged

#### Scenario: A rolled-back settlement restores the new bookkeeping fields
- **WHEN** a transaction that called `climax_settlement_action()` (an outer `advance()` transaction,
  an action commit, or a combat-session round) fails and is rolled back
- **THEN** `climax_turns`, `pending_climax_extension`, and the two lifetime counters are restored to
  their pre-transaction persisted values, exactly as `virgin`/`experience_types` are

### Requirement: climax_extended costs half of climax_ends' stamina and does not change climax_phase
`world/rules/rulebook/sexual.yaml` SHALL declare `sp_cost_on_climax_extension`, triggered by the
`climax_extended` event, applying a negative integer SP delta in the range `-15` to `-10` (half of
`sp_cost_on_climax`'s `-30` to `-20` range) to `entity.traits.sp.current`, subject to the same gauge
floor `sp_cost_on_climax` already respects. No rule triggered by `climax_extended` SHALL target
`climax_phase`.

#### Scenario: An extension costs stamina in the documented half range
- **WHEN** `apply_event(entity, "climax_extended", rng=<fixed-value stub returning -12>)` is called
- **THEN** `entity.traits.sp.value` decreases by exactly `12`

#### Scenario: An extension respects the stamina gauge's own floor
- **WHEN** `apply_event(entity, "climax_extended")` fires on an entity whose `sp` is below the rule's
  delta magnitude
- **THEN** `entity.traits.sp.value` stops at its own configured floor rather than going negative

#### Scenario: climax_extended never moves climax_phase
- **WHEN** `world/rules/rulebook/sexual.yaml` is inspected for every rule triggered by the
  `climax_extended` event
- **THEN** none of them target `climax_phase`

### Requirement: 高潮次數 and 連續高潮次數 increment exactly once per climax_ends/climax_extended
The entity's lifetime climax counter (`高潮次數`) SHALL increment by exactly one each time
`climax_settlement_action()` returns `"end"`. The entity's lifetime climax-extension counter
(`連續高潮次數`) SHALL increment by exactly one each time it returns `"extend"`. Neither counter
SHALL be incremented by any other call.

#### Scenario: An unstaged resolution increments only the climax counter
- **WHEN** `climax_settlement_action(entity)` returns `"end"`
- **THEN** the entity's lifetime climax counter increases by exactly `1`, and its lifetime
  extension counter is unchanged

#### Scenario: A consumed extension increments only the extension counter
- **WHEN** `climax_settlement_action(entity)` returns `"extend"`
- **THEN** the entity's lifetime extension counter increases by exactly `1`, and its lifetime climax
  counter is unchanged

### Requirement: penetrative_sex_with_male mirrors the shipped female counterpart and never touches virgin
`world/rules/rulebook/sexual.yaml` SHALL declare `experience_gay_added`, triggered by the
`penetrative_sex_with_male` event, adding `男男性愛` to `entity.sexual.experience_types` — the same
shape as the shipped `experience_lesbian_added` (`penetrative_sex_with_female` → `女女性愛`). Neither
rule SHALL target `virgin`; only `virginity_once`, triggered by `first_vaginal_penetration`, SHALL
continue to do so.

#### Scenario: A male-male event adds the corresponding experience type
- **WHEN** `apply_event(entity, "penetrative_sex_with_male")` is called
- **THEN** `entity.sexual.experience_types` contains `男男性愛`

#### Scenario: The male-male event does not break virginity
- **WHEN** `apply_event(entity, "penetrative_sex_with_male")` is called on an entity whose `virgin` is
  `True`
- **THEN** `entity.sexual.virgin` remains `True` afterward

#### Scenario: The two same-sex rules are symmetric in shape
- **WHEN** `experience_lesbian_added` and `experience_gay_added` are inspected in
  `sexual.yaml`
- **THEN** both target only `experience_types` with an `add` effect, and neither carries a `then`
  clause targeting any other field
