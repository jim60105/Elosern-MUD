# Spec Delta

## MODIFIED Requirements

### Requirement: Inventory mutations use exact allowlisted UI actions
The production UI action registry SHALL register `inventory.use` and `inventory.toggle_equip`.
`inventory.toggle_equip` SHALL accept exactly `{actor_id, item_key}`, where `actor_id` names the member
whose equipment toggles and is reauthorized by the party member boundary. `inventory.use` SHALL accept
exactly `{actor_id, item_key}` or `{actor_id, item_key, target_key}`, where `actor_id` names the
member who uses the item from that member's own bag (reauthorized for the acting purpose) and each key
is a bounded non-empty string containing no whitespace. A supplied `target_key` SHALL name **whom** an effect reaches and SHALL NOT
influence **what** the item does. The authenticated session SHALL be the only exploration actor source.

#### Scenario: Item use delegates once
- **WHEN** an authenticated player in exploration submits `inventory.use` naming a present member and one item that member holds
- **THEN** the adapter reauthorizes the member, revalidates current state and invokes the exploration deterministic facade exactly once with that member as user

#### Scenario: Client cannot choose an effect or slot
- **WHEN** an inventory payload includes an `effect`, `slot`, or other extra field
- **THEN** exact payload validation rejects it before adapter invocation and state remains unchanged

#### Scenario: Whitespace-bearing item keys are rejected
- **WHEN** an inventory payload carries an `item_key` containing a space, tab, or line break
- **THEN** exact payload validation rejects it before adapter invocation and state remains unchanged

#### Scenario: Unknown action cannot reach item rules
- **WHEN** a client submits an unregistered inventory action ID
- **THEN** the dispatcher rejects it without invoking an item, equipment, or text-command path

#### Scenario: A supplied target cannot widen an item's reach
- **WHEN** an `inventory.use` payload supplies a `target_key` for an item whose every effect is scoped
  to the acting entity
- **THEN** the target is ignored by scope resolution and the item affects only the actor, exactly as it
  would with no target supplied

#### Scenario: A target key naming a group shorthand is rejected
- **WHEN** an `inventory.use` payload supplies a `target_key` equal to a group shorthand token
- **THEN** the deterministic preflight rejects it, because group reach is fixed by the rulebook and is
  never selectable by the client

#### Scenario: Item keys stay byte-replayable in echoed input
- **WHEN** the whitespace ban on item and target keys is examined
- **THEN** it holds because the typed `use`/`equip` commands parse their arguments as
  whitespace-delimited tokens and the browser input echo prints the line verbatim, so an echoed
  line must stay byte-replayable

#### Scenario: Effects and scopes come from the item-effect rulebook
- **WHEN** an `inventory.use` settlement determines what an item does
- **THEN** the item's effects and their scopes are fixed by the item-effect rulebook, and a
  supplied target is consumed only by an effect the rulebook already scoped to a single entity

#### Scenario: Payloads reject non-key fields
- **WHEN** an `inventory.use` or `inventory.toggle_equip` payload carries quantity, effect,
  consumable, slot, HP, combat, or presentation fields, or omits `actor_id`
- **THEN** exact payload validation rejects it before adapter invocation

#### Scenario: Adapters use only public deterministic APIs
- **WHEN** an inventory adapter handles a validated payload
- **THEN** it re-resolves current canonical state and calls only the public deterministic
  item-use, combat-session, or equipment-toggle APIs, and it never assigns persistent state
  directly or routes through the text parser

#### Scenario: Active combat cannot use actorless inventory adapter
- **WHEN** inventory.use is submitted during a party combat session
- **THEN** it rejects without mutation; only guarded combat.command may save an actor item selection

#### Scenario: A companion's equipment toggles through the action
- **WHEN** `inventory.toggle_equip` names companion 艾拉 and a staff she holds
- **THEN** the adapter authorizes 艾拉 for the organizing purpose and toggles her equipment once, and a forged `actor_id` is rejected with `not_party_member` instead of toggling the commander

#### Scenario: A companion uses her own potion
- **WHEN** `inventory.use` names companion 艾拉 and a mana potion only 艾拉 holds
- **THEN** 艾拉's potion is consumed and her MP rises, and the same payload naming the commander is rejected because the commander holds none

### Requirement: Text clients expose the same deterministic item operations
The player command surface SHALL provide `使用 <item_key> [target] [= <成員>]` (alias `use`) and
`裝備 <item_key> [= <成員>]` (alias `equip`), passing only the parsed item key, for `使用` its optional
target token, and the resolved member (default: the caller) into the same deterministic APIs UI
adapters use. Both SHALL work in exploration and active combat: in combat `使用` saves the named
member's draft entry through the actor command path; equip toggles the named present member and stays
free.

#### Scenario: Command additions update both player documents
- **WHEN** a command key, alias, syntax, or context changes for this item surface
- **THEN** the same change updates both `docs/game/commands.md` and `docs/game/command-reference.md`

#### Scenario: Telnet healing matches WebClient healing
- **WHEN** equivalent injured actors in exploration use the same potion through the text command and `inventory.use`
- **THEN** both paths produce the same eligibility, HP, consumption and exploration-time outcomes

#### Scenario: Text equipment toggle uses exact item semantics
- **WHEN** a text client toggles a held accessory by item key
- **THEN** the same named accessory is equipped or unequipped under the five-slot rule without duplicating mutation logic

#### Scenario: Telnet targeting matches WebClient targeting
- **WHEN** equivalent actors in exploration use the same single-scope item on the same target, once through
  `使用 <item_key> <target>` and once through `inventory.use` with a `target_key`
- **THEN** both paths resolve the same target, apply the same effects, and consume the same resources

#### Scenario: A missing target renders the stable reason
- **WHEN** a text client runs `使用` on a single-scope item with no target argument
- **THEN** the no-target rejection renders in Traditional Chinese through the shared reason surface and
  nothing is consumed

#### Scenario: Combat use costs one round and equip costs none
- **WHEN** a text-client combat use is accepted before the draft is complete and, separately, a text-client equipment toggle completes
- **THEN** the combat use saves only the commander entry with no round/time/item consumption; the equipment toggle consumes no round

#### Scenario: Stable rejections match UI reason semantics
- **WHEN** a text command hits a stable rejection such as no-target or invalid-target
- **THEN** it renders the same Traditional Chinese reason semantics as the corresponding UI
  action

#### Scenario: Final text item selection has graphical command parity
- **WHEN** equivalent actors submit the same final item selection through combat command and guarded combat.command
- **THEN** both complete the same party draft and resolve the item at its actor initiative position with the same targets, costs and once-only round result

#### Scenario: Text equip names a companion
- **WHEN** a text client in combat runs `裝備 橡木圓盾 = 卡恩` while 卡恩 holds the shield
- **THEN** 卡恩's off hand toggles, no round or world time is consumed, and the result matches `inventory.toggle_equip` with 卡恩's `actor_id`

#### Scenario: Text use names a companion
- **WHEN** a text client outside combat runs `使用 魔力藥水 = 艾拉`
- **THEN** 艾拉 drinks her own potion with the same outcome as `inventory.use` naming 艾拉, and in combat the same line saves 艾拉's item draft entry instead
