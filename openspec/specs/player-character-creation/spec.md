## Purpose

Define account-bound player character creation that gates the blank Evennia shell until deterministic activation succeeds.

## Requirements

### Requirement: Newly registered accounts have an inert pending player character
When Evennia creates the default `PlayerCharacter` for a newly registered account, the project account hook SHALL call its parent hook before marking that same account-owned character pending creation. While pending, command-set resolution SHALL derive a `mergetype="Replace"` creation-only gate with a priority above local exits and with `no_exits` and `no_objs` enabled, exposing only the character-creation command and harmless assistance or disconnect commands.

#### Scenario: A new account cannot rest before completing creation
- **WHEN** a newly registered account's auto-created character enters `rest 5s`
- **THEN** it receives a creation-required message, no magic-study code is called, and the world clock does not advance

#### Scenario: A pending character remains pending after reconnecting
- **WHEN** an account disconnects before completing character creation and later logs in again
- **THEN** its same account-owned character remains pending and gameplay commands remain unavailable until successful completion

#### Scenario: Pending state blocks traversal and object commands
- **WHEN** a pending character attempts a normal exit traversal or an object-targeting command
- **THEN** the creation-only gate rejects it before room, object, or rules state is changed

#### Scenario: The account hook retains Evennia ownership state
- **WHEN** a new account is created
- **THEN** its pending shell remains in `account.characters`, is the account's last puppet, and retains the parent hook's ownership locks

#### Scenario: A reply to an open creation wizard prompt reaches the wizard
- **WHEN** a pending character has an open `character create` wizard prompt and replies to it
- **THEN** the reply is delivered to the wizard and advances, cancels, or rejects the flow exactly as the wizard defines, instead of being rejected by the gate

#### Scenario: A cancelled wizard tears down its prompt state
- **WHEN** a pending character replies `cancel` to an open creation wizard prompt
- **THEN** the wizard exits with the cancellation message, the character remains pending, and no prompt state remains to swallow later input

#### Scenario: A failed wizard tears down its prompt state
- **WHEN** a pending character replies to an open creation wizard prompt with an invalid value, such as a non-integer age
- **THEN** the wizard reports the invalid input, the character remains pending, and no prompt state remains to swallow later input

#### Scenario: Empty input with no open prompt is rejected like any in-world input
- **WHEN** a pending character sends an empty line while no creation wizard prompt is open
- **THEN** it receives the creation-required message

#### Scenario: A completed wizard leaves no prompt state behind
- **WHEN** a pending character completes the creation wizard successfully
- **THEN** the wizard tears down its prompt state so the gate never stays stuck swallowing later input

#### Scenario: A reply matching a gate-exposed command runs that command
- **WHEN** a pending character sends input that matches a command the creation gate exposes (for example `character`, `說明`, or `登出`), even while a creation wizard prompt is open
- **THEN** that exposed command runs instead of the reply being delivered to the wizard prompt

#### Scenario: The pending marker persists across a server reload
- **WHEN** the server reloads while a character is pending creation
- **THEN** the pending marker survives and the creation-only gate still applies after the reload

#### Scenario: Activation removes the gate by changing only the marker
- **WHEN** activation succeeds for a pending character
- **THEN** it changes only the pending marker and performs no independently fallible command-set removal step

### Requirement: Character creation offers preset and custom modes
The pending character's creation command SHALL offer exactly two activation modes. Preset mode SHALL select a key from an immutable player-preset catalog. Custom mode SHALL collect a non-empty player-supplied display name, actual age, apparent age, a race key, a required compatible subrace key, the full `ALLOCATABLE_AXES` stat allocations (all seven axes including `magic_power`), an optional background (flavor) text, an optional persona block, and an optional sex.

#### Scenario: A player selects a shipped preset
- **WHEN** a pending player selects a registered preset key
- **THEN** the system derives the preset's validated identity and allocation, initializes the account-owned character, and marks it active

#### Scenario: A player creates a custom character
- **WHEN** a pending player completes the custom creation prompts with a valid name, valid canonical ages, compatible race and required subrace, valid allocations, an optional background, and an optional sex
- **THEN** the system initializes that account-owned character with the chosen identity and calculated trait values, persists the background in the persona record when supplied, persists the accepted sex on the character, then marks it active

#### Scenario: A custom persona block persists at activation
- **WHEN** a custom character activates with a supplied persona block and a background
- **THEN** the persona record contains the three prose fields from the block plus the separate `background` key, and the character state is otherwise unchanged

#### Scenario: A custom creation without a subrace is rejected before activation
- **WHEN** custom creation supplies a race but omits a subrace (or sends an empty or `none` value)
- **THEN** activation is rejected with an explanation, and the account-owned shell retains its existing key and pending state

#### Scenario: The custom background is persisted and later updatable
- **WHEN** a custom character activates with a non-empty background and the owner later updates the background
- **THEN** the persona record contains the submitted background after activation, and the later update changes only that field through the deterministic persona-write service, leaving the rest of the character state unchanged

#### Scenario: An invalid display name is rejected before activation
- **WHEN** custom creation supplies a blank, overlong, control-character, structural-separator-bearing, or markup-delimiter-bearing display name
- **THEN** activation is rejected and the account-owned shell retains its existing key and pending state

#### Scenario: An invalid sex is rejected before activation
- **WHEN** custom creation supplies a sex value that is not a `SEX_VALUES` member
- **THEN** preflight rejects the request with a stable reason before any persistence, and the account-owned shell retains its existing key and pending state

#### Scenario: An omitted sex normalizes to the default
- **WHEN** custom creation omits the sex (or the creation flow carries no sex channel at all, as on Telnet)
- **THEN** preflight normalizes it to `DEFAULT_SEX` and activation persists that member value on the character

#### Scenario: Invalid draft input changes no character state
- **WHEN** a custom creation draft is cancelled, disconnected, or rejected for an invalid field before confirmation
- **THEN** the character remains pending with its prior empty trait set, its canonical identity attributes remain unchanged, and a rejected or cancelled save does not persist a new staging draft; an earlier validated staging draft, if any, is preserved so the browser can reconnect at the saved stage

#### Scenario: Activation clears the staging draft atomically
- **WHEN** a validated staging draft is activated through the deterministic service
- **THEN** the draft (including any background text, persona block, and accepted sex) is cleared in the same all-or-nothing transaction that writes the character's identity, traits, and initial mechanical state, so no completed character retains a draft

#### Scenario: Every race offers at least one subrace choice
- **WHEN** custom creation presents the subrace selection for any registered race
- **THEN** every race has at least one registered subrace to choose, so no "none" selection exists

#### Scenario: A custom persona block is all-or-nothing and bounded
- **WHEN** custom creation supplies a persona block
- **THEN** it consists of the three prose fields `personality`, `life_story`, and `habit`, each bounded by the shared persona-field bound, and the block is either fully present or absent, never partially filled

#### Scenario: The accepted sex follows the shared vocabulary
- **WHEN** custom creation accepts a sex value
- **THEN** it is one of the `SEX_VALUES` members, and an omitted or null sex is normalized to `DEFAULT_SEX`

#### Scenario: Custom mode refuses player-supplied power channels
- **WHEN** a custom creation request carries player-supplied raw magic level, guild merit, skills, equipment, or trait caps
- **THEN** the custom mode SHALL not accept any of them

#### Scenario: The display name follows the shared entity-key contract
- **WHEN** custom creation accepts a display name
- **THEN** it is trimmed, contains 1–64 printable non-control characters, contains no `|`, `/`, `:`, `{`, or `}` (no structural separator and no markup delimiter), and becomes the activated object's visible key

#### Scenario: The background is bounded, optional, and reload-durable
- **WHEN** custom creation supplies a background
- **THEN** it is accepted as a text field within the shared persona-field bound, may be left blank, is persisted at activation inside the character's persona record so it survives every reload, and can be inspected and freely updated by the owner afterwards

#### Scenario: Creation drafts stage only through the wizard service
- **WHEN** the WebClient needs reconnect-at-saved-stage support
- **THEN** the deterministic core MAY persist a bounded, versioned `creation_draft` staging attribute on the pending character, written only through a `world.rules` creation-wizard service

#### Scenario: Draft staging never touches canonical identity
- **WHEN** a `creation_draft` save succeeds
- **THEN** it SHALL NOT set `age`, `apparent_age`, `race`, `subrace`, `sex`, the object key, traits, or `creation_pending` on the character, because the staging attribute is not canonical identity

#### Scenario: Draft fields survive reconnect
- **WHEN** a custom draft is saved with the optional background text, a nullable persona block, and a normalized `sex`
- **THEN** those values survive a reconnect on the draft, and are cleared atomically with the draft at activation

### Requirement: Character creation enforces canonical identity and registry compatibility
Both preset and custom activation SHALL require `age` and `apparent_age` to be independent integer values within the 0..10000 reasonable range. The selected race SHALL exist in `RACE_REGISTRY`. A subrace SHALL exist in `SUBRACE_REGISTRY` and belong to that race. Successful activation SHALL persist the accepted age, apparent age, race, subrace, display name, and sex on the player character.

#### Scenario: Actual age below the range floor is rejected
- **WHEN** custom creation supplies `age=-1` with an in-range apparent age
- **THEN** activation is rejected, the character remains pending, and no traits are written

#### Scenario: Apparent age outside the range is rejected independently
- **WHEN** custom creation supplies an in-range actual age and `apparent_age=-1`
- **THEN** activation is rejected, the character remains pending, and no traits are written

#### Scenario: A subrace belonging to another race is rejected
- **WHEN** custom creation chooses a subrace whose registry `race_key` differs from the selected race
- **THEN** activation is rejected before persistence with an explanation of the mismatch

#### Scenario: A custom creation with no subrace is rejected
- **WHEN** custom creation supplies a race and valid canonical ages but no subrace
- **THEN** activation is rejected before persistence with an explanation, and the character remains pending

#### Scenario: An imported character without a subrace is rejected
- **WHEN** a character import record supplies a race but omits, blanks, or mis-assigns the subrace
- **THEN** the import rejects the record before any entity is created, since every race has at least one registered subrace and no imported character bypasses the mandatory-subrace contract

#### Scenario: Activation persists the accepted sex on the entity
- **WHEN** a custom character activates with `sex` set to a non-default `SEX_VALUES` member
- **THEN** the activated character's `entity.sex` holds exactly that member, and a rollback of the activation transaction restores the pending shell's prior sex state

#### Scenario: Preset activation carries the preset's declared sex
- **WHEN** a preset-mode activation succeeds
- **THEN** the activated character's `entity.sex` holds the preset's declared `sex`, and it is `DEFAULT_SEX` only when the preset itself declares `"other"`

#### Scenario: Subrace sourcing differs by creation mode
- **WHEN** creation resolves the subrace for a selected race
- **THEN** in custom mode the subrace is required (every race has at least one registered subrace), while preset mode uses the preset's declared subrace

#### Scenario: Sex sourcing and validation differ by creation mode
- **WHEN** creation resolves the sex
- **THEN** in custom mode a supplied sex SHALL be a `SEX_VALUES` member or omitted/null, the latter normalizing to `DEFAULT_SEX`, while in preset mode the sex comes from the preset's own declared `sex` field and SHALL NOT fall back to `DEFAULT_SEX`

#### Scenario: Persisted sex converges creation and import paths
- **WHEN** activation persists the accepted sex on the player character
- **THEN** the sex is written as the `entity.sex` attribute the character loader already honors, so creation and import paths converge on the same concrete value

### Requirement: Activation is an all-or-nothing deterministic-core operation
The creation command SHALL submit a validated request to a deterministic `world.rules` creation
service. The service SHALL preflight all fields and allocation constraints, then atomically write
the trait configuration (including the allocated `magic_power` static), identity attributes,
active state, and creation-owned initial mechanical state: skill proficiency,
skills, equipment, inventory, wallet, quest log, guild rank, and guild merit.

#### Scenario: An activation write failure leaves no partially initialized character
- **WHEN** a test injects a failure at any activation write position after preflight
- **THEN** the character has its original pending state, trait data, identity attributes, and
  initial mechanical attributes, with no active command set enabled

#### Scenario: Successful activation enables normal gameplay exactly once
- **WHEN** a valid activation commits
- **THEN** the pending gate is removed, the normal character command set is available, and a
  subsequent `rest 5s` reaches the world clock with a real `magic_power` trait

#### Scenario: Successful activation leaves the shell in place
- **WHEN** a valid activation commits for an already puppeted pending shell
- **THEN** its dbref, `account.characters` membership, and current puppet relationship are
  unchanged, its location is unchanged (the 虛境 birth room), the world clock does not advance,
  and no map-knowledge observation is recorded

#### Scenario: A failed activation restores all trait state
- **WHEN** any activation write fails
- **THEN** the service SHALL restore all persisted and in-process trait state and leave the character pending

#### Scenario: Activation never creates or puppets an object
- **WHEN** activation succeeds for a pending shell
- **THEN** it creates no new object and puppets nothing, and the shell's dbref, account relation, and puppeting are untouched

#### Scenario: Activation performs no relocation
- **WHEN** activation succeeds wherever the shell was created
- **THEN** the shell stays in its 虛境 birth location and activation itself records no map-knowledge observation

### Requirement: Preset activation grants the preset's declared skill kit
Preset mode SHALL additionally grant the selected preset's declared skill kit: every active key
SHALL be persisted into the character's `skills.active` and every passive key into
`skills.passive`, in the preset's declared order, inside the same all-or-nothing activation
transaction that writes identity, traits, and the remaining initial mechanical state.

#### Scenario: A preset activation persists the preset's skill kit
- **WHEN** a pending player activates a shipped preset that declares `active_skills` and
  `passive_skills`
- **THEN** the activated character's `db.skills` holds the declared active keys in declared order
  followed by any closure-added active keys, and the declared passive keys in declared order
  followed by any closure-added passive keys, written atomically with the activation, and the
  preset's `creation_draft`, if any, is cleared in the same transaction

#### Scenario: A deep preset kit arrives gate-usable
- **WHEN** a preset declares a skill whose prerequisite edge is unsatisfied by any declared key
- **THEN** the activated character owns the closed chain, the prerequisite's seeded proficiency is
  exactly the required value and never above, and `can_use_skill` passes for the declared skill

#### Scenario: A declared proficiency beats the auto-seed
- **WHEN** a preset declares a `skill_proficiency` entry below the value the seed would write for
  the same key
- **THEN** the activated character's stored proficiency is the declared value and the seed does not
  overwrite it

#### Scenario: Custom activation starts with innate skills only
- **WHEN** a pending player completes the custom creation flow
- **THEN** the activated character's `db.skills` is `{"active": [], "passive": []}`, so its only
  skills are the universal innate set, and its `skill_proficiency` is empty

#### Scenario: A preset kit with a registry-invalid skill is rejected at load
- **WHEN** a preset declares a skill key absent from `SKILL_REGISTRY`, an active key whose registry
  `SkillKind` is `PASSIVE` (or vice versa), or a `requires_divine_arts` skill on a race without
  `can_use_divine_arts`
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

#### Scenario: An invalid declared proficiency is rejected at load
- **WHEN** a preset declares a `skill_proficiency` key absent from `SKILL_REGISTRY`, a negative or
  non-numeric value, or the same key twice
- **THEN** importing `world.lore.player_presets` raises, so the invalid entry can never reach a
  player's activation

#### Scenario: Closure extension runs through the lineage ownership closure
- **WHEN** activation extends each declared skill list with the transitive prerequisite closure of the declared keys
- **THEN** it uses `world/rules/progression.py::lineage_ownership_closure`, appending closure-added keys after the declared ones so the declared order is preserved

#### Scenario: Proficiency is seeded over the closed set
- **WHEN** activation seeds `skill_proficiency` over the closed skill set
- **THEN** it does so through `world/rules/progression.py::seed_lineage_proficiency`, so a preset kit arrives gate-usable rather than owning a tip skill whose `can_use_skill` predicate fails

#### Scenario: A preset may declare explicit proficiency pairs
- **WHEN** a preset declares its own `skill_proficiency` as a tuple of `(skill_key, xp)` pairs
- **THEN** a declared entry SHALL always win over a seeded value, even when it leaves an edge unmet — the same precedence an explicit import record entry has

#### Scenario: Custom mode grants only the universal innate skills
- **WHEN** a custom activation completes
- **THEN** the character SHALL have no skills beyond the universal innate set (`basic_attack`, `flee`)

#### Scenario: Kit validation is load-time only
- **WHEN** a preset kit is validated
- **THEN** it SHALL reference only keys that exist in `SKILL_REGISTRY` with the matching `SkillKind` (active keys `SkillKind.ACTIVE`, passive keys `SkillKind.PASSIVE`), a preset SHALL NOT declare a `requires_divine_arts` skill unless its race `can_use_divine_arts`, and every declared `skill_proficiency` key SHALL resolve in `SKILL_REGISTRY` with a non-negative numeric value and no repeated key — an invalid kit or entry SHALL fail at registry load, never at player activation

#### Scenario: No player-facing surface exposes the skill kit
- **WHEN** the Telnet preset preview or the WebClient preset card renders a preset
- **THEN** neither surface exposes the kit, and the card contract and the `creation.preset` action payload are unchanged

### Requirement: Preset activation grants the preset's declared starting inventory
Preset mode SHALL additionally grant the selected preset's declared starting inventory: the
activated character's `inventory` SHALL equal the preset's `(item_key, quantity)` pairs flattened
into the flat repeated-key list shape in declared order, written inside the same all-or-nothing
activation transaction.

#### Scenario: A preset activation grants the declared starting items
- **WHEN** a pending player activates a shipped preset that declares `starting_items`
- **THEN** the activated character's `db.inventory` equals the declared pairs flattened by
  quantity in declared order, written atomically with the rest of the activation state, and the
  preset's subrace basic starting kit grants nothing extra

#### Scenario: Declared starting equipment is worn at activation
- **WHEN** a pending player activates a preset declaring `starting_equipment`
- **THEN** the activated character's `db.equipment` names every declared key in its resolved slot, the corresponding attached buffs are present, and the gauge ceilings reflect the worn set

#### Scenario: Undeclared items stay in the pack
- **WHEN** a preset declares `starting_items` containing an equippable key that is not in `starting_equipment`
- **THEN** that key remains in `db.inventory` and no equipment slot names it

#### Scenario: A rejected toggle rolls activation back
- **WHEN** a declared equipment toggle returns a rejected outcome during activation
- **THEN** activation raises naming the item key and the stable reason, rolls back entirely, and the character remains pending

#### Scenario: A failed activation leaves no equipment or buff residue
- **WHEN** a write failure is injected after the equipment toggles of a preset activation
- **THEN** `equipment`, `buffs`, and the gauge ceilings all read back at their pre-activation values, and the character remains pending

#### Scenario: Custom activation starts with its subrace kit
- **WHEN** a pending player completes the custom creation flow with a registered subrace
- **THEN** the activated character's `db.inventory` equals that subrace's basic starting kit
  flattened by quantity, never the empty list

#### Scenario: A preset kit with a registry-invalid item is rejected at load
- **WHEN** a preset declares an item key absent from `ITEM_REGISTRY`, a non-positive or
  non-integer quantity, or the same item key twice
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

#### Scenario: An invalid starting-equipment declaration is rejected at load
- **WHEN** a preset declares a `starting_equipment` key absent from its `starting_items`, a key that is not equipment, the same key twice, two keys claiming one singleton slot, or more accessories than `ACCESSORY_MAX_SLOTS`
- **THEN** importing `world.lore.player_presets` raises, so the invalid loadout can never reach a player's activation

#### Scenario: Subrace kit and kit validity rules around declared inventory
- **WHEN** a preset activation resolves starting inventory
- **THEN** the preset's declared inventory is not overridden by the chosen subrace's basic starting kit, custom mode instead starts with that subrace kit as defined by the `Custom activation grants the chosen subrace's basic starting kit` requirement, and a starting kit references only keys that exist in `ITEM_REGISTRY`, with a positive integer quantity per key and no repeated key — an invalid kit fails at registry load, never at player activation

#### Scenario: Starting equipment is a subset declaration worn through the sole equipment writer
- **WHEN** a preset declares `starting_equipment`, a tuple of item keys
- **THEN** the keys SHALL be a subset of its `starting_items`, every declared key is worn on the activated character applied through `world/rules/equipment.py::toggle_equipment` — the sole equipment writer — so the worn set, the gauge ceilings recomputed by `sync_equipment_gauge_limits`, and the attached-buff instances are all produced by the existing capability rather than a parallel implementation

#### Scenario: Equipment toggles run ordered inside the activation transaction
- **WHEN** activation applies the declared equipment toggles
- **THEN** they run inside the same all-or-nothing activation transaction, after the trait config is applied and after `inventory` is written, because the toggle preflight requires canonical inventory ownership and the ceiling recomputation reads the final trait values

#### Scenario: A rejected equipment toggle is never silently skipped
- **WHEN** a declared equipment toggle returns a rejected outcome
- **THEN** activation SHALL raise and roll the whole activation back, naming the item key and the stable rejection reason, and the rejected item SHALL NOT be silently skipped

#### Scenario: Buffs join the activation snapshot set
- **WHEN** activation runs equipment toggles, which write `db.buffs`
- **THEN** `buffs` SHALL join the activation attribute snapshot set, so a rolled-back activation leaves no readable equipment, buff, or gauge-ceiling residue in the in-process attribute cache

#### Scenario: Invalid starting-equipment declarations are authoring mistakes caught at load
- **WHEN** a `starting_equipment` declaration names a key absent from `starting_items`, a key whose `ItemDefinition.equipment_slot` is `None`, the same key twice, two keys claiming the same singleton slot, or more accessory keys than `ACCESSORY_MAX_SLOTS`
- **THEN** it SHALL fail at registry load, never at player activation, because each is an authoring mistake with no useful runtime meaning: `toggle_equipment` toggles rather than equips, and it silently replaces a singleton occupant

#### Scenario: Carried-but-undeclared items are granted unequipped
- **WHEN** a preset carries items it does not declare as `starting_equipment`
- **THEN** those items are granted unequipped, and the player equips them through the ordinary equipment surface

### Requirement: Every subrace has a validated basic starting equipment kit in the item catalog
Every subrace registered in `SUBRACE_REGISTRY` SHALL have a basic starting kit: a non-empty set of
item keys that all exist in `ITEM_REGISTRY` and all denote equipment — every kit item SHALL declare
an `equipment_slot`, so consumables and inspect-only items can never compose a kit. The kit
mapping SHALL live in an immutable lore registry keyed by subrace, validated at registry load
time, before any activation can observe the registry.

#### Scenario: Every registered subrace resolves a non-empty kit of registered equipment
- **WHEN** the starting-kit registry is inspected against `SUBRACE_REGISTRY` and `ITEM_REGISTRY`
- **THEN** every subrace key has exactly one kit, every kit is non-empty, and every item key in
  every kit resolves in `ITEM_REGISTRY` with a non-null `equipment_slot`

#### Scenario: A broken kit fails at load
- **WHEN** a starting-kit registry under construction omits a registered subrace, declares an
  unknown or non-equipment (no `equipment_slot`) item key, duplicates one item key within a kit,
  declares an empty kit, or declares a non-positive quantity
- **THEN** registry validation raises at load time instead of the broken kit ever reaching an
  activation

#### Scenario: A basic item is shared across kits
- **WHEN** two or more subrace kits declare the same basic equipment key (for example a common
  knife or leather armor)
- **THEN** both kits remain valid; sharing catalog items across subraces is conforming behavior

#### Scenario: Every race inherits fitting basic equipment
- **WHEN** every subrace of a registered race has a kit
- **THEN** every registered race likewise has fitting basic starting equipment available to its players

#### Scenario: Load-time kit validation covers every malformed shape
- **WHEN** the starting-kit registry is validated at load
- **THEN** a subrace without a kit, a kit referencing an unknown or non-equipment item key, a duplicated item key within one kit, an empty kit, or a non-positive quantity fails at load

#### Scenario: Kit gear fits lore identity; selections stay registry data
- **WHEN** a kit is authored for a subrace
- **THEN** the kit SHALL be composed of gear that fits its subrace's lore identity, while the concrete per-subrace selections are registry data deliberately NOT fixed by this requirement — only existence, equipment-only validity, sharing, and load-time enforcement are normative and mechanically tested

### Requirement: Custom activation grants the chosen subrace's basic starting kit
Custom-mode activation of a pending player shell SHALL set the character's starting inventory to
the chosen subrace's basic starting kit, flattened into the same repeated item-key list shape the
deterministic core already stores in `inventory`, written inside the same all-or-nothing activation
transaction as the identity, traits, and other creation-owned mechanical state.

#### Scenario: A custom character wakes with its subrace kit
- **WHEN** custom creation activates with a registered subrace whose kit declares item keys K1 and
  K2
- **THEN** the activated character's `inventory` contains exactly one entry per declared quantity
  of K1 and K2, the gear is visible through the normal inventory surface, and every kit item is
  worn: `db.equipment` names each key in the slot its `ItemDefinition.equipment_slot` resolves to,
  the corresponding attached buffs are present, and the gauge ceilings reflect the worn set

#### Scenario: Kit coverage holds for every subrace at activation
- **WHEN** custom activation runs once for each registered subrace
- **THEN** each activated character's `inventory` equals that subrace's kit expanded by quantity,
  with no subrace activated into an empty starting inventory

#### Scenario: A colliding or accessory-overflowing kit fails at registry load
- **WHEN** a starting-kit registry under construction declares one kit whose items claim the same
  singleton slot (for example two `weapon_main` keys), or declares more accessory items than
  `ACCESSORY_MAX_SLOTS`
- **THEN** importing the starting-kit registry raises at load time instead of the unwearable kit
  ever reaching a player's activation

#### Scenario: An activation write failure grants no kit items
- **WHEN** a test injects a failure at any activation write position after the kit was resolved
- **THEN** the character remains pending and its inventory retains its pre-activation value, with
  no partially granted kit

#### Scenario: An imported character is not re-kitted
- **WHEN** a character import record with its own declared inventory loads successfully
- **THEN** its inventory is exactly the record's inventory and no subrace kit is added, since the
  kit contract governs player-shell activation only

#### Scenario: The kit is resolved before any activation write
- **WHEN** custom activation begins writing
- **THEN** the kit SHALL have been resolved from the lore registry before any activation write, so an unresolvable kit fails preflight and leaves the character pending

#### Scenario: Preset mode grants only the preset's own inventory
- **WHEN** preset-mode activation grants starting inventory
- **THEN** it keeps granting only the preset's own declared inventory, never a subrace kit

#### Scenario: Kit items are worn through the shared wearing machinery
- **WHEN** custom activation grants the chosen subrace's kit
- **THEN** every kit item is additionally worn at activation: the derived `starting_equipment` is the kit's own keys, each landing in the slot resolved from its `ItemDefinition.equipment_slot` through `world/rules/equipment.py::toggle_equipment` — the same wearing machinery, running in the same position of the same all-or-nothing transaction, that preset activation uses, together with its attached buffs and gauge-ceiling recomputation

#### Scenario: An unwearable kit is a registry-load failure
- **WHEN** a kit's items cannot all be worn — two items claim the same singleton slot, or there are more accessories than `ACCESSORY_MAX_SLOTS`
- **THEN** the kit SHALL fail at registry load, never at player activation

### Requirement: Custom creation collects a race-bounded affinity element set
Custom mode SHALL additionally collect an optional element-affinity set whose size bound depends on
the selected race: a human may pick at most 2 elements, a beastfolk at most 1, and an elf picks
none. Activation SHALL write the resulting set to `entity.db.affinity_elements` inside the same
all-or-nothing activation transaction that writes identity, traits, and the remaining initial
mechanical state.

#### Scenario: A human custom character picks two affinity elements
- **WHEN** custom creation chooses `race == "human"` and supplies `affinity_elements == ["fire",
  "wind"]`
- **THEN** activation persists `entity.db.affinity_elements == ["fire", "wind"]` and both elements
  are favored

#### Scenario: A human picking a third element is rejected
- **WHEN** custom creation chooses `race == "human"` and supplies three elements
- **THEN** activation is rejected before persistence with an explanation of the two-element human
  bound

#### Scenario: A beastfolk picks at most one affinity element
- **WHEN** custom creation chooses `race == "beastfolk"` and supplies exactly one element
- **THEN** activation persists that single element, while a two-element beastfolk request is
  rejected before persistence

#### Scenario: An elf cannot supply an affinity set
- **WHEN** custom creation chooses `race == "elf"` and supplies any player-chosen affinity set
- **THEN** activation is rejected before persistence, and the elf's affinity set is instead seeded
  from the chosen subrace's `affinity_elements`

#### Scenario: An elf subrace seeds the affinity set at activation
- **WHEN** custom creation chooses `race == "elf"` and `subrace == "fionnen"` with no affinity input
- **THEN** activation persists `entity.db.affinity_elements == ["light"]`, matching
  `SUBRACE_REGISTRY["fionnen"].affinity_elements`

#### Scenario: Unknown or duplicate affinity elements are rejected
- **WHEN** custom creation supplies an element key absent from `ELEMENT_REGISTRY`, or repeats the
  same element twice
- **THEN** activation is rejected before persistence

#### Scenario: Elf affinity is derived from the subrace, never supplied
- **WHEN** custom creation selects an elf
- **THEN** the elf's affinity set SHALL be derived from the chosen subrace's `affinity_elements`, and a player-supplied affinity set on an elf SHALL be rejected

#### Scenario: Supplied elements are validated registry keys
- **WHEN** custom creation supplies affinity elements
- **THEN** every supplied element SHALL be a lowercase key present in `ELEMENT_REGISTRY`, with no duplicates

#### Scenario: Preset mode derives the affinity set from the preset
- **WHEN** preset-mode activation resolves the affinity set
- **THEN** it SHALL not collect an affinity set from the player; it SHALL derive the set from the selected preset's declared `affinity_elements`

#### Scenario: An empty affinity set yields neutral progression
- **WHEN** activation writes an empty affinity set
- **THEN** progression is neutral (×1.0 for every element)

### Requirement: Preset activation persists the preset's declared affinity set
Preset mode SHALL persist the selected preset's `affinity_elements` (possibly empty) into
`entity.db.affinity_elements` in the same all-or-nothing activation transaction that grants the
preset's skill kit.

#### Scenario: A preset with declared affinities activates with them
- **WHEN** a pending player activates a human or beastfolk preset whose `affinity_elements ==
  ["fire", "wind"]`
- **THEN** the activated character's `entity.db.affinity_elements` equals `["fire", "wind"]`

#### Scenario: A preset with an empty affinity set stays neutral
- **WHEN** a pending player activates a preset whose `affinity_elements` is empty
- **THEN** the activated character's `entity.db.affinity_elements` is empty and every element keeps
  the neutral ×1.0 multiplier

#### Scenario: An elf preset activates with its subrace seed, not a preset set
- **WHEN** a pending player activates an elf preset whose race/subrace is `fionnen`
- **THEN** the activated character's `entity.db.affinity_elements` equals
  `SUBRACE_REGISTRY["fionnen"].affinity_elements` (`["light"]`) regardless of the preset's own
  (empty) field

#### Scenario: A preset with an invalid affinity element fails at load
- **WHEN** a preset declares an affinity element absent from `ELEMENT_REGISTRY`, a duplicate, or any
  non-empty set on an elf preset
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

#### Scenario: Elf presets declare an empty affinity set
- **WHEN** an elf preset is authored
- **THEN** it SHALL declare an empty `affinity_elements` set — the elf's set is seeded from its subrace at activation, never from the preset

### Requirement: An account owns up to a configured number of independently created characters
The deployment SHALL configure the account character capacity through Evennia's
`MAX_NR_CHARACTERS` setting, derived from the `ELOSERN_MAX_CHARACTERS` environment knob with a
default of `5` and an inclusive 1-to-10 bound. An account SHALL be able to hold up to that many
player characters simultaneously, each carrying its own independent `creation_pending` lifecycle,
its own canonical identity attributes, and its own creation-gate cmdset resolution.

#### Scenario: An account holds several characters at once
- **WHEN** an account creates characters up to the configured capacity
- **THEN** every one of them appears in `account.characters`, each is marked pending creation, and
  each resolves its own creation-only command gate

#### Scenario: The capacity is enforced without side effects
- **WHEN** an account at the configured capacity requests one more character
- **THEN** the request returns the slot-limit error, no character object is created, and
  `account.characters` is unchanged

#### Scenario: Activation is per character
- **WHEN** an account owning two pending characters activates one of them through the
  deterministic-core activation
- **THEN** that character becomes activated with its chosen key and identity, and the other
  character remains pending with its own draft and gate intact

#### Scenario: The capacity knob is deployment-configurable
- **WHEN** the server is started with `ELOSERN_MAX_CHARACTERS=2`
- **THEN** an account can hold two characters and the third creation request is refused by the
  slot check

#### Scenario: Siblings never interfere with each other's state
- **WHEN** an account owns both pending and activated characters
- **THEN** activating one character SHALL NOT clear another's pending marker, and a pending sibling SHALL NOT restrict an activated character's command surface

#### Scenario: Explicitly created characters are marked pending too
- **WHEN** a character is created through `Account.create_character`
- **THEN** it SHALL receive the project account hook's pending marker, exactly as the account's first auto-created shell does

#### Scenario: Over-capacity requests are refused, not raised
- **WHEN** a creation request exceeds the configured capacity
- **THEN** the slot check SHALL refuse it without creating a character object, and the refusal SHALL be reported to the caller rather than raised

### Requirement: Preset activation persists the preset's declared sex
Every `PlayerPreset` SHALL declare a `sex` field holding exactly one
`SEX_VALUES` member, and preset-mode activation SHALL persist that value as the
activated character's `sex`.

#### Scenario: A preset activation persists the preset's declared sex
- **WHEN** a pending player activates a shipped preset declaring `sex="female"`
- **THEN** the activated character's `sex` is `"female"`, written atomically with the rest of the activation state

#### Scenario: A preset request never falls back to the vocabulary default
- **WHEN** a preset-mode `CharacterCreationRequest` is built without a `sex` field, as every preset entry point does
- **THEN** the resolved sex is the preset's declared value and is not `DEFAULT_SEX` unless the preset itself declares `"other"`

#### Scenario: Custom activation still uses the request's sex
- **WHEN** a pending player activates a custom draft carrying a `SEX_VALUES` member
- **THEN** the activated character's `sex` equals that value, and a custom draft with a null sex still normalizes to `DEFAULT_SEX`

#### Scenario: A preset with an out-of-vocabulary sex is rejected at load
- **WHEN** a preset declares a `sex` that is not a `SEX_VALUES` member
- **THEN** importing `world.lore.player_presets` raises, so the invalid value can never reach a player's activation

#### Scenario: A preset omitting sex fails at construction
- **WHEN** a `PlayerPreset` is constructed without the `sex` keyword argument
- **THEN** construction raises `TypeError`, so a new card cannot silently inherit `DEFAULT_SEX`

#### Scenario: Every shipped preset declares a concrete sex
- **WHEN** `PLAYER_PRESET_REGISTRY` is inspected
- **THEN** every entry declares a `SEX_VALUES` member, and the eight shipped cards all declare `"female"`

#### Scenario: Preflight resolves sex in the existing mode branch
- **WHEN** `preflight_character_creation` resolves the sex
- **THEN** it resolves in the same mode branch that resolves the display name, ages, race, and subrace: preset mode takes `preset.sex` and custom mode keeps `request.sex`, with both branches still normalized through the single `_validate_sex` validator before persistence, and a preset-mode request SHALL NOT fall back to `DEFAULT_SEX`

#### Scenario: The sex field is keyword-only from declaration onward
- **WHEN** the `PlayerPreset` dataclass is declared
- **THEN** `sex` is a required keyword argument (the dataclass declares `dataclasses.KW_ONLY` from this field onward), so a card that omits it fails at construction rather than silently inheriting the default

#### Scenario: The sex validator matches the other preset validators' timing
- **WHEN** a preset declares a value outside `SEX_VALUES`
- **THEN** it fails at registry load, never at player activation, matching the existing skill-kit, identity, affinity, and starting-item validators

#### Scenario: Surrounding surfaces are unchanged
- **WHEN** this requirement is implemented
- **THEN** custom creation, the WebClient creation action payload schemas, the Telnet wizard, and the import path are unchanged

### Requirement: The preset registry declares a full persona in import-card shape
Every `PlayerPreset` SHALL declare a keyword-only `persona` field holding a
frozen `PresetPersona` whose shape mirrors the persona record
`world/rules/persona.py` renders: `identity` (a `PresetIdentity` with `public`
and `hidden` layers), `personality`, `life_story`, `habit`, `appearance` (a
`PresetAppearance` carrying the seven `_SUBKEY_ORDER` sub-keys),
`social_connection` (a tuple of name/relationship string pairs), and
`background`.

#### Scenario: A shipped preset carries its background inside the persona
- **WHEN** `PLAYER_PRESET_REGISTRY` is inspected
- **THEN** no entry has a top-level `background` attribute, and every entry's `persona.background` holds the prose that the selection card renders

#### Scenario: to_record produces a PersonaStore-readable record
- **WHEN** `PresetPersona.to_record()` is called on a fully authored persona
- **THEN** the result is a mapping whose `identity` carries `public` and `hidden` sub-keys and whose `appearance` carries the declared sub-keys, and `PersonaStore.flatten()` renders it without raising

#### Scenario: An empty persona still yields the six-key import-card record
- **WHEN** `PresetPersona.to_record()` is called on a persona whose values are all empty
- **THEN** the result carries exactly the six `PERSONA_IMPORT_CARD_KEYS` with empty strings and empty containers, omits `background` and `identity.hidden`, and `PersonaStore.flatten()` over it returns `None` rather than raising

#### Scenario: The public view prunes the hidden identity layer
- **WHEN** a preset persona declaring a non-empty `identity.hidden` is written into a record and read through `PersonaStore.public_view()`
- **THEN** the hidden layer is absent from the public view while `identity.public` survives

#### Scenario: A structurally malformed persona is rejected at load
- **WHEN** a preset declares a non-string persona prose value, a non-`PresetAppearance` appearance, or a `social_connection` entry that is not a pair of strings
- **THEN** importing `world.lore.player_presets` raises, so the malformed persona can never reach a player's activation

#### Scenario: An over-long persona field is rejected at load
- **WHEN** a registered preset declares a persona prose value longer than `MAX_PERSONA_FIELD_LENGTH`
- **THEN** importing `world.rules.character_creation` raises from its registry sweep, naming the offending preset and field

#### Scenario: The card blurb stays inside the WebClient descriptor bound
- **WHEN** the repo-wide creation contract test inspects every shipped preset
- **THEN** each `persona.background` is at most `MAX_BACKGROUND_CODE_POINTS` code points

#### Scenario: The preset card contract is unchanged
- **WHEN** `build_preset_cards()` runs after the background moves into the persona
- **THEN** every `PresetCardView` carries the same field set and the same background text as before the move

#### Scenario: Appearance carries exactly the seven persona sub-keys
- **WHEN** a `PresetAppearance` is declared on a preset persona
- **THEN** it carries exactly the seven `_SUBKEY_ORDER` sub-keys `height`, `weight`, `measurement`, `style`, `overview`, `attire`, `feature`

#### Scenario: Background prose lives exactly once, inside the persona
- **WHEN** a `PlayerPreset` is declared
- **THEN** it SHALL NOT carry a separate top-level `background` field: the registry SHALL hold that prose exactly once, inside the persona

#### Scenario: to_record matches the shared custom/import record shape
- **WHEN** `PresetPersona.to_record()` produces the storage shape written to `entity.db.persona`
- **THEN** it matches the record shape custom activation and `world/rules/persona_edit.py` already produce: all six `PERSONA_IMPORT_CARD_KEYS` (`identity`, `personality`, `life_story`, `habit`, `appearance`, `social_connection`) SHALL always be present, unauthored prose keys holding `""` and unauthored structured keys holding `{}`; `identity.hidden` SHALL be omitted when empty; and `background` SHALL be included only when non-empty, exactly as a custom draft without a background omits the key

#### Scenario: Persona values are optional for incremental authoring
- **WHEN** a preset card is authored incrementally
- **THEN** every persona value SHALL be optional and default to empty, without a code change, and a minimally authored card still produces a record `PersonaStore.flatten()` and `PersonaStore.public_view()` read without error

#### Scenario: A non-PresetIdentity identity is rejected at load
- **WHEN** a preset persona declares a non-`PresetIdentity` identity
- **THEN** importing `world.lore.player_presets` raises at registry load, never at player activation, matching the existing skill-kit, identity, affinity, and starting-item validators

#### Scenario: Duplicate social-connection names are rejected at load
- **WHEN** a preset persona declares duplicate `social_connection` names
- **THEN** it SHALL be rejected the same way at registry load, because the stored name/relationship mapping would otherwise silently drop the earlier pair

#### Scenario: The prose bound is enforced by a rules-layer import sweep
- **WHEN** preset persona prose lengths are validated
- **THEN** because `world/lore/` SHALL NOT import `world/rules/`, the prose length bound SHALL be enforced by a load-time sweep in `world/rules/character_creation.py`, the module owning `MAX_PERSONA_FIELD_LENGTH`: every persona prose value of every registered preset SHALL be at most that bound, and a violation SHALL raise at import

#### Scenario: The card blurb derives from the persona background
- **WHEN** the selection card renders a preset
- **THEN** the blurb SHALL be derived from `persona.background`, and `PresetCardView`'s field set, the creation panel payload, and the `creation.preset` action payload SHALL be unchanged

#### Scenario: The card bound is pinned by a contract test, not a validator
- **WHEN** the WebClient preset-card descriptor bounds `background` at `MAX_BACKGROUND_CODE_POINTS` (256) while the persona bound is 600
- **THEN** a repo-wide contract test SHALL pin every shipped preset's `persona.background` at or under the card bound, so an author spending the full persona budget cannot silently overflow the card contract; this one bound is deliberately a contract test rather than a load-time validator, unlike every other preset constraint, because the constant lives in `web/webclient/presentation/creation.py` and neither `world/lore/` nor `world/rules/` may import the web layer to reach it — the test is the only place the two bounds can be compared without inverting a layering rule

#### Scenario: Activation is governed by a separate requirement
- **WHEN** this registry declares a persona record
- **THEN** activation behavior is outside this requirement: the record reaches `entity.db.persona` through the activation requirement "Preset activation persists the preset's declared persona"

### Requirement: Preset activation persists the preset's declared persona
Preset mode SHALL persist the selected preset's declared persona: activation
SHALL write `entity.db.persona` from `preset.persona.to_record()` inside the same
all-or-nothing transaction that writes identity, traits, skills, and inventory,
so a preset-created character is a persona owner from its first login exactly as
a custom-created one is.

#### Scenario: A preset activation persists the registry persona
- **WHEN** a pending player activates a shipped preset whose registry entry declares a persona
- **THEN** `entity.db.persona` equals that preset's `to_record()` output, written atomically with the rest of the activation state

#### Scenario: Both modes produce the same record key set
- **WHEN** a preset activation and a custom activation are compared
- **THEN** both records carry exactly the six `PERSONA_IMPORT_CARD_KEYS`, with `background` present in each only when that source supplied one

#### Scenario: A preset persona write failure rolls activation back
- **WHEN** a write failure is injected into the persona step of a preset activation
- **THEN** activation rolls back entirely, the character remains pending, and no identity, trait, skill, inventory, or persona state survives

#### Scenario: A preset character reaches the dialogue persona surface
- **WHEN** an NPC builds its dialogue context for a preset-created character whose declared persona carries dialogue-visible fields (identity, appearance, or social_connection)
- **THEN** the player persona block resolves from the written record instead of being absent, with the hidden identity layer excluded by the public-view policy

#### Scenario: A background-only preset record renders no dialogue block
- **WHEN** an NPC builds its dialogue context for a character created from a preset whose persona declares only a background
- **THEN** the persona record is written with the background intact, and no player persona block is injected — the same policy-excluded outcome a custom background-only record produces

#### Scenario: Custom activation output is unchanged
- **WHEN** a custom draft carrying a persona block and a background activates
- **THEN** the persisted record is identical to the record produced before the shared builder was introduced

#### Scenario: A persona write failure rolls activation back entirely
- **WHEN** the persona write fails during activation
- **THEN** activation SHALL roll back entirely, leaving the character pending with no canonical identity, trait, or persona state written

#### Scenario: One shared helper builds both modes' records
- **WHEN** either creation mode builds its persona record
- **THEN** both modes SHALL use one shared helper in `world/rules/character_creation.py`, which remains the sole writer of creation-generated persona, and the custom path's output SHALL be unchanged

#### Scenario: Consumers need no mode-dependent branch
- **WHEN** a preset-created character's persona record is consumed
- **THEN** it SHALL carry the same six `PERSONA_IMPORT_CARD_KEYS` a custom-created character's record carries, so no consumer — `PersonaStore`, the dialogue prompt builder, or `world/rules/persona_edit.py` — needs a mode-dependent branch

#### Scenario: Rendering remains consumer mode-blind policy
- **WHEN** a record's dialogue-visible fields are all empty in either creation mode
- **THEN** it produces no player dialogue block in either mode — whether any consumer renders anything is the consumer's own mode-blind policy, exactly as `persona-dialogue-injection` already dictates for custom records

### Requirement: Preset activation persists the preset's declared disguise layer and sexual baseline
Every `PlayerPreset` MAY declare a keyword-only `disguised_stats` field, a tuple of
`(axis_key, value)` pairs, and a keyword-only `sexual_baseline` field holding either a frozen
`PresetSexualBaseline` or `None`. Both SHALL default to the empty form, and the empty form SHALL
preserve today's behavior exactly.

#### Scenario: A declared disguise layer is persisted
- **WHEN** a pending player activates a preset declaring `disguised_stats`
- **THEN** `entity.db.disguised_stats` equals the declared mapping, written atomically with the rest of the activation state, and the character's true traits are unchanged

#### Scenario: An empty disguise declaration writes None
- **WHEN** a pending player activates a preset declaring no `disguised_stats`
- **THEN** `entity.db.disguised_stats` is `None`, which every existing reader already treats as absent

#### Scenario: A declared sexual baseline seeds the handler
- **WHEN** a pending player activates a preset declaring a `sexual_baseline`
- **THEN** `entity.db.sexual` equals the declared record and the constructed `entity.sexual` derives its fields from it rather than from the generic default

#### Scenario: An undeclared sexual baseline preserves the lazy default
- **WHEN** a pending player activates a preset declaring `sexual_baseline=None`
- **THEN** `entity.db.sexual` is absent and `SexualState` constructs from `_generic_default_baseline()` exactly as before this change

#### Scenario: A failed activation leaves no disguise or baseline residue
- **WHEN** a write failure is injected after the disguise and baseline writes of a preset activation
- **THEN** `disguised_stats` and `sexual` both read back at their pre-activation values and the character remains pending

#### Scenario: An invalid declaration is rejected at load
- **WHEN** a preset declares a non-string `disguised_stats` key, a non-integer value, a `sexual_baseline` level outside its vocabulary tuple, or a `sensitivity` key outside `BODY_PARTS` plus `GENERIC_BODY_PART`
- **THEN** importing `world.lore.player_presets` raises, so the invalid declaration can never reach a player's activation

#### Scenario: Activation persists the disguise mapping with import-loader normalization
- **WHEN** preset activation grants the declared disguise layer
- **THEN** it SHALL write `entity.db.disguised_stats` as the declared mapping, or `None` when the declaration is empty — the same normalization the import loader applies — inside the same all-or-nothing activation transaction

#### Scenario: Activation writes the sexual baseline only when declared
- **WHEN** preset activation resolves the sexual baseline
- **THEN** it SHALL write `entity.db.sexual` from `sexual_baseline.to_record()` only when the preset declares a baseline; when it declares `None`, activation SHALL write nothing, so `SexualState` keeps applying its generic default lazily on first construction

#### Scenario: The baseline type mirrors the import card
- **WHEN** a `PresetSexualBaseline` is declared
- **THEN** it SHALL mirror the import card's `sexual_baseline` object: `arousal`, `virgin`, and `sensitivity` are required, and `wetness`, `shame`, `exposure`, and `climax_phase` are optional, each omitted value defaulting through the existing `SexualState` construction rule rather than being written as a literal

#### Scenario: Disguise and sexual join the snapshot set
- **WHEN** activation snapshots its attribute set
- **THEN** `disguised_stats` and `sexual` SHALL join it, so a rolled-back activation leaves no readable disguise or sexual-baseline residue in the in-process attribute cache

#### Scenario: Disguise keys are not whitelist-restricted
- **WHEN** `disguised_stats` keys are validated
- **THEN** they SHALL NOT be restricted to a whitelist: `CHARACTER_SCHEMA_V1` constrains the field only to integer values, and preset parity with the import card is the point of the field

#### Scenario: Duplicate and non-boolean baseline defects fail at load
- **WHEN** a preset declares duplicate `disguised_stats` keys, duplicate `sensitivity` body parts, or a non-boolean `sexual_baseline.virgin`
- **THEN** it SHALL fail at registry load — the same silent-`dict()`-collapse and builder-laundering defects the proficiency validator already rejects
