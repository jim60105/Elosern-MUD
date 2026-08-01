## ADDED Requirements

### Requirement: Newly registered accounts have an inert pending player character
When Evennia creates the default `PlayerCharacter` for a newly registered
account, the project account hook SHALL call its parent hook before marking that
same account-owned character pending creation. While pending, command-set
resolution SHALL derive a `mergetype="Replace"` creation-only gate with a
priority above local exits and with `no_exits` and `no_objs` enabled. It SHALL
expose only the character-creation command and harmless assistance or
disconnect commands, rejecting every in-world command before it reaches a
rules API or advances the world clock. The pending marker SHALL persist across
logout, login, and server reload; activation SHALL only change the marker, not
perform an independently fallible command-set removal.

#### Scenario: A new account cannot rest before completing creation
- **WHEN** a newly registered account's auto-created character enters `rest 5s`
- **THEN** it receives a creation-required message, no magic-study code is
  called, and the world clock does not advance

#### Scenario: A pending character remains pending after reconnecting
- **WHEN** an account disconnects before completing character creation and
  later logs in again
- **THEN** its same account-owned character remains pending and gameplay
  commands remain unavailable until successful completion

#### Scenario: Pending state blocks traversal and object commands
- **WHEN** a pending character attempts a normal exit traversal or an
  object-targeting command
- **THEN** the creation-only gate rejects it before room, object, or rules state
  is changed

#### Scenario: The account hook retains Evennia ownership state
- **WHEN** a new account is created
- **THEN** its pending shell remains in `account.characters`, is the account's
  last puppet, and retains the parent hook's ownership locks

### Requirement: Character creation offers preset and custom modes
The pending character's creation command SHALL offer exactly two activation
modes. A preset mode SHALL select a key from the immutable player-preset
catalog. A custom mode SHALL collect a non-empty player-supplied display name,
actual age, apparent age, a race key, an optional compatible subrace key, and
six stat allocations. The custom mode SHALL not accept player-supplied raw
magic level, guild merit, skills, equipment, or trait caps. The requested
display name SHALL be trimmed, contain 1–80 printable non-control characters,
contain no Evennia markup delimiter, and become the activated object's visible
key.

#### Scenario: A player selects a shipped preset
- **WHEN** a pending player selects a registered preset key
- **THEN** the system derives the preset's validated identity and allocation,
  initializes the account-owned character, and marks it active

#### Scenario: A player creates a custom character
- **WHEN** a pending player completes the custom creation prompts with a valid
  name, adult identity, compatible race/subrace, and valid allocations
- **THEN** the system initializes that account-owned character with the chosen
  identity and calculated trait values, then marks it active

#### Scenario: An invalid display name is rejected before activation
- **WHEN** custom creation supplies a blank, overlong, control-character, or
  markup-delimiter-bearing display name
- **THEN** activation is rejected and the account-owned shell retains its
  existing key and pending state

#### Scenario: Invalid draft input changes no character state
- **WHEN** a custom creation draft is cancelled, disconnected, or rejected for
  an invalid field before confirmation
- **THEN** the character remains pending with its prior empty trait set and no
  identity or magic-level value is persisted

### Requirement: Character creation enforces adult identity and registry compatibility
Both preset and custom activation SHALL require `age` and `apparent_age` to be
independent integer values of at least 18. The selected race SHALL exist in
`RACE_REGISTRY`; an optional subrace SHALL exist in `SUBRACE_REGISTRY` and
belong to that race. Successful activation SHALL persist the accepted age,
apparent age, race, subrace, and display name on the player character.

#### Scenario: Actual age below adulthood is rejected
- **WHEN** custom creation supplies `age=17` with an adult apparent age
- **THEN** activation is rejected, the character remains pending, and no traits
  are written

#### Scenario: Apparent age below adulthood is rejected independently
- **WHEN** custom creation supplies an adult actual age and `apparent_age=17`
- **THEN** activation is rejected, the character remains pending, and no traits
  are written

#### Scenario: A subrace belonging to another race is rejected
- **WHEN** custom creation chooses a subrace whose registry `race_key` differs
  from the selected race
- **THEN** activation is rejected before persistence with an explanation of the
  mismatch

### Requirement: Activation is an all-or-nothing deterministic-core operation
The creation command SHALL submit a validated request to a deterministic
`world.rules` creation service. The service SHALL preflight all fields and
allocation constraints before sampling a magic value, then atomically write
the trait configuration, identity attributes, sampled starting magic level,
active state, and creation-owned initial mechanical state: `magic_xp`, skill
proficiency, skills, equipment, inventory, wallet, quest log, guild rank, and
guild merit. If any write fails, it SHALL restore all persisted and in-process
trait state and leave the character pending. Activation SHALL not create, move,
or puppet an object; the shell's dbref, account relation, location, and
puppeting remain unchanged.

#### Scenario: An activation write failure leaves no partially initialized character
- **WHEN** a test injects a failure at any activation write position after
  preflight
- **THEN** the character has its original pending state, trait data, identity
  attributes, and magic-progress attributes, with no active command set
  enabled

#### Scenario: Successful activation enables normal gameplay exactly once
- **WHEN** a valid activation commits
- **THEN** the pending gate is removed, the normal character command set is
  available, and a subsequent `rest 5s` reaches the world clock with a real
  `magic_level` trait

#### Scenario: Activation does not change the existing shell's placement or ownership
- **WHEN** a valid activation commits for an already puppeted pending shell
- **THEN** its dbref, `account.characters` membership, location, and current
  puppet relationship are unchanged
