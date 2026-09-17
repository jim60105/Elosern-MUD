# buff-handler-integration Specification

## Purpose
Mounts Evennia's BuffHandler on LivingEntity as a read-only entity.buffs property, replacing change 3's stand-in, and defines the buff model around it: definitions configuring rate of change, clamped bounds, and decay; conferred rate-of-change buffs consumed by pure query; a declared unbuilt seam for buff-forbidden actions; and validated effect-source identities for damaging rate buffs.

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
`world/rules/rulebook/buffs.yaml` SHALL define each buff's tunable parameters (duration, tick interval, stacking policy, and a `modifiers` mapping using at most the keys `rate`, `bounds`, `divert`, and `decay`) with rate choosing either a fixed delta or a validated recovery profile (never both), per design doc §6.4's exhaustive list of what a buff may modify. A buff definition SHALL NOT configure a combat-stat multiplier (`atk_phys`/`agility`/`defense` scaling) — that remains the combat-modifier/`SkillHandler.effective_value()` territory. A buff MAY declare an empty `modifiers` mapping when its sole purpose is being detectable as present (a marker buff). A `divert` modifier SHALL be validated fail-closed at load: its `target` must be a gauge key, its `fraction` a finite number in (0, 1], its `cap` a positive integer, and the row must carry a finite duration; malformed divert rows SHALL make the buff-definition load fail with the offending key named. A fixed-delta `rate` modifier targeting `hp` with a negative delta MAY additionally declare one `caster_share` transfer clause: a finite number in (0, 1] naming the fraction of each tick's actual HP loss credited to the buff's origin caster. The clause SHALL be validated fail-closed at load — rejected on a non-`hp` rate target, on a non-negative delta, on a boolean or non-finite or out-of-range value, and on any co-declaration with a `recovery` or `scale_from_source` rate — the offending definition key SHALL be named and the load SHALL fail. Rows without the clause SHALL keep ticking exactly as before. Additionally, a definition MAY carry one top-level `marker` clause outside `modifiers` whose value belongs to the closed marker vocabulary — now `ground` or `positional`; a malformed value SHALL fail the load naming the offending definition key, and every row without the clause SHALL load bit-identically to its pre-clause behavior. The public buff-application entry point SHALL, for a definition declaring the `positional` marker value, first remove the recipient's live `ground`-marker instances through the existing scoped removal path before mounting (zero damage or revive side effects, non-marker instances untouched), and SHALL refuse the mount entirely on an entity that is defeated (hp ≤ 0) or recorded fled or knocked-out in its active combat session; both behaviors SHALL consult only the marker clause and SHALL NOT change the mount semantics of any ground or non-marker row.

#### Scenario: A rate-of-change buff definition is well-formed
- **WHEN** `buffs.yaml`'s `poisoned` definition is inspected
- **THEN** its `modifiers` mapping contains a `rate` key naming a target field and a per-tick delta, and contains neither `bounds` nor a combat-stat-multiplier key

#### Scenario: A marker-only buff definition has an empty modifiers mapping
- **WHEN** `buffs.yaml`'s `paralysis` and `fear` definitions are inspected
- **THEN** each has an empty `modifiers` mapping, and each is still loadable and applyable via `BuffHandler`

#### Scenario: No buff definition configures a combat-stat multiplier
- **WHEN** every entry in `buffs.yaml` is inspected
- **THEN** none contains a `modifiers` key resembling a multiplicative combat-stat scale (e.g. `atk_phys_multiplier`); combat-facing consequences of a buff's presence are expressed exclusively through the validated modifier vocabulary

#### Scenario: A divert-profile buff definition is well-formed and malformed ones fail closed
- **WHEN** a synthetic divert row (gauge target, fraction in (0,1], positive cap, finite duration) is loaded, and separately rows with a fraction of 1.5, a zero/negative cap, a non-gauge target, or a null duration are loaded
- **THEN** the well-formed row loads as a divert-capable definition and each malformed row raises at load time naming the offending definition key

#### Scenario: A caster-share clause loads only on a damaging hp rate row
- **WHEN** a synthetic hp-target negative-delta rate row declaring `caster_share` in (0, 1] is loaded
- **THEN** the definition loads carrying the validated share

#### Scenario: Every misplaced caster-share clause fails the load closed
- **WHEN** rows declaring `caster_share` on an mp-target rate, on a non-negative hp delta, on a recovery-profile rate, on a `scale_from_source` rate, or with a boolean, zero, negative, greater than one, or non-finite value are loaded
- **THEN** each raises at load time naming the offending definition key and no definition is produced

#### Scenario: A marker clause loads only with a vocabulary value
- **WHEN** a synthetic row declaring the closed-vocabulary ground marker value is loaded, and separately rows declaring the positional marker value, an element name, a boolean, or a number as the marker value are loaded
- **THEN** each well-formed row (ground and positional) loads carrying the validated marker clause and each malformed row raises at load time naming the offending definition key

#### Scenario: Mounting a positional row sweeps ground markers at the entry point
- **WHEN** the public entry point applies a synthetic positional row to an entity holding a live synthetic ground-marker instance plus an ordinary timed buff
- **THEN** the ground instance is removed first with no damage or revive side effects, the ordinary buff is untouched, and the positional instance mounts live

#### Scenario: The positional mount refuses impossible recipients
- **WHEN** the public entry point applies a synthetic positional row to a defeated, fled, or knocked-out entity
- **THEN** nothing is written for any of the three, while the identical call on a living still-fighting entity mounts the instance

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
`_apply_rate_modifier()` SHALL treat `skill_practice` (the `conferred_growth_rate` buff's declared
`rate` target) as an explicit, documented no-op on tick, not an unimplemented or erroring case. The
buff's `scale` SHALL be consumed exclusively by pull, through `growth_rate_multiplier(entity)` (its live reader is `use-driven-skill-lineage`'s practice-XP formula, read by pull at
the moment proficiency accrues), and SHALL NOT be additionally applied as a per-tick effect. This SHALL be stated in `_apply_rate_modifier()`'s own
docstring, naming `growth_rate_multiplier()`/change 11b as the actual reader, so a future edit does not
reintroduce a push-side application and double-count the scale.

#### Scenario: Ticking a conferred growth-rate buff completes without raising
- **WHEN** `tick_buffs(entity)` is called on an entity holding an active `conferred_growth_rate` buff
  (applied via `grant_conferred_growth_rate`)
- **THEN** it completes without raising `NotImplementedError` or any other exception

#### Scenario: Ticking a conferred growth-rate buff leaves magic_power untouched
- **WHEN** `tick_buffs(entity)` is called on an entity holding an active `conferred_growth_rate` buff
- **THEN** `entity.traits.magic_power.value` and `entity.db.skill_proficiency` are unchanged
  before and after the call, and no other entity attribute is mutated as a result of this buff's
  tick

#### Scenario: The no-op is documented as intentional, not a placeholder gap
- **WHEN** `_apply_rate_modifier()`'s docstring is inspected for the `skill_practice` branch
- **THEN** it states that the value is read by pull through `growth_rate_multiplier()` (change 11b's
  growth multiplier query), and that applying it again on tick would double-apply the
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
- **THEN** it returns two records in application order, each carrying the definition key, the buff cache's `source_pk` (or `None`), its configured rate delta (`-5` and `-8` respectively), and the entity's HP immediately before that tick applied

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
`_handle_buff_apply` SHALL persist the resolving actor's dbref as `source_pk`, and for a source-bearing cast also the granting skill key as `source_skill`, in the buff cache whenever the applied definition's `rate` modifier damages a gauge (target `hp` or `mp` with a negative delta). The value SHALL be derived from the actor inside the handler; a caller-supplied `source_pk` in `buff_kwargs` SHALL NOT override it, and an actor without a resolvable positive-int dbref SHALL reject the action before commit. Widening this persistence gate to mp-target rates SHALL NOT widen the combat-round consumption gates: `tick_buffs`' `TickRecord` emission and `settle_upkeep`'s HP damage/defeat event projection stay hp-rate-only. Buff instances created outside the handler (for example direct `_add_buff` calls) MAY lack `source_pk`, in which case their rate ticks are unattributed. An mp-target damaging rate tick SHALL carry this persisted attribution into the canonical MP-change writer so a depletion crossing it causes dispatches with the grant-time source skill and source tier; the hp-target dispatch path SHALL remain behaviorally unchanged.

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

#### Scenario: An mp-target drain ticks with grant-time attribution
- **WHEN** a synthetic mp-target negative-delta buff applied by a source-bearing cast later ticks the holder's MP to zero
- **THEN** the depletion crossing is attributed to the persisted grant-time source skill and tier, not to the tick moment

#### Scenario: An mp tick inside a combat round fabricates no HP consumption
- **WHEN** a combat round settles while an mp-target damaging buff ticks on a low-HP roster entity
- **THEN** the round's event log contains no HP damage or defeat entry attributable to that tick, while hp-target rates keep producing their existing records unchanged

### Requirement: Buff application has one public entry point carrying both grant-time guards
`world/rules/buffs.py` SHALL expose a public buff-application function taking an entity, a buff
definition key, an optional instance key, and arbitrary cache data. Every deterministic caller that
applies a buff SHALL use it rather than calling `BuffHandler.add()` directly, because two grant-time
guards live in it and nowhere else: (1) a debuff whose definition key is immunized by the target's
worn equipment SHALL NOT be written at all, and (2) a definition declaring
`stacking: unique_per_source` SHALL raise when no `source_key` is supplied. Neither guard SHALL be
weakened or made optional for any caller.

#### Scenario: An immunized debuff is refused, not half-applied
- **WHEN** the public entry point is called with a debuff-polarity key the target's worn equipment
  immunizes against
- **THEN** no buff is written and the target's active buff set is unchanged

#### Scenario: A unique_per_source buff without a source key raises
- **WHEN** the public entry point is called for a definition declaring
  `stacking: unique_per_source` with no `source_key` in the supplied data
- **THEN** it raises rather than writing an unattributable instance

#### Scenario: A caller outside the buffs module applies a buff through the entry point
- **WHEN** a deterministic module other than `world/rules/buffs.py` applies a buff
- **THEN** it does so through the public entry point, and no module outside `world/rules/buffs.py`
  calls `entity.buffs.add(...)` directly

### Requirement: Recovery profiles restore living recipients with explicit snapshot and live inputs
A timed recovery profile SHALL combine a validated base amount, optional live recipient-state adjustment and persisted caster-side modifiers. Caster inputs SHALL be captured on application and recipient effective state SHALL be read at each tick. Recovery SHALL floor the resulting nonnegative value, clamp to each living HP gap, and never revive a dead target. Malformed profiles SHALL be rejected before application.

#### Scenario: Live recipient and captured caster inputs differ
- **WHEN** recipient exposure changes after application and the caster later changes equipment or is deleted
- **THEN** the next tick reflects new recipient exposure but the original caster modifier and does not require the caster object

#### Scenario: No revival or overflow
- **WHEN** a tick addresses a dead recipient or a living recipient near maximum HP
- **THEN** dead HP is unchanged and living HP never exceeds its maximum

### Requirement: Finite recovery ticks and refresh are deterministic across elapsed-time partitions
A configured three-tick recovery SHALL tick at 10, 20 and 30 elapsed world seconds, never at application or after expiration. Advances within the clock's settlement-quanta budget SHALL produce the same ticks whether taken at once or in equivalent segments; an advance beyond that budget SHALL never fabricate ticks. Reapplication SHALL replace source snapshots and restart duration and tick remainder without stacking. Removal SHALL stop future ticks; persistence reload SHALL not replay completed ticks.

#### Scenario: Final tick precedes expiration
- **WHEN** world time advances 30 seconds at once or in three equal segments
- **THEN** exactly three recovery ticks occur with no application-time tick and no fourth tick at 40 seconds

#### Scenario: Refresh and reload preserve schedule
- **WHEN** a partially elapsed profile is refreshed and refetched
- **THEN** only the new three-tick schedule runs using the new source snapshots

#### Scenario: Removal cancels recovery
- **WHEN** the buff is removed before its next due tick
- **THEN** no later tick restores HP

### Requirement: Buff verification establishes mechanics rather than catalog correspondence
Distinct buff mechanics SHALL have substantive behavior tests using synthetic definitions. Assertions SHALL establish state changes, timing, refresh, expiry or immunity rather than require test function names or duplicate each authored buff key. Timed defense riders SHALL be verified through actual damage changes and expiration, not declaration equality.

#### Scenario: Synthetic timed defense affects combat
- **WHEN** a synthetic refreshable defense marker is applied and then expires
- **THEN** computed incoming damage is reduced while active and returns to its prior value after expiration without stacking on refresh

### Requirement: Buff definitions may declare a validated in-round order operation
A buff definition MAY declare a closed-vocabulary in-round order-operation clause at definition
load — one operation value drawn from exactly {advance_to_head, retreat_to_tail} in a well-formed
wrapper mapping —
carried on the loaded definition beside the shipped marker clause. A malformed declaration (an
unknown operation word, a bare string instead of the wrapper, a boolean, a number, or extra keys)
SHALL raise at load time naming the offending definition key, fail-closed like every other
definition-shape clause. The clause is definitional data only: a row declaring it with no
round-loop consumer present SHALL load and apply exactly like an ordinary timed row, and the
definition SHALL remain applyable, refreshable, and removable through the ordinary `BuffHandler`
lifecycle with no ordering side effect of its own.

#### Scenario: A well-formed order row loads and cycles through the ordinary lifecycle
- **WHEN** a synthetic row declaring the advance-to-head operation value is loaded, applied to a living
  entity, refreshed, and expired with no combat round running
- **THEN** the loaded definition carries the validated operation and the instance mounts, refreshes,
  and expires through the ordinary `BuffHandler` path with no effect beyond an ordinary timed buff

#### Scenario: Every malformed order clause fails the load closed
- **WHEN** rows declare an unknown operation word, a bare operation string without the wrapper, a
  boolean, a number, or the wrapper with extra keys
- **THEN** each raises at load time naming the offending definition key and no definition is
  produced, while every previously valid row file loads unchanged
