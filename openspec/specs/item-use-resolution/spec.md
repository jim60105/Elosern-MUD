## Purpose

Deterministic item-use preflight, atomic settlement, stable event identity, world-clock boundaries, and combat round occupancy.

## Requirements

### Requirement: Item mechanics are immutable and independent from presentation
Every registered item SHALL declare exactly one of a usable-item definition, an equipment-slot definition, or no mechanics. A usable-item definition SHALL contain a registered deterministic effect key, a boolean consumable flag, and a combat-use permission. An equipment definition SHALL contain exactly one `EquipmentSlot` and exactly one registered `EquipmentModifierKey` binding it to the equipment-effect rulebook; an item whose mechanics are not an equipment definition SHALL NOT carry a modifier key. The registry SHALL reject an item that declares both forms, an unknown effect, a malformed slot, a missing or unknown modifier key on an equipment item, or a modifier key on any non-equipment item. Presentation kind, icon, rarity, summary, display name, and price SHALL NOT select or modify mechanics.

#### Scenario: Healing potion resolves registered use mechanics
- **WHEN** the `healing_potion` definition is inspected
- **THEN** it resolves the registered self-heal effect, is consumable, is allowed in combat, and carries no equipment slot

#### Scenario: Visual metadata cannot make an item usable
- **WHEN** an inspect-only item's presentation kind is changed to `potion` without adding use mechanics
- **THEN** item preflight still rejects it as not usable and no state changes

#### Scenario: Ambiguous item mechanics fail registry validation
- **WHEN** an item definition declares both use mechanics and an equipment slot
- **THEN** registry construction fails before the item can be presented or used

#### Scenario: Equipment must bind its effect key
- **WHEN** an item definition declares an equipment slot without a registered modifier key, or declares a modifier key while carrying no equipment slot
- **THEN** registry construction fails before the item can be presented or toggled

### Requirement: Item-use preflight is side-effect-free and revalidates current conditions
The deterministic item-use service SHALL expose a side-effect-free preflight that resolves the item from canonical registry data, verifies that the actor currently holds at least one matching key in canonical inventory, verifies the current mode against the item definition, validates effect data, and evaluates every current effect condition. It SHALL return stable named rejection reasons and SHALL NOT mutate inventory, traits, quest state, equipment, combat state, clock, or presentation. Healing SHALL require current HP below maximum HP.

#### Scenario: Full HP rejects a healing potion
- **WHEN** an actor holds a healing potion and current HP equals maximum HP
- **THEN** preflight rejects with `hp_full` and inventory, HP, combat round, and clock remain unchanged

#### Scenario: Missing ownership rejects use
- **WHEN** an actor submits a registered usable item key that is absent from canonical inventory
- **THEN** preflight rejects with `item_not_held` without applying its effect

#### Scenario: Eligible healing preflight writes nothing
- **WHEN** an actor holds a healing potion and current HP is below maximum HP
- **THEN** preflight succeeds while HP and inventory remain byte-for-byte unchanged

### Requirement: Item use applies effect and conditional consumption atomically
The deterministic item-use settlement SHALL repeat preflight against current state, compute the complete effect, inventory, and mirror-object plan before writing, and commit them atomically. A successful consumable use SHALL remove exactly one matching inventory key and, when one exists, exactly one matching contained Evennia Object mirror. A key-only item SHALL require no fabricated mirror before consumption. A successful reusable use SHALL apply the effect without changing inventory quantity or contained mirrors. Healing SHALL restore the canonical rulebook amount up to, but never above, maximum HP. Any rejection or settlement failure SHALL restore durable state, idmapper/contents caches, trait and Attribute caches, and every other touched surface to its pre-call state.

#### Scenario: Consumable healing removes one unit
- **WHEN** an injured actor holding two healing potions successfully uses one
- **THEN** HP increases by the canonical amount capped at maximum and canonical inventory retains exactly one healing potion

#### Scenario: Reusable use preserves quantity
- **WHEN** an eligible actor successfully uses a registered reusable item
- **THEN** its deterministic effect applies and the count of that item key is unchanged

#### Scenario: Materialized consumable removes one mirror
- **WHEN** an injured actor successfully uses one of two healing potions whose two contained-object mirrors exist
- **THEN** HP is restored and exactly one canonical key plus one corresponding contained mirror remain

#### Scenario: Key-only consumable needs no mirror
- **WHEN** an injured actor successfully uses a key-only healing potion granted by a quest
- **THEN** its key is consumed without materializing or deleting an unrelated object

#### Scenario: Effect or mirror failure rolls back consumption
- **WHEN** fault injection raises during trait, key-list, or mirror-object settlement
- **THEN** HP, inventory, contained objects, quest progress, combat state, clock, and in-process caches equal their pre-call values

### Requirement: Out-of-combat item use advances deterministic time once
A successful out-of-combat item use SHALL compose its complete item plan and the player-driven world's canonical six-second advance inside one outer transaction and rollback journal. A rejected or failed use SHALL advance no time. A failure in any due clock callback SHALL roll back the item effect, consumption, contained mirror, clock, due-event effects, and all in-process caches together. Combat use SHALL add no command-default time because combat-session round settlement owns elapsed time.

#### Scenario: Exploration use advances six seconds
- **WHEN** an injured actor successfully uses a healing potion outside combat
- **THEN** the item effect and consumption commit and the world clock advances exactly six seconds once

#### Scenario: Rejected exploration use advances no time
- **WHEN** a full-HP actor attempts to use a healing potion outside combat
- **THEN** the world clock and every item-use surface remain unchanged

#### Scenario: Clock callback failure rolls back item use
- **WHEN** a due deterministic clock callback fails during the six-second advance after item planning
- **THEN** HP, inventory, contained mirror, clock tick, due-event state, and in-process caches all equal their pre-use values

### Requirement: Combat item use occupies one initiative-ordered round
An active combat session SHALL admit a preflight-valid `ItemUseRequest` as the player's selected action. Ordinary and compressed round providers SHALL supply that request exactly once at the player's first initiative position, dispatch it only to the deterministic item resolver, and supply ordinary policy actions for other capable participants. A preflight rejection SHALL start no round. If an earlier initiative action invalidates a preflight-valid item request, the already-started round SHALL remain consumed. Combat's outer rollback contract SHALL include inventory, selected mirror object, and every item-touched cache. A combat item use SHALL contribute round-based time and SHALL NOT add separate item-use time.

#### Scenario: Valid potion use runs one combat round
- **WHEN** an injured player in active combat submits a preflight-valid healing potion use
- **THEN** the potion request resolves at the player's initiative position, every other eligible participant receives at most one ordinary action, and the session round count increases exactly once

#### Scenario: Full HP preserves the combat turn
- **WHEN** a full-HP player attempts to use a healing potion during active combat
- **THEN** preflight rejects before initiative, no participant acts, no item is consumed, and the round count is unchanged

#### Scenario: Mid-round invalidation consumes the started round
- **WHEN** item preflight succeeds but an earlier initiative action makes the player unable to use the item at their turn
- **THEN** item resolution rejects without consumption, prior actions remain committed, and the round count increases once

#### Scenario: Later combat failure restores item surfaces
- **WHEN** item use resolves but later upkeep, session persistence, or terminal settlement raises
- **THEN** HP, inventory, contained mirror, session state, all participant effects, and in-process caches roll back together

#### Scenario: Player-direction overwhelm uses the item once
- **WHEN** the player's team is overwhelming and the injured player selects a valid healing potion
- **THEN** the potion resolves on the first compressed player turn, later compressed player turns use basic attack, and exactly one commanded item identity is emitted

### Requirement: Successful item use emits a stable EventLog entry
Every successful item use SHALL emit one `item_used` EventLog entry for the actor and self target. Its data SHALL contain exactly `item_key`, `effect_key`, `consumable`, and `amount`, where amount is the actual bounded effect applied. Rejected preflight SHALL emit no item-use EventLog. A compressed commanded-action marker SHALL identify the selected item separately and SHALL NOT replace the item-use entry.

#### Scenario: Healing log records actual restoration
- **WHEN** a potion configured for more healing than the actor's missing HP succeeds
- **THEN** one `item_used` entry reports the potion and effect keys, consumable true, and amount equal only to the HP actually restored

### Requirement: Blessed cleansing consumes holy water to purge debuffs
`blessed_cleansing` SHALL be a registered deterministic item-effect key whose rulebook entry carries no amount. Using a held 受洗聖水 SHALL remove every active debuff-polarity buff from the actor through the shipped cleanse removal path, consume exactly one item key (with its contained mirror when present), emit its stable EventLog entry, and commit atomically with the existing item-use settlement. The item-use touched-journal SHALL snapshot and restore the buff storage surface so a post-cleanse failure rolls back persistence and live buff reads together.

#### Scenario: Holy water cleanses the actor
- **WHEN** an actor afflicted with `poisoned` and `fear` uses 受洗聖水
- **THEN** both debuffs are gone, exactly one potion key was consumed, and a stable event entry was logged

#### Scenario: Nothing to cleanse rejects without consuming
- **WHEN** an unafflicted actor uses 受洗聖水
- **THEN** preflight rejects with the registered `no_debuffs` reason (mirroring the `hp_full` heal discipline) rendered in Traditional Chinese through the shipped reason surfaces, the potion is not consumed, and no world clock advances

#### Scenario: Post-cleanse failure restores buffs
- **WHEN** settlement fails after the cleanse removal (injected fault)
- **THEN** the potion key, the debuffs, and live buff reads are all restored to their pre-use state

#### Scenario: Cleanse entry shape is validated
- **WHEN** the item-effects rulebook gives a `blessed_cleansing` entry an `amount` field
- **THEN** the validated loader rejects it
