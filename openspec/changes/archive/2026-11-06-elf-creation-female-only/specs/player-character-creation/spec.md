## MODIFIED Requirements

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
- **WHEN** custom creation supplies a sex value that is not a `SEX_VALUES` member, or one the selected race does not permit
- **THEN** preflight rejects the request with a stable reason before any persistence, and the account-owned shell retains its existing key and pending state

#### Scenario: An omitted sex normalizes to the default
- **WHEN** custom creation omits the sex (or the creation flow carries no sex channel at all, as on Telnet)
- **THEN** preflight normalizes it to `DEFAULT_SEX` when the selected race permits that member and otherwise to the race's single permitted sex, and activation persists that member value on the character

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
- **THEN** it is one of the `SEX_VALUES` members the selected race declares, and an omitted or null sex is normalized to the race-permitted default

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
Both preset and custom activation SHALL require `age` and `apparent_age` to be independent integer values within the 0..10000 reasonable range. The selected race SHALL exist in `RACE_REGISTRY` and SHALL bound the resolved sex to the race's declared sex set. A subrace SHALL exist in `SUBRACE_REGISTRY` and belong to that race. Successful activation SHALL persist the accepted age, apparent age, race, subrace, display name, and sex on the player character.

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
- **THEN** in custom mode a supplied sex SHALL be a `SEX_VALUES` member or omitted/null, while in preset mode the sex comes from the preset's own declared `sex` field and SHALL NOT fall back to `DEFAULT_SEX`; both modes then resolve that value through the same race-aware validator before persistence

#### Scenario: A custom elf request with a non-female sex is rejected before persistence
- **WHEN** custom creation chooses `race == "elf"` and supplies `sex="male"` or `sex="other"`
- **THEN** activation is rejected before any write, the character remains pending with no traits, and the rejection is the single deterministic sex/race error the WebClient adapter maps to its stable code and shared Traditional Chinese message

#### Scenario: A custom elf request with a female sex activates
- **WHEN** custom creation chooses `race == "elf"` and supplies `sex="female"`
- **THEN** activation commits and the activated character's `entity.sex` is `"female"`

#### Scenario: An omitted sex on an elf resolves to the race's sole permitted sex
- **WHEN** custom creation chooses `race == "elf"` and omits `sex` (or supplies `null`), as the Telnet wizard always does
- **THEN** the resolved sex is `"female"`, activation commits, and the stored draft carries that same concrete value

#### Scenario: Human and beastfolk keep the full vocabulary
- **WHEN** custom creation chooses `race == "human"` or `race == "beastfolk"` and supplies `sex="male"`, `"female"`, or `"other"`
- **THEN** activation commits with that exact member, and an omitted sex on either race still normalizes to `DEFAULT_SEX`

#### Scenario: An elf preset declaring a non-female sex is rejected
- **WHEN** a preset card declares `race == "elf"` and a `sex` other than `"female"`
- **THEN** the preset-mode preflight rejects it before any write with the same stable code and message the custom path uses, instead of activating a character the race forbids

#### Scenario: Persisted sex converges creation and import paths
- **WHEN** activation persists the accepted sex on the player character
- **THEN** the sex is written as the `entity.sex` attribute the character loader already honors, so creation and import paths converge on the same concrete value

### Requirement: Preset activation persists the preset's declared sex
Every `PlayerPreset` SHALL declare a `sex` field holding exactly one `SEX_VALUES` member permitted by the preset's race, and preset-mode activation SHALL persist that value as the activated character's `sex`.

#### Scenario: A preset activation persists the preset's declared sex
- **WHEN** a pending player activates a shipped preset declaring `sex="female"`
- **THEN** the activated character's `sex` is `"female"`, written atomically with the rest of the activation state

#### Scenario: A preset request never falls back to the vocabulary default
- **WHEN** a preset-mode `CharacterCreationRequest` is built without a `sex` field, as every preset entry point does
- **THEN** the resolved sex is the preset's declared value and is not `DEFAULT_SEX` unless the preset itself declares `"other"`

#### Scenario: Custom activation still uses the request's sex
- **WHEN** a pending player activates a custom draft carrying a `SEX_VALUES` member
- **THEN** the activated character's `sex` equals that value, and a custom draft with a null sex still normalizes to the race's permitted default

#### Scenario: A preset with an out-of-vocabulary sex is rejected at load
- **WHEN** a preset declares a `sex` that is not a `SEX_VALUES` member
- **THEN** importing `world.lore.player_presets` raises, so the invalid value can never reach a player's activation

#### Scenario: A preset whose sex its race forbids is rejected at load
- **WHEN** a preset declares a `sex` that is a `SEX_VALUES` member but is absent from its race's `allowed_sexes` — for example an elf card declaring `"male"` or `"other"`
- **THEN** the preset load validator raises naming the card, its race and its sex, so the card can never reach a player's activation

#### Scenario: A preset omitting sex fails at construction
- **WHEN** a `PlayerPreset` is constructed without the `sex` keyword argument
- **THEN** construction raises `TypeError`, so a new card cannot silently inherit `DEFAULT_SEX`

#### Scenario: Every shipped preset declares a concrete sex
- **WHEN** `PLAYER_PRESET_REGISTRY` is inspected
- **THEN** every entry declares a `SEX_VALUES` member its race permits, and the eight shipped cards all declare `"female"`

#### Scenario: Preflight resolves sex in the existing mode branch
- **WHEN** `preflight_character_creation` resolves the sex
- **THEN** it resolves in the same mode branch that resolves the display name, ages, race, and subrace: preset mode takes `preset.sex` and custom mode keeps `request.sex`, with both branches still normalized through the single race-aware validator before persistence, and a preset-mode request SHALL NOT fall back to `DEFAULT_SEX`

#### Scenario: The sex field is keyword-only from declaration onward
- **WHEN** the `PlayerPreset` dataclass is declared
- **THEN** `sex` is a required keyword argument (the dataclass declares `dataclasses.KW_ONLY` from this field onward), so a card that omits it fails at construction rather than silently inheriting the default

#### Scenario: The sex validator matches the other preset validators' timing
- **WHEN** a preset declares a value outside `SEX_VALUES`, or inside it but outside its race's declared set
- **THEN** it fails at registry load, never at player activation, matching the existing skill-kit, identity, affinity, and starting-item validators

#### Scenario: Surrounding surfaces are unchanged
- **WHEN** this requirement is implemented
- **THEN** `SEX_VALUES`, `DEFAULT_SEX`, the WebClient creation action payload schemas, the `creation` panel descriptor and both of its client renderers, and the Telnet wizard's prompts are unchanged; the one new constraint is that the resolved sex must lie in the selected race's declared set
