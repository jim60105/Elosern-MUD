## MODIFIED Requirements

### Requirement: Creation presentation derives finite controls from immutable registries
The `presets` array SHALL contain at most 8 preset cards, each with exactly `key` (1..64), `display_name` (1..128), `race` (1..64), `race_description` (1..512), nullable `subrace`, `emphasis` (1..256), and `background` (1..256), derived from `PLAYER_PRESET_REGISTRY` and the race registry rather than duplicated literals. The `custom` object SHALL contain exactly `name`, `adult`, `races`, `subraces`, `profiles`, and `affinity`. `name` SHALL contain exactly `min_length` 1 and `max_length` 64, mirroring the deterministic display-name bound (the shared entity-key contract). `adult` SHALL contain exactly `age_minimum` 18, `age_maximum` 10000, `apparent_age_minimum` 18, and `apparent_age_maximum` 10000. `races` SHALL be a list of at most 8 race options, each with exactly `key` (1..64), `description` (1..512), and `subraces` (a list of subrace keys or a single null). `subraces` SHALL map at most 16 subrace keys to exactly `display_name_zh`, `common_name_zh`, and `specialty`, each 1..256 code points. `profiles` SHALL contain at most 16 entries, one per race/subrace combination, each with exactly `race`, `subrace` (null or a key), `budget`, and `axes`; each axis SHALL contain exactly `axis`, `label`, `explanation`, `minimum`, and `maximum`, with `axis` from `hp`, `mp`, `sp`, `atk_phys`, `agility`, or `defense`, integer `budget`/`minimum`/`maximum` within JavaScript-safe range, and the six-axis set matching `resolve_starting_profile`. `affinity` SHALL map each race key (`human`, `beastfolk`, `elf`) to exactly `maximum` (integer `2`, `1`, and `0` respectively) and `elements` (exactly the eight lore element choices, each with `key` and `label`, derived from `ELEMENT_REGISTRY`). The panel SHALL NOT expose persona, skills, equipment, inventory, magic-level, or import-only fields merely because a character-card schema defines them.

#### Scenario: Preset cards render from registry data
- **WHEN** the creation panel ships for a pending character
- **THEN** each preset card names the registry preset key and the registry-derived display name, race, race description, subrace, emphasis, and background with no duplicated string literal

#### Scenario: Custom descriptor carries server-advertised bounds and profiles
- **WHEN** the custom descriptor ships for human, beastfolk, and elf
- **THEN** every race option carries its registry description and subrace list, every (race, subrace) profile carries the exact allocatable axes and budget from `resolve_starting_profile`, the adult fields advertise a minimum of 18, `name` advertises `min_length` 1 and `max_length` 64, and `affinity` advertises the race-dependent maximum (human 2, beastfolk 1, elf 0) with the eight element choices

#### Scenario: Custom descriptor omits import-only fields
- **WHEN** the custom descriptor is inspected
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-schema field

### Requirement: Creation actions are exact, allowlisted, and server-authoritative
The production action registry SHALL register exactly `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, and `creation.reset` for this delivery unit in addition to the three combat and seven service adapters and no unrelated gameplay adapter. `creation.preset` SHALL accept exactly `preset_key` (a 1..64-character non-empty string that exists in the player-preset registry). `creation.custom` SHALL accept exactly `display_name` (1..64 characters), `age` and `apparent_age` (integers in 0..10000 excluding booleans; the deterministic creation service independently enforces the adult minimum on every submission), `race` (a 1..64-character registry key), `subrace` (a 1..64-character registry key belonging to the race; the deterministic service rejects a missing or incompatible subrace), `allocations` (an object containing exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense`, each an integer in 0..10000 excluding booleans), optional `affinity_elements` (an array of at most 8 lowercase element keys, each a lore element; the deterministic creation service enforces the race-dependent maximum and rejects a player-supplied set on an elf), and an optional `background` (a string of at most the declared persona-field bound; a missing value is treated as an empty background). `creation.concept` SHALL accept exactly `concept` (a non-empty string of at most the declared bound), SHALL run the guarded `character_creation` generative layer with the injected client, and SHALL call the deterministic concept-apply service to save the `concept_filled` draft (including its server-owned persona block). `creation.activate` and `creation.reset` SHALL each accept exactly an empty payload. Every adapter SHALL obtain the account from the authenticated session's puppet, SHALL reject any actor/account/session/puppet/calculated-stat/unknown field, SHALL validate through the existing deterministic creation service (`preflight_character_creation`, `activate_player_character`, and the creation-wizard draft service), and SHALL NOT assign `.db`, traits, identity attributes, or `creation_pending` directly. No action SHALL route an action ID or payload through the text command parser.

#### Scenario: Preset selection reaches the deterministic registry
- **WHEN** a pending character submits `creation.preset` with a shipped preset key
- **THEN** the adapter validates the key against the immutable preset registry, saves the `preset_selected` draft, and refreshes the `creation` panel

#### Scenario: Preset selection is a two-step confirmation in the browser
- **WHEN** a browser player chooses a preset card and then confirms it
- **THEN** the flow submits `creation.preset` with the preset key and then `creation.activate`, sharing the same deterministic activation service the `character preset <key>` command uses while keeping the browser confirmation step explicit

#### Scenario: Custom submission runs the existing preflight
- **WHEN** a pending character submits `creation.custom` with a complete valid custom request including a registered subrace, an optional bounded background, and `affinity_elements` within the race-dependent maximum
- **THEN** the adapter builds the request and validates it through `preflight_character_creation`, saves the `custom_filled` draft, and reports success

#### Scenario: A missing or incompatible subrace is rejected before activation
- **WHEN** a client submits `creation.custom` with no `subrace`, an empty `subrace`, or a subrace key that does not belong to the submitted race
- **THEN** the deterministic service rejects with a stable reason and no draft, trait, or identity value changes

#### Scenario: An overlong display name is rejected before the deterministic service
- **WHEN** a client submits `creation.custom` with a `display_name` longer than 64 characters
- **THEN** the adapter rejects it structurally without invoking the deterministic service

#### Scenario: An over-bound background is rejected
- **WHEN** a client submits `creation.custom` with a `background` longer than the declared persona-field bound
- **THEN** the adapter or deterministic service rejects it before activation and the character remains pending

#### Scenario: A concept submission fills the draft through the guarded pipeline
- **WHEN** a pending character submits `creation.concept` with a bounded concept and the guarded layer returns a valid proposal with a matching draft fingerprint
- **THEN** the adapter validates the proposal deterministically, saves the `concept_filled` draft including the server-owned persona block, and refreshes the `creation` panel with pre-filled finite controls and the background-generated indicator

#### Scenario: An abnormal puppet cannot reach a write path
- **WHEN** an adapter is dispatched with a puppet that has no accessible owning account, is not a `PlayerCharacter`, or is not in `account.characters`
- **THEN** the adapter rejects with a stable ownership/creation reason before any deterministic write and no draft, trait, or identity value changes

#### Scenario: An unknown field cannot sneak past activation
- **WHEN** a client submits any creation action carrying an actor, account, session, persona prose, skill, equipment, starting-magic, or calculated-stat field
- **THEN** exact-schema validation rejects the request without invoking the adapter or the deterministic service

#### Scenario: A skipped or incomplete draft cannot activate
- **WHEN** `creation.activate` is submitted while no valid draft exists or the draft stage is incomplete
- **THEN** the adapter rejects before `activate_player_character`, the character remains pending, and no trait or identity is written

#### Scenario: An over-bound affinity set on an elf is rejected
- **WHEN** a client submits `creation.custom` with `race == "elf"` and a non-empty `affinity_elements`
- **THEN** the deterministic service rejects the request before persistence and no draft or identity value changes

### Requirement: The creation dock is keyboard-first, form-capable, and confirmation-protected
In `creation` mode the action dock SHALL present preset cards and the custom form rather
than exploration or service menus. Arrow keys SHALL navigate finite lists and buttons, Tab
and Shift+Tab SHALL move focus through text/numeric fields, Enter SHALL activate the
focused control or submit a complete server-declared form, and Escape SHALL pop exactly one
menu level without discarding the saved server wizard draft. The custom form SHALL require a
subrace selection (no "無子種族" radio is rendered), SHALL display an allocation briefing
(total budget, seven-axis count, each axis's 0–span, and the sum-must-equal-budget rule)
above the allocation fields, and SHALL provide a bounded optional background text field. The
form action buttons (confirm, reset, cancel, and concept-apply) SHALL be operable by
pointer through the shared focus/disabled/submission gate as well as by keyboard, and SHALL
pre-empt the keyboard bridge (a capture-phase listener) while the form owns focus, so keys
the form owns are claimed by the form and none reach the bridge's fall-through text path;
the capture listener SHALL be removed when the form closes. The final activation and the
destructive custom reset SHALL each require an explicit confirmation panel. Disabled entries
SHALL remain focusable with their explanation and SHALL submit nothing. Validation messages
SHALL be associated with the field they concern and announced through the accessible live
region. A stale revision SHALL preserve typed unsent values locally where safe, refresh
server-declared choices, and ask the player to review rather than automatically resubmitting.
No canonical service or creation state SHALL be stored in localStorage.

#### Scenario: Custom form completes without typed commands
- **WHEN** a player uses arrows and Tab/Shift+Tab to choose race and subrace, reviews the
  allocation briefing, types name, ages, allocations, and an optional background into the
  fields, confirms, and activates
- **THEN** the flow submits exactly `creation.custom` once with the expected payload
  (including the required subrace and any background), then `creation.activate` once, and
  the exploration snapshot follows

#### Scenario: The custom form cannot submit without a subrace
- **WHEN** a player leaves the subrace unselected in the custom form and confirms
- **THEN** the form reports the missing subrace against the subrace field and sends no
  `creation.custom` mutation

#### Scenario: The allocation briefing renders before the fields
- **WHEN** the custom form renders race and subrace with a resolvable profile
- **THEN** it displays the profile budget, the seven-axis count, each axis's 0–span range,
  and the rule that the total must equal the budget above the allocation inputs

#### Scenario: Form action buttons respond to pointer clicks
- **WHEN** a player clicks the confirm, reset, cancel, or concept-apply button with the
  pointer
- **THEN** the button runs the identical action the keyboard Enter would run, obeying the
  shared disabled/in-flight/awaiting-revision gate, and no unclaimed keydown reaches the
  bridge's fall-through text path for clicks or for keys the form owns

#### Scenario: The form claims its keys without breaking native input
- **WHEN** a player types or presses Tab, modifier, or IME-composition keys while the
  custom form owns focus
- **THEN** native focus movement, text input, and Chinese IME continue to work (no
  `preventDefault` on those keys), the form's capture-phase pre-emption claims those keys
  (so no unclaimed keydown reaches the bridge), and a held or repeated Enter submits at most
  once

#### Scenario: A pointer click and a keyboard Enter cannot double-submit
- **WHEN** a player activates a form button by pointer while the same button also receives a
  keyboard-synthesized Enter
- **THEN** exactly one `creation.*` mutation is emitted per deliberate activation, with the
  in-flight / awaiting-revision gate and the pointer bridge's primary-single-activation
  check suppressing the duplicate

#### Scenario: Activation and reset require confirmation
- **WHEN** the player focuses activation or the custom reset but has not confirmed
- **THEN** no mutation is sent and Escape returns exactly one menu level without activating
  or clearing the draft
