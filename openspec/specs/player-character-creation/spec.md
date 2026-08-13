## Purpose

Define account-bound player character creation that gates the blank Evennia shell until deterministic activation succeeds.

## Requirements

### Requirement: Newly registered accounts have an inert pending player character
When Evennia creates the default `PlayerCharacter` for a newly registered account, the project account hook SHALL call its parent hook before marking that same account-owned character pending creation. While pending, command-set resolution SHALL derive a `mergetype="Replace"` creation-only gate with a priority above local exits and with `no_exits` and `no_objs` enabled. It SHALL expose only the character-creation command and harmless assistance or disconnect commands, rejecting every in-world command before it reaches a rules API or advances the world clock. The pending marker SHALL persist across logout, login, and server reload; activation SHALL only change the marker, not perform an independently fallible command-set removal.

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

### Requirement: Character creation offers preset and custom modes
The pending character's creation command SHALL offer exactly two activation modes. A preset mode SHALL select a key from the immutable player-preset catalog. A custom mode SHALL collect a non-empty player-supplied display name, actual age, apparent age, a race key, an optional compatible subrace key, and six stat allocations. The custom mode SHALL not accept player-supplied raw magic level, guild merit, skills, equipment, or trait caps. The requested display name SHALL be trimmed, contain 1–64 printable non-control characters, contain no `|`, `/`, `:`, `{`, or `}` (the shared entity-key contract: no structural separator and no markup delimiter), and become the activated object's visible key.

The deterministic core MAY additionally persist a bounded, versioned `creation_draft` staging attribute on the pending character, written only through a `world.rules` creation-wizard service, to satisfy the WebClient's reconnect-at-saved-stage requirement. The staging attribute is not canonical identity: writing it SHALL NOT set `age`, `apparent_age`, `race`, `subrace`, the object key, traits, or `creation_pending` on the character, and it SHALL be cleared by the same atomic transaction that activates the character. A rejected or cancelled draft save SHALL leave the canonical identity attributes, the trait set, and any previously validated staging draft unchanged.

#### Scenario: A player selects a shipped preset
- **WHEN** a pending player selects a registered preset key
- **THEN** the system derives the preset's validated identity and allocation, initializes the account-owned character, and marks it active

#### Scenario: A player creates a custom character
- **WHEN** a pending player completes the custom creation prompts with a valid name, adult identity, compatible race/subrace, and valid allocations
- **THEN** the system initializes that account-owned character with the chosen identity and calculated trait values, then marks it active

#### Scenario: An invalid display name is rejected before activation
- **WHEN** custom creation supplies a blank, overlong, control-character, structural-separator-bearing, or markup-delimiter-bearing display name
- **THEN** activation is rejected and the account-owned shell retains its existing key and pending state

#### Scenario: Invalid draft input changes no character state
- **WHEN** a custom creation draft is cancelled, disconnected, or rejected for an invalid field before confirmation
- **THEN** the character remains pending with its prior empty trait set, its canonical identity attributes remain unchanged, and a rejected or cancelled save does not persist a new staging draft; an earlier validated staging draft, if any, is preserved so the browser can reconnect at the saved stage

#### Scenario: Activation clears the staging draft atomically
- **WHEN** a validated staging draft is activated through the deterministic service
- **THEN** the draft is cleared in the same all-or-nothing transaction that writes the character's identity, traits, and initial mechanical state, so no completed character retains a draft

### Requirement: Character creation enforces adult identity and registry compatibility
Both preset and custom activation SHALL require `age` and `apparent_age` to be independent integer values of at least 18. The selected race SHALL exist in `RACE_REGISTRY`; an optional subrace SHALL exist in `SUBRACE_REGISTRY` and belong to that race. Successful activation SHALL persist the accepted age, apparent age, race, subrace, and display name on the player character.

#### Scenario: Actual age below adulthood is rejected
- **WHEN** custom creation supplies `age=17` with an adult apparent age
- **THEN** activation is rejected, the character remains pending, and no traits are written

#### Scenario: Apparent age below adulthood is rejected independently
- **WHEN** custom creation supplies an adult actual age and `apparent_age=17`
- **THEN** activation is rejected, the character remains pending, and no traits are written

#### Scenario: A subrace belonging to another race is rejected
- **WHEN** custom creation chooses a subrace whose registry `race_key` differs from the selected race
- **THEN** activation is rejected before persistence with an explanation of the mismatch

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
