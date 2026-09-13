## RENAMED Requirements

- FROM: `### Requirement: Blessed cleansing consumes holy water to purge debuffs`
- TO: `### Requirement: 受洗聖水 purges debuffs through an ordinary status-removal effect`

## ADDED Requirements

### Requirement: An ineffective effect is skipped silently rather than failing the use
Within a use that has at least one effective effect, any effect that can change nothing against
current state SHALL be skipped: it SHALL write nothing, SHALL emit no event entry, and SHALL NOT
reject the use. Effectiveness SHALL be evaluated per effect against current state: a positive stat
adjustment requires headroom below the maximum, a negative one requires a value above zero, a status
application requires that the target is not immune to it, and a status removal requires a non-empty
selected set.

#### Scenario: A composite item applies only its effective half
- **WHEN** an actor at full HP but missing MP uses an item declaring both an HP restore and an MP
  restore
- **THEN** the use succeeds, MP is restored, HP is unchanged, one event entry is emitted for the MP
  restore and none for the HP restore

#### Scenario: A skipped effect consumes nothing extra
- **WHEN** a use containing one effective and one ineffective effect settles
- **THEN** exactly one item key is consumed, exactly as it would be if the item declared only the
  effective one

### Requirement: Every effect family names its own ineffective reason
Each effect family SHALL have a stable rejection reason for the case where it can change nothing, so
the single-effect fallback reports a specific reason rather than a generic one regardless of which
verb the item declares. A stat adjustment SHALL report that stat's own bound-reached reason. A status
application blocked by the target's equipment immunity SHALL report a blocked-status reason. A status
removal whose selector matches nothing SHALL report a nothing-to-remove reason, except the
debuff-polarity selector, which SHALL keep the shipped `no_debuffs` reason so 受洗聖水's behavior is
unchanged. Every reason SHALL render a Traditional Chinese message through the shared reason surface.

#### Scenario: A blocked status application reports its own reason
- **WHEN** an item whose only effect applies a debuff the target's worn equipment immunizes against is
  used
- **THEN** preflight rejects with the blocked-status reason, not the generic no-effect reason, and
  nothing is consumed

#### Scenario: An empty removal reports nothing-to-remove
- **WHEN** an item whose only effect removes buff-polarity statuses is used against a target carrying
  none
- **THEN** preflight rejects with the nothing-to-remove reason and nothing is consumed

#### Scenario: The debuff selector keeps the shipped reason
- **WHEN** an unafflicted actor uses an item whose only effect removes debuff-polarity statuses
- **THEN** preflight rejects with `no_debuffs`, the reason 受洗聖水 reports today

#### Scenario: Every reason renders a message
- **WHEN** every member of the item-use rejection vocabulary is rendered through the shared reason
  surface
- **THEN** each produces a non-empty Traditional Chinese message

## MODIFIED Requirements

### Requirement: Item mechanics are immutable and independent from presentation
Every registered item SHALL declare exactly one of a usable-item definition, an equipment-slot
definition, or no mechanics. A usable-item definition SHALL contain a boolean consumable flag and a
combat-use permission, and SHALL NOT name an effect, magnitude, stat, scope, or status: a usable
item's effects are bound to its own key by the item-effect rulebook. An equipment definition SHALL
contain exactly one `EquipmentSlot` and exactly one registered `EquipmentModifierKey` binding it to
the equipment-effect rulebook; an item whose mechanics are not an equipment definition SHALL NOT carry
a modifier key. The registry SHALL reject an item that declares both forms, a malformed slot, or a
missing or unknown modifier key on an equipment item, or a modifier key on any non-equipment item.
Presentation kind, icon, rarity, summary, display name, and price SHALL NOT select or modify
mechanics.

#### Scenario: Healing potion resolves registered use mechanics
- **WHEN** the `healing_potion` definition is inspected
- **THEN** it is consumable, is allowed in combat, carries no equipment slot, and names no effect —
  its single HP-restoring effect is resolved from the item-effect rulebook by its own key

#### Scenario: Visual metadata cannot make an item usable
- **WHEN** an inspect-only item's presentation kind is changed to `potion` without adding use
  mechanics
- **THEN** item preflight still rejects it as not usable and no state changes

#### Scenario: Ambiguous item mechanics fail registry validation
- **WHEN** an item definition declares both use mechanics and an equipment slot
- **THEN** registry construction fails before the item can be presented or used

#### Scenario: Equipment must bind its effect key
- **WHEN** an item definition declares an equipment slot without a registered modifier key, or
  declares a modifier key while carrying no equipment slot
- **THEN** registry construction fails before the item can be presented or toggled

### Requirement: Item-use preflight is side-effect-free and revalidates current conditions
The deterministic item-use service SHALL expose a side-effect-free preflight that resolves the item
from canonical registry data, verifies that the actor currently holds at least one matching key in
canonical inventory, verifies the current mode against the item definition, resolves the item's
ordered effect list from the item-effect rulebook, and evaluates each effect's condition against
current state. The preflight SHALL reject only when **no** effect is effective. Its reason code SHALL
be the shared code when every ineffective effect names the same one, and a generic no-effect code
otherwise. It SHALL return stable named rejection reasons and SHALL NOT mutate inventory, traits,
quest state, equipment, combat state, clock, or presentation.

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

### Requirement: Item use applies effect and conditional consumption atomically
The deterministic item-use settlement SHALL repeat preflight against current state, compute the
complete effect, inventory, and mirror-object plan before writing, and commit them atomically. The
plan SHALL carry one step per effective effect, each holding the magnitude actually applicable to
current state, and steps SHALL be applied in the order the rulebook declares. Each effect family
SHALL apply through the single shared entry point for that family, never through a second increment
path. A successful consumable use SHALL remove exactly one matching inventory key and, when one
exists, exactly one matching contained Evennia Object mirror. A key-only item SHALL require no
fabricated mirror before consumption. A successful reusable use SHALL apply its effects without
changing inventory quantity or contained mirrors. A stat adjustment SHALL move the stat by its
configured amount up to, but never beyond, that stat's bound in the direction of travel. Any rejection
or settlement failure SHALL restore durable state, idmapper/contents caches, trait and Attribute
caches, and every other touched surface to its pre-call state.

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

### Requirement: Successful item use emits a stable EventLog entry
Every successful item use SHALL emit one EventLog carrying one `item_used` entry per **effective**
effect. Each entry's data SHALL carry `item_key` and `consumable`, plus the per-family payload: a stat
adjustment SHALL carry the stat name and the signed amount actually applied; a status effect SHALL
carry the status keys involved and the count actually applied or removed. No entry SHALL carry an
effect-key field, because effects are no longer identified by a closed key. Rejected preflight SHALL
emit no item-use EventLog. A compressed commanded-action marker SHALL identify the selected item
separately and SHALL NOT replace the item-use entries.

#### Scenario: Healing log records actual restoration
- **WHEN** a potion configured for more healing than the actor's missing HP succeeds
- **THEN** one `item_used` entry reports the potion key, consumable true, the `hp` stat, and an amount
  equal only to the HP actually restored, with no effect-key field

#### Scenario: Cleanse log records the removed count
- **WHEN** 受洗聖水 removes three active debuffs
- **THEN** one `item_used` entry carries the potion key, consumable true, the three removed status
  keys, and a count of exactly three, with no amount and no effect-key field

#### Scenario: A two-effect use emits two entries
- **WHEN** an item whose two effects are both effective is used
- **THEN** the EventLog carries exactly two `item_used` entries, one per effect, in declaration order

### Requirement: 受洗聖水 purges debuffs through an ordinary status-removal effect
受洗聖水 SHALL declare a single status-removal effect selecting every debuff-polarity status. Using a
held 受洗聖水 SHALL remove every active debuff-polarity status from the actor through the shared
selector-driven removal, consume exactly one item key (with its contained mirror when present), emit
its stable EventLog entry, and commit atomically with the existing item-use settlement. It SHALL carry
no special case anywhere in preflight, planning, settlement, or logging: it SHALL be resolved by the
same code path as every other status-removal effect. The item-use touched-journal SHALL snapshot and
restore the buff storage surface so a post-cleanse failure rolls back persistence and live buff reads
together.

#### Scenario: Holy water cleanses the actor
- **WHEN** an actor afflicted with `poisoned` and `fear` uses 受洗聖水
- **THEN** both debuffs are gone, exactly one potion key was consumed, and a stable event entry was
  logged

#### Scenario: Nothing to cleanse rejects without consuming
- **WHEN** an unafflicted actor uses 受洗聖水
- **THEN** preflight rejects with the registered `no_debuffs` reason (mirroring the `hp_full` heal
  discipline) rendered in Traditional Chinese through the shipped reason surfaces, the potion is not
  consumed, and no world clock advances

#### Scenario: Post-cleanse failure restores buffs
- **WHEN** settlement fails after the cleanse removal (injected fault)
- **THEN** the potion key, the debuffs, and live buff reads are all restored to their pre-use state

#### Scenario: Cleanse entry shape is validated
- **WHEN** the item-effect rulebook gives 受洗聖水's status-removal effect an amount field
- **THEN** the validated loader rejects it, because the removal verb accepts no magnitude

#### Scenario: Holy water has no dedicated branch
- **WHEN** the item-use resolver is inspected
- **THEN** it contains no branch keyed to 受洗聖水, to cleansing, or to any individual item identity
