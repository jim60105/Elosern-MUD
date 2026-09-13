## ADDED Requirements

### Requirement: Item preflight resolves each effect's targets through the shared resolver
Item-use preflight SHALL accept an action context — the battlefield context inside an active combat
session, a room-backed context outside one — and SHALL resolve every effect's target set through the
shared target resolver, supplying the targeting requirement that effect's scope maps to. It SHALL
accept at most one caller-supplied explicit target for the whole use, consumed only by single-entity
scopes; self scopes SHALL bind the actor and group scopes SHALL expand through the context. A
single-entity effect with no supplied target SHALL reject with a stable no-target reason; a supplied
target the resolver refuses SHALL reject with a stable invalid-target reason carrying the resolver's
own reason as detail. Preflight SHALL remain side-effect-free.

#### Scenario: A single-scope item with no target rejects before writing
- **WHEN** an actor uses an item whose only effect is scoped to a single entity, supplying no target
- **THEN** preflight rejects with the no-target reason and nothing is consumed, written, or advanced

#### Scenario: An invalid target reports the resolver's own reason
- **WHEN** an actor supplies a dead entity as the target of a single-scope item
- **THEN** preflight rejects with the invalid-target reason and the resolver's own target-dead reason
  as detail

#### Scenario: A group scope needs no caller target
- **WHEN** an actor uses an item whose effects are scoped to their own side, supplying no target
- **THEN** preflight succeeds and resolves every eligible member of that side through the context

#### Scenario: An out-of-combat group scope resolves through the room
- **WHEN** an actor with two present companions uses an own-side item outside combat
- **THEN** all three entities resolve as targets, because out-of-combat relations carry no hostility
  model

#### Scenario: A group scope with no eligible member rejects
- **WHEN** an opposing-side item is used with no living opposing entity resolvable
- **THEN** preflight rejects and nothing is consumed

## MODIFIED Requirements

### Requirement: Item-use preflight is side-effect-free and revalidates current conditions
The deterministic item-use service SHALL expose a side-effect-free preflight that resolves the item
from canonical registry data, verifies that the actor currently holds at least one matching key in
canonical inventory, verifies the current mode against the item definition, resolves the item's
ordered effect list from the item-effect rulebook, resolves each effect's targets through the shared
resolver, and evaluates each effect's condition against each target's current state. The preflight
SHALL reject only when **no** effect is effective against **any** of its targets. Its reason code SHALL
be the shared code when every ineffective evaluation names the same one, and a generic no-effect code
otherwise. It SHALL return stable named rejection reasons and SHALL NOT mutate inventory, traits,
quest state, equipment, combat state, clock, or presentation for the actor or for any target.

#### Scenario: Full HP rejects a healing potion
- **WHEN** an actor holds a healing potion and current HP equals maximum HP
- **THEN** preflight rejects with `hp_full` and inventory, HP, combat round, and clock remain unchanged

#### Scenario: Missing ownership rejects use
- **WHEN** an actor submits a registered usable item key that is absent from canonical inventory
- **THEN** preflight rejects with `item_not_held` without applying its effect

#### Scenario: Eligible healing preflight writes nothing
- **WHEN** an actor holds a healing potion and current HP is below maximum HP
- **THEN** preflight succeeds while HP and inventory remain byte-for-byte unchanged

#### Scenario: A multi-effect item with nothing to do reports the generic reason
- **WHEN** an actor at full HP and full MP uses an item declaring an HP restore and an MP restore
- **THEN** preflight rejects with the generic no-effect reason rather than either gauge's full reason,
  and nothing is consumed

#### Scenario: Agreeing ineffective effects keep their specific reason
- **WHEN** an actor at full HP uses an item declaring two HP restores
- **THEN** preflight rejects with `hp_full`, not the generic no-effect reason

#### Scenario: One effective target among several carries the whole use
- **WHEN** an own-side healing item is used where one ally is injured and every other member is at
  full HP
- **THEN** preflight succeeds, and settlement heals only the injured ally

### Requirement: Item use applies effect and conditional consumption atomically
The deterministic item-use settlement SHALL repeat preflight against current state, compute the
complete effect, inventory, and mirror-object plan before writing, and commit them atomically. The
plan SHALL carry one step per effective effect-and-target pair, each holding the magnitude actually
applicable to that target's current state, and steps SHALL be applied in the order the rulebook
declares. Each effect family SHALL apply through the single shared entry point for that family, never
through a second increment path. A successful consumable use SHALL remove exactly one matching
inventory key from the **actor** and, when one exists, exactly one matching contained Evennia Object
mirror — consumption SHALL never scale with target count. A key-only item SHALL require no fabricated
mirror before consumption. A successful reusable use SHALL apply its effects without changing inventory
quantity or contained mirrors. A stat adjustment SHALL move the stat by its configured amount up to,
but never beyond, that stat's bound in the direction of travel. Any rejection or settlement failure
SHALL restore durable state, idmapper/contents caches, trait and Attribute caches, and every other
touched surface to its pre-call state, **for every touched entity**, not only the actor.

#### Scenario: Consumable healing removes one unit
- **WHEN** an injured actor holding two healing potions successfully uses one
- **THEN** HP increases by the canonical amount capped at maximum and canonical inventory retains
  exactly one healing potion

#### Scenario: Reusable use preserves quantity
- **WHEN** an eligible actor successfully uses a registered reusable item
- **THEN** its deterministic effects apply and the count of that item key is unchanged

#### Scenario: Materialized consumable removes one mirror
- **WHEN** an injured actor successfully uses one of two healing potions whose two contained-object
  mirrors exist
- **THEN** HP is restored and exactly one canonical key plus one corresponding contained mirror remain

#### Scenario: Key-only consumable needs no mirror
- **WHEN** an injured actor successfully uses a key-only healing potion granted by a quest
- **THEN** its key is consumed without materializing or deleting an unrelated object

#### Scenario: Effect or mirror failure rolls back consumption
- **WHEN** fault injection raises during trait, key-list, or mirror-object settlement
- **THEN** HP, inventory, contained objects, quest progress, combat state, clock, and in-process
  caches equal their pre-call values

#### Scenario: A negative stat adjustment stops at zero
- **WHEN** an actor whose SP is below the declared drain uses an item declaring a negative SP
  adjustment
- **THEN** SP lands at zero, never below, and the emitted amount is the drop that actually occurred

#### Scenario: Ordered effects apply in declaration order
- **WHEN** an item declares a status removal followed by a stat adjustment
- **THEN** the removal is applied first and the adjustment second

#### Scenario: A multi-target use consumes exactly one unit
- **WHEN** an own-side item resolving four targets is used successfully
- **THEN** all four are affected and exactly one inventory key plus at most one mirror is consumed

#### Scenario: A mid-settlement failure restores every touched entity
- **WHEN** fault injection raises after two of four targets have been written
- **THEN** the traits, buffs, and sexual state of all four targets, plus the actor's inventory and
  mirror, equal their pre-call values

#### Scenario: A rolled-back target reads its pre-call state through live handlers
- **WHEN** fault injection raises after a group-scoped pleasure effect has written a non-actor target,
  and that target's pleasure is then read back through its live handler in the same process
- **THEN** it reports the pre-call value, because the rollback dropped that entity's memoized handler
  as well as restoring its stored attributes

### Requirement: Successful item use emits a stable EventLog entry
Every successful item use SHALL emit one EventLog carrying one `item_used` entry per **effective**
effect-and-target pair. Each entry's data SHALL carry `item_key`, `consumable`, and the target it
applied to, plus the per-family payload: a stat adjustment SHALL carry the stat name and the signed
amount actually applied; a status effect SHALL carry the status keys involved and the count actually
applied or removed. No entry SHALL carry an effect-key field, because effects are no longer identified
by a closed key. The EventLog's target list SHALL be the deduplicated set of entities actually
touched. Rejected preflight SHALL emit no item-use EventLog. A compressed commanded-action marker
SHALL identify the selected item separately and SHALL NOT replace the item-use entries.

#### Scenario: Healing log records actual restoration
- **WHEN** a potion configured for more healing than the actor's missing HP succeeds
- **THEN** one `item_used` entry reports the potion key, consumable true, the `hp` stat, the actor as
  target, and an amount equal only to the HP actually restored, with no effect-key field

#### Scenario: Cleanse log records the removed count
- **WHEN** 受洗聖水 removes three active debuffs
- **THEN** one `item_used` entry carries the potion key, consumable true, the three removed status
  keys, and a count of exactly three, with no amount and no effect-key field

#### Scenario: A two-effect use emits two entries
- **WHEN** an item whose two effects are both effective is used
- **THEN** the EventLog carries exactly two `item_used` entries, one per effect, in declaration order

#### Scenario: A multi-target effect emits one entry per affected target
- **WHEN** one own-side healing effect restores HP on three allies
- **THEN** the EventLog carries three `item_used` entries, each naming its own target and its own
  restored amount, and the log's target list contains exactly those three entities

### Requirement: Combat item use occupies one initiative-ordered round
An active combat session SHALL admit a preflight-valid `ItemUseRequest` as the player's selected
action, supplying the battlefield action context and the player's chosen target when the item's scope
requires one. Ordinary and compressed round providers SHALL supply that request exactly once at the
player's first initiative position, dispatch it only to the deterministic item resolver, and supply
ordinary policy actions for other capable participants. A preflight rejection SHALL start no round. If
an earlier initiative action invalidates a preflight-valid item request, the already-started round
SHALL remain consumed. Combat's outer rollback contract SHALL include inventory, selected mirror
object, and every item-touched cache **on every touched entity**. A combat item use SHALL contribute
round-based time and SHALL NOT add separate item-use time. The number of targets an item reaches SHALL
NOT affect the number of rounds it consumes.

#### Scenario: Valid potion use runs one combat round
- **WHEN** an injured player in active combat submits a preflight-valid healing potion use
- **THEN** the potion request resolves at the player's initiative position, every other eligible
  participant receives at most one ordinary action, and the session round count increases exactly once

#### Scenario: Full HP preserves the combat turn
- **WHEN** a full-HP player attempts to use a healing potion during active combat
- **THEN** preflight rejects before initiative, no participant acts, no item is consumed, and the round
  count is unchanged

#### Scenario: Mid-round invalidation consumes the started round
- **WHEN** item preflight succeeds but an earlier initiative action makes the player unable to use the
  item at their turn
- **THEN** item resolution rejects without consumption, prior actions remain committed, and the round
  count increases once

#### Scenario: Later combat failure restores item surfaces
- **WHEN** item use resolves but later upkeep, session persistence, or terminal settlement raises
- **THEN** HP, inventory, contained mirror, session state, all participant effects, and in-process
  caches roll back together, for the actor and for every entity the item touched

#### Scenario: Player-direction overwhelm uses the item once
- **WHEN** the player's team is overwhelming and the injured player selects a valid healing potion
- **THEN** the potion resolves on the first compressed player turn, later compressed player turns use
  basic attack, and exactly one commanded item identity is emitted

#### Scenario: A four-target item still consumes one round
- **WHEN** a player in active combat uses an item whose effects reach four combatants
- **THEN** all four are affected within one initiative position and the session round count increases
  exactly once
