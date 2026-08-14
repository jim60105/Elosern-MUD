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
- **THEN** it contains no persona, skill, equipment, inventory, magic-level, or import-schema field

### Requirement: The server owns the persisted creation wizard draft
The deterministic core SHALL provide a creation-wizard draft service that is the sole writer of the pending character's draft. The draft SHALL persist across logout, login, server reload, and WebSocket reconnect and SHALL store exactly the server-accepted mode and values: for `preset` mode, the stage `preset_selected` and the accepted `preset_key`; for `custom` mode, the stage `custom_filled`, `display_name`, `age`, `apparent_age`, `race`, `subrace`, the six `allocations`, and the optional `affinity_elements` (bounded by the race-dependent maximum, elf `none`); and for the concept path, the stage `concept_filled`, `race`, `subrace`, `allocations`, and an optional persona block (`personality`, `life_story`, `habit` bounded text fields) accepted only from the deterministic concept-apply service. Saving a custom draft SHALL validate every accepted value through the existing deterministic preflight before persisting, and SHALL preserve the concept draft's persona block only when the submitted race equals the concept draft's race, clearing it otherwise. Activation SHALL re-validate the draft and the actor's ownership and pending state inside one deterministic `transaction.atomic()` block, call the existing all-or-nothing activation service (which persists the persona block into `entity.db.persona` in the import-card shape when present), and clear the draft in the same transaction so a completed character never retains a draft and two concurrent activations cannot both apply. A reset SHALL clear the draft idempotently. No value SHALL be accepted from a client control the server did not declare, and an incomplete or skipped draft SHALL NOT activate. The draft SHALL NOT set canonical identity attributes, traits, or `creation_pending` on the character; a rejected or cancelled save SHALL leave the canonical identity attributes, the trait set, and any previously validated draft unchanged. Persona content SHALL NOT be exposed in any panel payload.

#### Scenario: A saved draft survives reconnect
- **WHEN** a pending character saves a validated custom draft, disconnects, and logs in again
- **THEN** the creation panel rebuilds from the persisted draft (including the saved `affinity_elements`) and the browser resumes at the saved stage without re-typing accepted values

#### Scenario: Activation clears the draft atomically
- **WHEN** `creation.activate` commits successfully
- **THEN** the draft (including any persona block) is cleared in the same transaction that flips `creation_pending` to false, and no subsequent snapshot returns the draft

#### Scenario: A draft-clear write failure rolls back activation
- **WHEN** a write failure is injected into the draft-clearing step of the activation transaction
- **THEN** the whole activation rolls back, the character remains pending with its prior draft and trait state, and no canonical identity or mechanical state is written

#### Scenario: Concurrent activation applies exactly once
- **WHEN** two live sessions submit `creation.activate` for the same pending character around the same time
- **THEN** the first commit flips `creation_pending` to false and clears the draft, the second fails its re-checked pending or ownership validation, and the character activates exactly once

#### Scenario: Invalid draft input is rejected without mutation
- **WHEN** a custom draft is saved with a name containing a markup delimiter, an underage value, an unknown race, an incompatible subrace, allocations outside the profile bounds or budget, or an affinity set that violates the race-dependent maximum
- **THEN** the save is rejected with a stable reason, no value is persisted, and the character remains pending with its prior draft unchanged

#### Scenario: Reset is idempotent
- **WHEN** `creation.reset` succeeds on a pending character with and without a saved draft
- **THEN** the draft is absent in both cases, the character remains pending, and a repeated reset reports the same success

### Requirement: Creation actions are exact, allowlisted, and server-authoritative
The production action registry SHALL register exactly `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, and `creation.reset` for this delivery unit in addition to the three combat and seven service adapters and no unrelated gameplay adapter. `creation.preset` SHALL accept exactly `preset_key` (a 1..64-character non-empty string that exists in the player-preset registry). `creation.custom` SHALL accept exactly `display_name` (1..64 characters), `age` and `apparent_age` (integers in 0..10000 excluding booleans; the deterministic creation service independently enforces the adult minimum on every submission), `race` (a 1..64-character registry key), `subrace` (null or a 1..64-character registry key), `allocations` (an object containing exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense`, each an integer in 0..10000 excluding booleans), and optional `affinity_elements` (an array of at most 8 lowercase element keys, each a lore element; the deterministic creation service enforces the race-dependent maximum and rejects a player-supplied set on an elf). `creation.concept` SHALL accept exactly `concept` (a non-empty string of at most the declared bound), SHALL run the guarded `character_creation` generative layer with the injected client, and SHALL call the deterministic concept-apply service to save the `concept_filled` draft (including its server-owned persona block). `creation.activate` and `creation.reset` SHALL each accept exactly an empty payload. Every adapter SHALL obtain the account from the authenticated session's puppet, SHALL reject any actor/account/session/puppet/calculated-stat/unknown field, SHALL validate through the existing deterministic creation service (`preflight_character_creation`, `activate_player_character`, and the creation-wizard draft service), and SHALL NOT assign `.db`, traits, identity attributes, or `creation_pending` directly. No action SHALL route an action ID or payload through the text command parser.

#### Scenario: Preset selection reaches the deterministic registry
- **WHEN** a pending character submits `creation.preset` with a shipped preset key
- **THEN** the adapter validates the key against the immutable preset registry, saves the `preset_selected` draft, and refreshes the `creation` panel

#### Scenario: Preset selection is a two-step confirmation in the browser
- **WHEN** a browser player chooses a preset card and then confirms it
- **THEN** the flow submits `creation.preset` with the preset key and then `creation.activate`, sharing the same deterministic activation service the `character preset <key>` command uses while keeping the browser confirmation step explicit

#### Scenario: Custom submission runs the existing preflight
- **WHEN** a pending character submits `creation.custom` with a complete valid custom request, including `affinity_elements` within the race-dependent maximum
- **THEN** the adapter builds the request and validates it through `preflight_character_creation`, saves the `custom_filled` draft, and reports success

#### Scenario: An overlong display name is rejected before the deterministic service
- **WHEN** a client submits `creation.custom` with a `display_name` longer than 64 characters
- **THEN** the adapter rejects it structurally without invoking the deterministic service

#### Scenario: A concept submission fills the draft through the guarded pipeline
- **WHEN** a pending character submits `creation.concept` with a bounded concept and the guarded layer returns a valid proposal with a matching draft fingerprint
- **THEN** the adapter validates the proposal deterministically, saves the `concept_filled` draft including the server-owned persona block, and refreshes the `creation` panel with pre-filled finite controls and the background-generated indicator

#### Scenario: An abnormal puppet cannot reach a write path
- **WHEN** an adapter is dispatched with a puppet that has no accessible owning account, is not a `PlayerCharacter`, or is not in `account.characters`
- **THEN** the adapter rejects with a stable ownership/creation reason before any deterministic write and no draft, trait, or identity value changes

#### Scenario: An unknown field cannot sneak past activation
- **WHEN** a client submits any creation action carrying an actor, account, session, persona, skill, equipment, magic-level, or calculated-stat field
- **THEN** exact-schema validation rejects the request without invoking the adapter or the deterministic service

#### Scenario: A skipped or incomplete draft cannot activate
- **WHEN** `creation.activate` is submitted while no valid draft exists or the draft stage is incomplete
- **THEN** the adapter rejects before `activate_player_character`, the character remains pending, and no trait or identity is written

#### Scenario: An over-bound affinity set on an elf is rejected
- **WHEN** a client submits `creation.custom` with `race == "elf"` and a non-empty `affinity_elements`
- **THEN** the deterministic service rejects the request before persistence and no draft or identity value changes
