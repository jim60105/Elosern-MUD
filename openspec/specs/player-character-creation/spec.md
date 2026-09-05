## Purpose

Define account-bound player character creation that gates the blank Evennia shell until deterministic activation succeeds.

## Requirements

### Requirement: Newly registered accounts have an inert pending player character
When Evennia creates the default `PlayerCharacter` for a newly registered account, the project account hook SHALL call its parent hook before marking that same account-owned character pending creation. While pending, command-set resolution SHALL derive a `mergetype="Replace"` creation-only gate with a priority above local exits and with `no_exits` and `no_objs` enabled. It SHALL expose only the character-creation command and harmless assistance or disconnect commands, rejecting every in-world command before it reaches a rules API or advances the world clock. While an interactive creation-wizard prompt that the creation surface itself started is open on the pending character, every unmatched or empty reply SHALL be delivered to that prompt so the wizard can resume, cancel, or reject it, and a completed, cancelled, or failed wizard SHALL tear down its prompt state so the gate never stays stuck; replies that match a command the gate exposes (for example `character`, `說明`, or `登出`) SHALL run that command instead. The pending marker SHALL persist across logout, login, and server reload; activation SHALL only change the marker, not perform an independently fallible command-set removal.

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

### Requirement: Character creation offers preset and custom modes
The pending character's creation command SHALL offer exactly two activation modes. A preset mode SHALL select a key from the immutable player-preset catalog. A custom mode SHALL collect a non-empty player-supplied display name, actual age, apparent age, a race key, a required compatible subrace key (every race has at least one registered subrace, so no "none" selection exists), the full `ALLOCATABLE_AXES` stat allocations (all seven axes including `magic_power`), an optional bounded player-authored background (flavor) text, an optional persona block (the three prose fields `personality`, `life_story`, `habit`, each bounded by the shared persona-field bound; the block is either fully present or absent, never partially filled), and an optional sex (one of the `SEX_VALUES` members; an omitted or null sex is normalized to `DEFAULT_SEX`). The custom mode SHALL not accept player-supplied raw magic level, guild merit, skills, equipment, or trait caps. The requested display name SHALL be trimmed, contain 1–64 printable non-control characters, contain no `|`, `/`, `:`, `{`, or `}` (the shared entity-key contract: no structural separator and no markup delimiter), and become the activated object's visible key. The background SHALL be accepted when present as a text field within the shared persona-field bound, may be left blank, and SHALL be persisted at activation inside the character's persona record so it survives every reload and can be inspected and freely updated by the owner afterwards. A custom persona block, when supplied, SHALL likewise persist at activation inside the same persona record.
The deterministic core MAY additionally persist a bounded, versioned `creation_draft` staging attribute on the pending character, written only through a `world.rules` creation-wizard service, to satisfy the WebClient's reconnect-at-saved-stage requirement. The staging attribute is not canonical identity: writing it SHALL NOT set `age`, `apparent_age`, `race`, `subrace`, `sex`, the object key, traits, or `creation_pending` on the character, and it SHALL be cleared by the same atomic transaction that activates the character. A rejected or cancelled draft save SHALL leave the canonical identity attributes, the trait set, and any previously validated staging draft unchanged. A custom draft SHALL carry the accepted optional background text, the accepted nullable persona block, and the accepted normalized `sex`, which survive reconnect and are cleared atomically with the draft.

#### Scenario: A player selects a shipped preset
- **WHEN** a pending player selects a registered preset key
- **THEN** the system derives the preset's validated identity and allocation, initializes the account-owned character, and marks it active

#### Scenario: A player creates a custom character
- **WHEN** a pending player completes the custom creation prompts with a valid name, adult identity, compatible race and required subrace, valid allocations, an optional background, and an optional sex
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

### Requirement: Character creation enforces adult identity and registry compatibility
Both preset and custom activation SHALL require `age` and `apparent_age` to be independent integer values of at least 18. The selected race SHALL exist in `RACE_REGISTRY`. A subrace SHALL exist in `SUBRACE_REGISTRY` and belong to that race; in custom mode the subrace is required (every race has at least one registered subrace), while preset mode uses the preset's declared subrace. A supplied sex SHALL be a `SEX_VALUES` member or omitted/null, the latter normalizing to `DEFAULT_SEX`. Successful activation SHALL persist the accepted age, apparent age, race, subrace, display name, and sex on the player character (the sex written as the `entity.sex` attribute the character loader already honors, so creation and import paths converge on the same concrete value).

#### Scenario: Actual age below adulthood is rejected
- **WHEN** custom creation supplies `age=17` with an adult apparent age
- **THEN** activation is rejected, the character remains pending, and no traits are written

#### Scenario: Apparent age below adulthood is rejected independently
- **WHEN** custom creation supplies an adult actual age and `apparent_age=17`
- **THEN** activation is rejected, the character remains pending, and no traits are written

#### Scenario: A subrace belonging to another race is rejected
- **WHEN** custom creation chooses a subrace whose registry `race_key` differs from the selected race
- **THEN** activation is rejected before persistence with an explanation of the mismatch

#### Scenario: A custom creation with no subrace is rejected
- **WHEN** custom creation supplies a race and a valid adult identity but no subrace
- **THEN** activation is rejected before persistence with an explanation, and the character remains pending

#### Scenario: An imported character without a subrace is rejected
- **WHEN** a character import record supplies a race but omits, blanks, or mis-assigns the subrace
- **THEN** the import rejects the record before any entity is created, since every race has at least one registered subrace and no imported character bypasses the mandatory-subrace contract

#### Scenario: Activation persists the accepted sex on the entity
- **WHEN** a custom character activates with `sex` set to a non-default `SEX_VALUES` member
- **THEN** the activated character's `entity.sex` holds exactly that member, and a rollback of the activation transaction restores the pending shell's prior sex state

#### Scenario: Preset activation carries the default sex
- **WHEN** a preset-mode activation succeeds (the preset catalog declares no sex)
- **THEN** the activated character's `entity.sex` holds `DEFAULT_SEX`

### Requirement: Activation is an all-or-nothing deterministic-core operation
The creation command SHALL submit a validated request to a deterministic `world.rules` creation
service. The service SHALL preflight all fields and allocation constraints, then atomically write
the trait configuration (including the allocated `magic_power` static), identity attributes,
active state, and creation-owned initial mechanical state: skill proficiency,
skills, equipment, inventory, wallet, quest log, guild rank, and guild merit. If any write fails, it
SHALL restore all persisted and in-process trait state and leave the character pending. Activation
SHALL not create or puppet an object, and SHALL not change the shell's dbref, account relation, or
puppeting. Activation performs no relocation: the shell stays wherever it was created (its 虛境
birth location), and no map-knowledge observation SHALL be recorded by activation itself.

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

### Requirement: Preset activation grants the preset's declared skill kit
Preset mode SHALL additionally grant the selected preset's declared skill kit: every active key
SHALL be persisted into the character's `skills.active` and every passive key into
`skills.passive`, in the preset's declared order, inside the same all-or-nothing activation
transaction that writes identity, traits, and the remaining initial mechanical state. Custom mode
SHALL grant no skills beyond the universal innate set (`basic_attack`, `flee`). A preset kit SHALL
reference only keys that exist in `SKILL_REGISTRY` with the matching `SkillKind` (active keys
`SkillKind.ACTIVE`, passive keys `SkillKind.PASSIVE`), and a preset SHALL NOT declare a
`requires_divine_arts` skill unless its race `can_use_divine_arts` — an invalid kit SHALL fail at
registry load, never at player activation. No player-facing surface (the Telnet preset preview or
the WebClient preset card) SHALL expose the kit; the card contract and the `creation.preset` action
payload are unchanged.

#### Scenario: A preset activation persists the preset's skill kit
- **WHEN** a pending player activates a shipped preset that declares `active_skills` and
  `passive_skills`
- **THEN** the activated character's `db.skills` equals `{"active": [<declared active keys in
  order>], "passive": [<declared passive keys in order>]}` written atomically with the activation,
  and the preset's `creation_draft`, if any, is cleared in the same transaction

#### Scenario: Custom activation starts with innate skills only
- **WHEN** a pending player completes the custom creation flow
- **THEN** the activated character's `db.skills` is `{"active": [], "passive": []}`, so its only
  skills are the universal innate set

#### Scenario: A preset kit with a registry-invalid skill is rejected at load
- **WHEN** a preset declares a skill key absent from `SKILL_REGISTRY`, an active key whose registry
  `SkillKind` is `PASSIVE` (or vice versa), or a `requires_divine_arts` skill on a race without
  `can_use_divine_arts`
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

### Requirement: Preset activation grants the preset's declared starting inventory
Preset mode SHALL additionally grant the selected preset's declared starting inventory: the
activated character's `inventory` SHALL equal the preset's `(item_key, quantity)` pairs flattened
into the flat repeated-key list shape in declared order, written inside the same all-or-nothing
activation transaction. A preset's declared inventory SHALL NOT be overridden by the chosen
subrace's basic starting kit. Custom mode SHALL instead start with the chosen subrace's basic
starting kit as defined by the `Custom activation grants the chosen subrace's basic starting kit`
requirement. A starting kit SHALL reference only keys that exist in `ITEM_REGISTRY`, with a
positive integer quantity per key and no repeated key — an invalid kit SHALL fail at registry
load, never at player activation. Starting items are granted unequipped; the player equips them
through the ordinary equipment surface.

#### Scenario: A preset activation grants the declared starting items
- **WHEN** a pending player activates a shipped preset that declares `starting_items`
- **THEN** the activated character's `db.inventory` equals the declared pairs flattened by
  quantity in declared order, written atomically with the rest of the activation state, and the
  preset's subrace basic starting kit grants nothing extra

#### Scenario: Custom activation starts with its subrace kit
- **WHEN** a pending player completes the custom creation flow with a registered subrace
- **THEN** the activated character's `db.inventory` equals that subrace's basic starting kit
  flattened by quantity, never the empty list

#### Scenario: A preset kit with a registry-invalid item is rejected at load
- **WHEN** a preset declares an item key absent from `ITEM_REGISTRY`, a non-positive or
  non-integer quantity, or the same item key twice
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

### Requirement: Every subrace has a validated basic starting equipment kit in the item catalog
Every subrace registered in `SUBRACE_REGISTRY` SHALL have a basic starting kit: a non-empty set of
item keys that all exist in `ITEM_REGISTRY` and all denote equipment — every kit item SHALL declare
an `equipment_slot`, so consumables and inspect-only items can never compose a kit. Because every
subrace has a kit, every registered race SHALL likewise have fitting basic starting equipment
available to its players. The kit mapping SHALL live in an immutable lore registry keyed by
subrace, validated at registry load time: a subrace without a kit, a kit referencing an unknown or
non-equipment item key, a duplicated item key within one kit, an empty kit, or a non-positive
quantity SHALL fail at load, before any activation can observe the registry. One item key MAY
appear in any number of subrace kits (basic gear is a shared catalog pool, not a per-subrace
bespoke item). Each kit SHALL be composed of gear that fits its subrace's lore identity; the
concrete per-subrace selections are registry data deliberately NOT fixed by this requirement —
only existence, equipment-only validity, sharing, and load-time enforcement are normative and
mechanically tested.

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

### Requirement: Custom activation grants the chosen subrace's basic starting kit
Custom-mode activation of a pending player shell SHALL set the character's starting inventory to
the chosen subrace's basic starting kit, flattened into the same repeated item-key list shape the
deterministic core already stores in `inventory`, written inside the same all-or-nothing activation
transaction as the identity, traits, and other creation-owned mechanical state. The kit SHALL be
resolved from the lore registry before any activation write, so an unresolvable kit fails preflight
and leaves the character pending. This applies only to player-shell creation activation: imported
characters keep their record-owned inventory unchanged and SHALL NOT receive a subrace kit.
Preset-mode activation SHALL keep granting only the preset's own declared inventory.

#### Scenario: A custom character wakes with its subrace kit
- **WHEN** custom creation activates with a registered subrace whose kit declares item keys K1 and
  K2
- **THEN** the activated character's `inventory` contains exactly one entry per declared quantity
  of K1 and K2, unequipped, and the gear is visible through the normal inventory surface

#### Scenario: Kit coverage holds for every subrace at activation
- **WHEN** custom activation runs once for each registered subrace
- **THEN** each activated character's `inventory` equals that subrace's kit expanded by quantity,
  with no subrace activated into an empty starting inventory

#### Scenario: An activation write failure grants no kit items
- **WHEN** a test injects a failure at any activation write position after the kit was resolved
- **THEN** the character remains pending and its inventory retains its pre-activation value, with
  no partially granted kit

#### Scenario: An imported character is not re-kitted
- **WHEN** a character import record with its own declared inventory loads successfully
- **THEN** its inventory is exactly the record's inventory and no subrace kit is added, since the
  kit contract governs player-shell activation only

### Requirement: Custom creation collects a race-bounded affinity element set
Custom mode SHALL additionally collect an optional element-affinity set whose size bound depends on
the selected race: a human may pick at most 2 elements, a beastfolk at most 1, and an elf picks none
(an elf's affinity set SHALL be derived from the chosen subrace's `affinity_elements`, and a
player-supplied affinity set on an elf SHALL be rejected). Every supplied element SHALL be a
lowercase key present in `ELEMENT_REGISTRY`, with no duplicates. Preset mode SHALL not collect an
affinity set; it SHALL derive the set from the selected preset's declared `affinity_elements`.
Activation SHALL write the resulting set to `entity.db.affinity_elements` inside the same
all-or-nothing activation transaction that writes identity, traits, and the remaining initial
mechanical state. An empty set yields neutral progression (×1.0 for every element).

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

### Requirement: Preset activation persists the preset's declared affinity set
Preset mode SHALL persist the selected preset's `affinity_elements` (possibly empty) into
`entity.db.affinity_elements` in the same all-or-nothing activation transaction that grants the
preset's skill kit. An elf preset SHALL declare an empty set — the elf's set is seeded from its
subrace at activation, never from the preset. The registry SHALL reject a preset whose declared
affinity elements include an unknown key, a duplicate, or (for an elf preset) any element — at
registry load, never at player activation.

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

### Requirement: An account owns up to a configured number of independently created characters
The deployment SHALL configure the account character capacity through Evennia's
`MAX_NR_CHARACTERS` setting, derived from the `ELOSERN_MAX_CHARACTERS` environment knob with a
default of `5` and an inclusive 1-to-10 bound. An account SHALL be able to hold up to that many
player characters simultaneously, each carrying its own independent `creation_pending` lifecycle,
its own canonical identity attributes, and its own creation-gate cmdset resolution: activating one
character SHALL NOT clear another's pending marker, and a pending sibling SHALL NOT restrict an
activated character's command surface. Every character created through
`Account.create_character` SHALL receive the project account hook's pending marker, exactly as the
account's first auto-created shell does. A creation request beyond the configured capacity SHALL
be refused by the slot check without creating a character object, and the refusal SHALL be
reported to the caller rather than raised.

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
