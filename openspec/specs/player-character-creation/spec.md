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
The pending character's creation command SHALL offer exactly two activation modes. A preset mode SHALL select a key from the immutable player-preset catalog. A custom mode SHALL collect a non-empty player-supplied display name, actual age, apparent age, a race key, a required compatible subrace key (every race has at least one registered subrace, so no "none" selection exists), six stat allocations, and an optional bounded player-authored background (flavor) text. The custom mode SHALL not accept player-supplied raw magic level, guild merit, skills, equipment, or trait caps. The requested display name SHALL be trimmed, contain 1–64 printable non-control characters, contain no `|`, `/`, `:`, `{`, or `}` (the shared entity-key contract: no structural separator and no markup delimiter), and become the activated object's visible key. The background SHALL be accepted when present as a text field within the shared persona-field bound, may be left blank, and SHALL be persisted at activation inside the character's persona record so it survives every reload and can be inspected and freely updated by the owner afterwards.

The deterministic core MAY additionally persist a bounded, versioned `creation_draft` staging attribute on the pending character, written only through a `world.rules` creation-wizard service, to satisfy the WebClient's reconnect-at-saved-stage requirement. The staging attribute is not canonical identity: writing it SHALL NOT set `age`, `apparent_age`, `race`, `subrace`, the object key, traits, or `creation_pending` on the character, and it SHALL be cleared by the same atomic transaction that activates the character. A rejected or cancelled draft save SHALL leave the canonical identity attributes, the trait set, and any previously validated staging draft unchanged. A custom draft SHALL carry the accepted optional background text, which survives reconnect and is cleared atomically with the draft.

#### Scenario: A player selects a shipped preset
- **WHEN** a pending player selects a registered preset key
- **THEN** the system derives the preset's validated identity and allocation, initializes the account-owned character, and marks it active

#### Scenario: A player creates a custom character
- **WHEN** a pending player completes the custom creation prompts with a valid name, adult identity, compatible race and required subrace, valid allocations, and an optional background
- **THEN** the system initializes that account-owned character with the chosen identity and calculated trait values, persists the background in the persona record when supplied, then marks it active

#### Scenario: A custom creation without a subrace is rejected before activation
- **WHEN** custom creation supplies a race but omits a subrace (or sends an empty or `none` value)
- **THEN** activation is rejected with an explanation, and the account-owned shell retains its existing key and pending state

#### Scenario: The custom background is persisted and later updatable
- **WHEN** a custom character activates with a non-empty background and the owner later updates the background
- **THEN** the persona record contains the submitted background after activation, and the later update changes only that field through the deterministic persona-write service, leaving the rest of the character state unchanged

#### Scenario: An invalid display name is rejected before activation
- **WHEN** custom creation supplies a blank, overlong, control-character, structural-separator-bearing, or markup-delimiter-bearing display name
- **THEN** activation is rejected and the account-owned shell retains its existing key and pending state

#### Scenario: Invalid draft input changes no character state
- **WHEN** a custom creation draft is cancelled, disconnected, or rejected for an invalid field before confirmation
- **THEN** the character remains pending with its prior empty trait set, its canonical identity attributes remain unchanged, and a rejected or cancelled save does not persist a new staging draft; an earlier validated staging draft, if any, is preserved so the browser can reconnect at the saved stage

#### Scenario: Activation clears the staging draft atomically
- **WHEN** a validated staging draft is activated through the deterministic service
- **THEN** the draft (including any background text) is cleared in the same all-or-nothing transaction that writes the character's identity, traits, and initial mechanical state, so no completed character retains a draft

### Requirement: Character creation enforces adult identity and registry compatibility
Both preset and custom activation SHALL require `age` and `apparent_age` to be independent integer values of at least 18. The selected race SHALL exist in `RACE_REGISTRY`. A subrace SHALL exist in `SUBRACE_REGISTRY` and belong to that race; in custom mode the subrace is required (every race has at least one registered subrace), while preset mode uses the preset's declared subrace. Successful activation SHALL persist the accepted age, apparent age, race, subrace, and display name on the player character.

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

### Requirement: Activation is an all-or-nothing deterministic-core operation
The creation command SHALL submit a validated request to a deterministic `world.rules` creation
service. The service SHALL preflight all fields and allocation constraints before sampling a magic
value, then atomically write the trait configuration, identity attributes, sampled starting magic
level, active state, and creation-owned initial mechanical state: `magic_xp`, skill proficiency,
skills, equipment, inventory, wallet, quest log, guild rank, and guild merit. If any write fails, it
SHALL restore all persisted and in-process trait state and leave the character pending. Activation
SHALL not create or puppet an object, and SHALL not change the shell's dbref, account relation, or
puppeting.

The relocation to the starting location is a separate, best-effort step taken only after the atomic
activation commit succeeds. It SHALL move the shell to 聖潔王都南門 (`capital_altoria` `(2,0)`), SHALL
NOT advance the world clock and SHALL NOT emit a player-move event, and SHALL NEVER roll back the
already-committed activation when it fails. It SHALL additionally record the South Gate's canonical
`grid:capital_altoria:2:0` node through `world.rules.map_knowledge.record_arrival()` (the
`map-knowledge` capability) without charging movement time, so a freshly activated character starts
with the starting location known on their minimap. If the starting location does not exist, the shell
SHALL remain in place, activation SHALL still succeed, the player SHALL receive a degradation notice
instead of the arrival welcome, and no map-knowledge observation SHALL be recorded.

#### Scenario: An activation write failure leaves no partially initialized character
- **WHEN** a test injects a failure at any activation write position after preflight
- **THEN** the character has its original pending state, trait data, identity attributes, and
  magic-progress attributes, with no active command set enabled

#### Scenario: Successful activation enables normal gameplay exactly once
- **WHEN** a valid activation commits
- **THEN** the pending gate is removed, the normal character command set is available, and a
  subsequent `rest 5s` reaches the world clock with a real `magic_level` trait

#### Scenario: Activation moves the shell to the starting location and records it
- **WHEN** a valid activation commits for an already puppeted pending shell and the 南門 room exists
- **THEN** its dbref, `account.characters` membership, and current puppet relationship are unchanged,
  its location is the 聖潔王都南門 room, the relocation does not advance the world clock, and its
  map-knowledge record contains the `grid:capital_altoria:2:0` node

#### Scenario: Activation succeeds even when the starting location is unavailable
- **WHEN** a valid activation commits but the 南門 room does not exist
- **THEN** activation still succeeds, the pending gate is still removed, the shell remains in place,
  the player receives a degradation notice rather than the arrival welcome, and no map-knowledge
  observation is recorded

#### Scenario: A failed relocation never rolls back activation and records nothing
- **WHEN** a valid activation commits but the relocation fails for any reason
- **THEN** the activation remains committed, the player remains able to play from wherever the
  shell is, and no map-knowledge observation is recorded

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
