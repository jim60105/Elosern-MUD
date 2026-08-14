## MODIFIED Requirements

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
