# buff-handler-integration Specification

## Purpose
TBD - created by archiving change buffs-rulebook. Update Purpose after archive.
## Requirements
### Requirement: entity.buffs is mounted as the real BuffHandler, replacing the change-3 placeholder
`LivingEntity` SHALL mount `evennia.contrib.rpg.buffs.BuffHandler` as a read-only computed property named
`entity.buffs`, replacing change 3's `None`-defaulting `AttributeProperty` placeholder. `entity.buffs`
SHALL have no bare-assignment form, matching `entity.traits`/`entity.skills`/`entity.equipment`. No
function added by this change SHALL assign a raw dict or any other payload directly to `entity.buffs` or
to `entity.db.buffs`.

#### Scenario: entity.buffs returns a BuffHandler instance
- **WHEN** `entity.buffs` is read on any `LivingEntity` instance
- **THEN** it returns a `BuffHandler` instance bound to that entity, not `None` and not a raw dict

#### Scenario: entity.buffs has no bare-assignment form
- **WHEN** code attempts `entity.buffs = {...}`
- **THEN** it raises, since `buffs` is a read-only computed property, matching `entity.traits`'s own
  behavior

#### Scenario: No module added by this change writes a raw payload to entity.buffs or entity.db.buffs
- **WHEN** `world/rules/buffs.py` and `world/rules/combat_modifiers.py` are inspected
- **THEN** neither contains an assignment of the form `entity.buffs = ...` or
  `entity.db.buffs = ...`; every mutation of buff state goes through `BuffHandler`'s own `.add()`/
  `.remove()` API

### Requirement: Buff definitions configure a subset of rate of change, clamped bounds, and decay rate
— never a combat-stat multiplier
`world/rules/rulebook/buffs.yaml` SHALL define each buff's tunable parameters (duration, tick interval,
stacking policy, and a `modifiers` mapping using at most the keys `rate`, `bounds`, and `decay`) per
design doc §6.4's exhaustive list of what a buff may modify. A buff definition SHALL NOT configure a
combat-stat multiplier (`atk_phys`/`agility`/`defense` scaling) — that remains change 5's
`SkillHandler.effective_value()` territory. A buff MAY declare an empty `modifiers` mapping when its
sole purpose is being detectable as present (a marker buff).

#### Scenario: A rate-of-change buff definition is well-formed
- **WHEN** `buffs.yaml`'s `poisoned` definition is inspected
- **THEN** its `modifiers` mapping contains a `rate` key naming a target field and a per-tick delta, and
  contains neither `bounds` nor a combat-stat-multiplier key

#### Scenario: A marker-only buff definition has an empty modifiers mapping
- **WHEN** `buffs.yaml`'s `paralysis` and `fear` definitions are inspected
- **THEN** each has an empty `modifiers` mapping, and each is still loadable and applyable via
  `BuffHandler`

#### Scenario: No buff definition configures a combat-stat multiplier
- **WHEN** every entry in `buffs.yaml` is inspected
- **THEN** none contains a `modifiers` key resembling a multiplicative combat-stat scale (e.g.
  `atk_phys_multiplier`); combat-facing consequences of a buff's presence are expressed exclusively
  through `combat_modifiers.yaml`'s separate table, never through a buff definition's own `modifiers`

### Requirement: A rate-of-change modifier can be conferred from one entity to another as a buff
instance carrying a source and a scale
`world/rules/buffs.py` SHALL provide `grant_conferred_growth_rate(entity, source_key, scale)`, which
applies the single `RulebookBuff` class via `BuffHandler.add()`, using a source-qualified instance key
and `to_cache` data carrying `definition_key="conferred_growth_rate"`, the supplied `source_key`, and
the supplied `scale`. This function SHALL perform no ownership or resource check — it is a
plain, unconditional data write, mirroring change 5's `grant_conferred()` for `ConferredSkillGrant`. The
conferred growth-rate modifier SHALL NOT be represented as a new dataclass parallel to change 5's
`ConferredSkillGrant`; it SHALL be represented as a `BuffHandler`-managed buff instance.

#### Scenario: Granting a conferred growth rate applies a buff instance
- **WHEN** `grant_conferred_growth_rate(violet, source_key="elosia", scale=0.5)` is called
- **THEN** `violet.buffs` subsequently reports a `conferred_growth_rate` buff active, carrying
  `source_key="elosia"` and `scale=0.5`

#### Scenario: Granting performs no ownership or resource check
- **WHEN** `grant_conferred_growth_rate(entity, source_key="nonexistent_entity_key", scale=0.5)` is
  called
- **THEN** it succeeds without raising, exactly mirroring `grant_conferred()`'s documented behavior for
  an unknown `source_key`

#### Scenario: No parallel dataclass exists for this mechanism
- **WHEN** `world/rules/buffs.py` is inspected
- **THEN** it contains no dataclass definition resembling `ConferredRateGrant` or similar — the
  mechanism is implemented entirely through `BuffHandler`/`BaseBuff`

### Requirement: growth_rate_multiplier() is a pure query folding every active conferred growth-rate
buff's scale
`world/rules/buffs.py` SHALL provide `growth_rate_multiplier(entity) -> float`, returning the product of
every currently-active `conferred_growth_rate` buff's `scale` on that entity, or `1.0` when none is
active. This function SHALL NOT write to `entity.traits`, `entity.buffs`, or any other entity attribute.

#### Scenario: A single active conferred growth-rate buff yields its scale
- **WHEN** `growth_rate_multiplier(violet)` is called after `grant_conferred_growth_rate(violet,
  source_key="elosia", scale=0.5)` has been applied
- **THEN** it returns `0.5`

#### Scenario: No active conferred growth-rate buff yields the identity multiplier
- **WHEN** `growth_rate_multiplier(entity)` is called on an entity with no `conferred_growth_rate` buff
  active
- **THEN** it returns `1.0`

#### Scenario: Calling the query does not mutate entity state
- **WHEN** `growth_rate_multiplier(entity)` is called any number of times in sequence
- **THEN** the entity's active buff set and every `entity.traits.<key>.value` remain unchanged after
  each call

### Requirement: The conferred growth-rate buff's tick is a documented no-op, consumed by pull rather
than push
`_apply_rate_modifier()` SHALL treat `magic_level_growth` (the `conferred_growth_rate` buff's declared
`rate` target) as an explicit, documented no-op on tick, not an unimplemented or erroring case. The
buff's `scale` SHALL be consumed exclusively by pull, through `growth_rate_multiplier(entity)` (read by
change 11b's `effective_magic_growth_multiplier()` at the moment progression is computed), and SHALL
NOT be additionally applied as a per-tick effect. This SHALL be stated in `_apply_rate_modifier()`'s own
docstring, naming `growth_rate_multiplier()`/change 11b as the actual reader, so a future edit does not
reintroduce a push-side application and double-count the scale.

#### Scenario: Ticking a conferred growth-rate buff completes without raising
- **WHEN** `tick_buffs(entity)` is called on an entity holding an active `conferred_growth_rate` buff
  (applied via `grant_conferred_growth_rate`)
- **THEN** it completes without raising `NotImplementedError` or any other exception

#### Scenario: Ticking a conferred growth-rate buff leaves magic_level untouched
- **WHEN** `tick_buffs(entity)` is called on an entity holding an active `conferred_growth_rate` buff
- **THEN** `entity.traits.magic_level.value` is unchanged before and after the call, and no other
  entity attribute is mutated as a result of this buff's tick

#### Scenario: The no-op is documented as intentional, not a placeholder gap
- **WHEN** `_apply_rate_modifier()`'s docstring is inspected for the `magic_level_growth` branch
- **THEN** it states that the value is read by pull through `growth_rate_multiplier()` (change 11b's
  `effective_magic_growth_multiplier()`), and that applying it again on tick would double-apply the
  conferred scale

### Requirement: A declared, unbuilt seam exists for buff-forbidden actions
`world/rules/buffs.py` SHALL provide `blocks_action(entity) -> bool`, returning whether any currently
active buff key is in a small, explicit blocking set (at minimum `paralysis`). This function SHALL NOT
itself reject, cancel, or otherwise interact with any action — it is a query for change 8's
`ActionResolver` (design doc §6.1 step 4) to call.

#### Scenario: An active blocking buff is detected
- **WHEN** `blocks_action(entity)` is called on an entity with `paralysis` currently active
- **THEN** it returns `True`

#### Scenario: No active blocking buff yields False
- **WHEN** `blocks_action(entity)` is called on an entity with no buff in the blocking set active (e.g.
  only `fear` active)
- **THEN** it returns `False`

#### Scenario: blocks_action() has no side effect
- **WHEN** `blocks_action(entity)` is called
- **THEN** no entity attribute changes as a result, and no action, resolution, or resolution-pipeline
  code is invoked by this function

### Requirement: Buff tick is exposed as a plain callable, with no settlement order invented
`world/rules/buffs.py` SHALL expose buff-tick behavior as a plain callable that a caller (change 11's
world clock) can invoke explicitly. This change SHALL NOT hardcode, assume, or invent any ordering
between buff ticks, trait regen, and sexual-state decay — that fixed settlement order is design doc
§6.5's and change 11's exclusive concern. The callable SHALL still apply each active buff's rate
modifier on tick, and SHALL additionally return an ordered tuple of damaging tick records — one per
applied rate tick whose modifier targets `hp` with a negative delta — each carrying the definition
key, the buff cache's `source_pk` (or `None`), the delta, and the entity's HP immediately before that
tick applied. A caller that ignores the return value SHALL observe identical state changes to the
pre-change callable.

#### Scenario: Buff tick is invokable independently of any clock
- **WHEN** the buff-tick callable is invoked directly in a test, without any `WorldClock` or scheduler
  present
- **THEN** it applies exactly one tick's worth of each active buff's rate modifier (e.g. `poisoned`
  reduces `hp` by its configured per-tick delta once) and completes without requiring any other module
  to exist

#### Scenario: No settlement-order policy is encoded in this change's modules
- **WHEN** `world/rules/buffs.py` and `world/rules/combat_modifiers.py` are inspected
- **THEN** neither contains a reference to trait regen scheduling or sexual-state decay scheduling, and
  neither module imports or assumes the existence of `world/rules/sexual_state.py` or a `WorldClock`
  class

#### Scenario: A damaging tick returns one ordered record
- **WHEN** `tick_buffs(entity, 10)` fires both `poisoned` and `fire_scorch` in one call on a living entity
- **THEN** it returns two records in application order, each carrying the definition key, the buff cache's `source_pk` (or `None`), delta `-5`, and the entity's HP immediately before that tick applied

#### Scenario: Non-damaging ticks return no records
- **WHEN** `tick_buffs(entity)` fires only marker buffs or the conferred growth-rate buff
- **THEN** it returns an empty tuple and applies the rate modifier exactly as before

### Requirement: Action-workflow debuff grants are neutralized by worn equipment immunity
When the action-resolution workflow would grant a debuff-polarity buff to a target whose worn equipment confers immunity to that buff key, the staged effect SHALL be a non-mutating neutralization with a stable `equipment_immune|<entity>|<buff_key>` event tag and Traditional-Chinese renderer text visible to actor and target, and the buff storage SHALL be untouched. The buff-grant chokepoint SHALL independently refuse the write for immune targets as a defense-in-depth backstop. Immunity rejects only new grants while worn: it SHALL NOT remove, pause, or alter already-applied debuffs. Buff-polarity grants and entities without equipment SHALL be unaffected.

#### Scenario: Poisoned strike lands but does not apply
- **WHEN** a skill would apply `poisoned` to an actor wearing 淨化吊墜
- **THEN** no buff instance exists afterwards, the event log records the stable neutralization for both sides, and the action's damage settled normally

#### Scenario: Existing poison survives equipping the pendant
- **WHEN** an already-poisoned actor equips 淨化吊墜 and rounds tick
- **THEN** the poison keeps ticking exactly as before and the pendant prevents only new debuff grants

#### Scenario: Buff-polarity grants bypass the gate
- **WHEN** an ally applies `focus` to the same actor
- **THEN** the buff applies normally with no neutralization event

#### Scenario: Repeated attempts never half-apply
- **WHEN** the immune target is hit by three separate poison casts in one round
- **THEN** buff storage is unchanged after all three and each attempt produced its own neutralization event

### Requirement: Damaging rate buffs persist a validated effect-source identity in the buff cache
`_handle_buff_apply` SHALL persist the resolving actor's dbref as `source_pk` in the buff cache whenever the applied definition's `rate` modifier damages HP (target `hp` with a negative delta). The value SHALL be derived from the actor inside the handler; a caller-supplied `source_pk` in `buff_kwargs` SHALL NOT override it, and an actor without a resolvable positive-int dbref SHALL reject the action before commit. Buff instances created outside the handler (for example direct `_add_buff` calls) MAY lack `source_pk`, in which case their rate ticks are unattributed.

#### Scenario: Applying fire_scorch stores the caster's dbref
- **WHEN** `_handle_buff_apply` resolves `buff:fire_scorch` for a target in combat
- **THEN** the target's buff cache entry carries `source_pk` equal to the caster's dbref, readable on the buff instance

#### Scenario: Caller-supplied source identity cannot spoof attribution
- **WHEN** a `buff_kwargs` value supplies `source_pk` naming a different entity than the actor
- **THEN** the cached `source_pk` is the actor's dbref, never the supplied value

#### Scenario: An actor without a resolvable dbref rejects the damaging buff application
- **WHEN** `_handle_buff_apply` stages a damaging buff for an actor with no positive-int pk
- **THEN** the action rejects before commit and no buff is added

#### Scenario: Reapplying a damaging buff replaces the source with the new caster
- **WHEN** the same damaging buff key is re-applied by a different caster before expiry
- **THEN** the buff cache's `source_pk` is the newest caster's dbref, and a refresh that omits `source_pk` retains the previously cached value rather than erasing attribution

### Requirement: Every buff key in buffs.yaml has exactly one corresponding unit test
For every buff `key` present in `world/rules/rulebook/buffs.yaml`, `world/rules/tests/test_buffs.py`
SHALL define exactly one test function named `test_buff_<key>`. A regression test SHALL mechanically
verify this correspondence.

#### Scenario: Every seed buff has a matching test function
- **WHEN** the mechanical correspondence check inspects `buffs.yaml`'s buff keys against
  `test_buffs.py`'s test function names
- **THEN** it finds exactly one `test_buff_<key>` function for each of `poisoned`, `paralysis`, `fear`,
  and `conferred_growth_rate`

#### Scenario: Adding a buff without a matching test fails the correspondence check
- **WHEN** a new buff definition is added to `buffs.yaml` with no corresponding `test_buff_<key>`
  function added to `test_buffs.py`
- **THEN** the mechanical correspondence check fails, naming the buff key missing a test
