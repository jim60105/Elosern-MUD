## Purpose

The browser's graphical character-creation surface: a read-only `creation` panel
derived from immutable registries, a server-owned wizard draft so the browser
reconnects at any saved stage, four exact allowlisted creation action adapters,
a keyboard-first creation dock with confirmation screens, the server-
authoritative age-range gate, and the atomic exploration hand-off after activation.

## Requirements

### Requirement: Creation presents a bounded desktop identity form and allocation workspace
The creation wizard SHALL present a persistent portrait slot beside freely navigable identity, story and allocation steps, with confirmation in its shared footer. All current required and optional fields, errors and confirmation actions SHALL remain reachable at 1451x790 and 2560x1440 without page-level horizontal scrolling. Preset cards SHALL render server-supplied canonical artwork in one card wall without inventing media URLs.

#### Scenario: Custom form remains complete
- **WHEN** a keyboard user completes creation at the 1451x790 reference viewport
- **THEN** name, sex, both ages, race/subrace, allocations and optional fields are reachable in logical order, with visible errors and confirmation controls

#### Scenario: Preset lacks artwork
- **WHEN** a synthetic preset’s descriptor has no official image attempt
- **THEN** the card uses the supplied alpha terminal through the shared artwork loader, never a fabricated portrait URL

### Requirement: Creation controls preserve native entry and existing authority
Themed creation selects and checkboxes SHALL preserve native keyboard/IME behavior. Allocation steppers SHALL retain direct numeric entry and use only existing server bounds and budget rules; previews SHALL NOT become a second stat authority.

#### Scenario: Invalid allocation is edited
- **WHEN** a player types a value outside its advertised range
- **THEN** the existing validation/error path remains effective and preview does not silently make it valid

#### Scenario: Concept fill settles
- **WHEN** a concept proposal arrives while its request is in flight
- **THEN** the existing revision-gated custom-form fill and confirmation flow remain unchanged by layout

### Requirement: The creation panel is an exact read-only creation-mode panel
The production presentation registry SHALL register `creation` schema version 7. Its available
payload SHALL contain exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`,
and the optional `proposal`; `available` SHALL be true and `kind` SHALL be `creation`. The whole
panel SHALL use the registered common unavailable form outside `creation` mode and when the global
prerequisite fails.

#### Scenario: A pending character receives the creation panel
- **WHEN** a puppeted WebClient session with `creation_pending` true receives a full snapshot
- **THEN** `creation` reports `available` true, `kind` `creation`, schema version 7, the preset
  cards, the custom-form descriptor, and the current server-persisted draft while a before/after
  comparison of canonical game state is unchanged

#### Scenario: Activated and combat characters do not receive the creation panel
- **WHEN** the active puppet is not creation-pending or is in an active combat session
- **THEN** `creation` uses its schema-valid unavailable form and contains no preset card, field,
  draft, or proposal

#### Scenario: Creation presentation stays read-only
- **WHEN** the creation panel is built for a pending character with a saved draft, a pending session
  proposal, and a disguise-independent empty trait set
- **THEN** `creation_pending`, the wizard draft, the session proposal slot, identity attributes,
  traits, and world time are byte-for-byte unchanged and no skill, equipment, inventory, or
  import-schema field is exposed

#### Scenario: A stale schema version is rejected
- **WHEN** a `creation` panel payload declares `schema_version` 6, 5, 4, 3, 2, or any version other than 7
- **THEN** exact-schema validation rejects it on both the presenter and the mirrored browser
  validator rather than accepting a stale shape

#### Scenario: Schema version ships as the integer 6
- **WHEN** an available `creation` panel payload ships
- **THEN** `schema_version` carries the integer 7

#### Scenario: The proposal key mirrors the transient session proposal
- **WHEN** the authenticated session holds a transient concept proposal
- **THEN** the payload carries the `proposal` key with exactly the shape defined by the
  transient-fill contract — the base `revision`/`race`/`subrace`/`allocations`/`persona` keys plus
  the optional `display_name`, `age`, `apparent_age`, `background`, and `affinity_elements`
  transient-fill keys — and the presenter renders it from an immutable session snapshot copy
- **AND** when the session holds no transient concept proposal, the `proposal` key is absent

#### Scenario: Controls and previews derive from immutable sources
- **WHEN** the presenter builds the panel
- **THEN** every finite control and preview is derived from immutable registries and the
  deterministic starting-profile resolver

#### Scenario: The payload carries no live reference or path
- **WHEN** the presenter emits the `creation` payload
- **THEN** it contains no live object reference and no filesystem path

#### Scenario: Presentation mutates no game state
- **WHEN** the presenter builds and emits the panel
- **THEN** `creation_pending`, the wizard draft, the session proposal slot, traits, identity
  attributes, location, and world time are unchanged

#### Scenario: A partial failure fabricates no value
- **WHEN** a failure is confined to one field, preset, or profile
- **THEN** the panel does not fabricate a value

### Requirement: Creation presentation derives finite controls from immutable registries
The presenter SHALL derive bounded, exact-shape preset cards and custom controls from `PLAYER_PRESET_REGISTRY`, the race registry and the starting-profile resolver, never duplicated literals. Presets SHALL carry `artwork` and custom controls SHALL carry `silhouettes` under the schemas below.

#### Scenario: Preview additions preserve exact control shapes
- **WHEN** finite creation controls are serialized
- **THEN** `presets` contains at most 8 cards, each with exactly `key` (1..64), `display_name` (1..128), `race` (1..64), `race_description` (1..512), nullable `subrace`, `emphasis` (1..256), `background` (1..256), and `artwork`
- **AND** `custom` contains exactly `name`, `age`, `races`, `subraces`, `profiles`, `affinity`, `sex`, and `silhouettes`

#### Scenario: Preset cards render from registry data
- **WHEN** the creation panel ships for a pending character
- **THEN** each preset card names the registry preset key and the registry-derived display name, race, race description, subrace, emphasis, and background with no duplicated string literal

#### Scenario: Custom descriptor carries server-advertised bounds and profiles
- **WHEN** the custom descriptor ships under synthetic race and affinity registries
- **THEN** every race option carries its registry display name, description and subrace list, every (race, subrace) profile carries the exact allocatable axes and budget from `resolve_starting_profile`, the age and name fields retain their schema bounds, and `affinity` advertises each race’s declared maximum and registered element choices

#### Scenario: Custom descriptor advertises server-labelled sex options
- **WHEN** the custom descriptor ships for a pending character
- **THEN** `custom.sex` lists every `SEX_VALUES` member exactly once in registry order, each carrying the server-owned Traditional Chinese label with no label literal duplicated in browser code

#### Scenario: Custom descriptor omits import-only fields
- **WHEN** the custom descriptor is inspected
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-schema field

#### Scenario: The name descriptor mirrors the display-name bound
- **WHEN** the `custom.name` descriptor ships
- **THEN** it contains exactly `min_length` 1 and `max_length` 64, mirroring the deterministic
  display-name bound (the shared entity-key contract)

#### Scenario: The age descriptor carries the exact range bounds
- **WHEN** the `custom.age` descriptor ships
- **THEN** it contains exactly `age_minimum` 0, `age_maximum` 10000, `apparent_age_minimum` 0,
  and `apparent_age_maximum` 10000

#### Scenario: Race options carry their exact fields
- **WHEN** the `custom.races` list ships
- **THEN** it is a list of at most 8 race options, each with exactly `key` (1..64),
  `display_name_zh` (non-empty 1..128), `description` (1..512), and `subraces` (a list of subrace
  keys or a single null)

#### Scenario: The subraces map carries bounded localized fields
- **WHEN** the `custom.subraces` map ships
- **THEN** it maps at most 16 subrace keys to exactly `display_name_zh`, `common_name_zh`, and
  `specialty`, each 1..256 code points

#### Scenario: Profiles carry the exact seven-axis shape
- **WHEN** the `custom.profiles` list ships
- **THEN** it contains at most 16 entries, one per race/subrace combination, each with exactly
  `race`, `subrace` (null or a key), `budget`, and `axes`; each axis contains exactly `axis`,
  `label`, `explanation`, `minimum`, and `maximum`, with `axis` from `hp`, `mp`, `sp`, `atk_phys`,
  `agility`, `defense`, or `magic_power`, integer `budget`/`minimum`/`maximum` within
  JavaScript-safe range, and the seven-axis set matching `resolve_starting_profile`

#### Scenario: The affinity map carries race maxima and element choices
- **WHEN** the `custom.affinity` map ships
- **THEN** it maps each advertised race key to exactly `maximum` (that race’s declared integer bound) and `elements` (the registered element choices, each with `key` and `label`, derived from `ELEMENT_REGISTRY`)

#### Scenario: The sex descriptor lists every server value once
- **WHEN** the `custom.sex` list ships
- **THEN** it is a nonempty list of at most 8 sex options in `SEX_VALUES` order, each with exactly
  `key` (1..64 code points, one of the `SEX_VALUES` members) and `label` (1..64 code points of
  server-owned Traditional Chinese text derived server-side, never duplicated in the browser),
  covering every `SEX_VALUES` member exactly once

#### Scenario: Persona prose never enters control metadata
- **WHEN** the `custom` descriptor ships for a character-card-capable schema
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-only
  fields merely because a character-card schema defines them, and persona prose values appear only
  inside `draft.persona` and the transient `proposal` payload, never in control metadata

#### Scenario: Preset race keys resolve to custom race options
- **WHEN** a preset card's race key is checked against the custom descriptor
- **THEN** every preset race key resolves to a custom race option and its display name is reused
  for preset/confirmation display without changing action keys

### Requirement: The server owns the persisted creation wizard draft
The deterministic core SHALL provide a creation-wizard draft service that is the sole writer of the pending character's draft. The draft SHALL persist across logout, login, server reload, and WebSocket reconnect and SHALL store exactly the server-accepted mode and values. Saving a custom draft SHALL validate every accepted value through the existing deterministic preflight before persisting, and an incomplete or skipped draft SHALL NOT activate.

#### Scenario: A saved draft survives reconnect
- **WHEN** a pending character saves a validated custom draft (including the saved `affinity_elements`, an accepted background, a persona block, and an accepted `sex`), disconnects, and logs in again
- **THEN** the creation panel rebuilds from the persisted draft and the browser resumes at the saved stage without re-typing accepted values, including the affinity set, background text, persona block, and the saved sex selection

#### Scenario: An omitted sex is normalized into the draft
- **WHEN** a custom draft saves with a payload that omits `sex` or sends it null
- **THEN** the persisted draft stores the race-permitted default — `DEFAULT_SEX` when the selected race
  permits that member, otherwise that race's single permitted sex — as a concrete `SEX_VALUES`
  member, and the panel rebuild carries that value

#### Scenario: Activation clears the draft atomically
- **WHEN** `creation.activate` commits successfully
- **THEN** the draft (including any background, persona block, and accepted sex) is cleared in the same transaction that flips `creation_pending` to false, and no subsequent snapshot returns the draft

#### Scenario: A draft-clear write failure rolls back activation
- **WHEN** a write failure is injected into the draft-clearing step of the activation transaction
- **THEN** the whole activation rolls back, the character remains pending with its prior draft and trait state, and no canonical identity or mechanical state is written

#### Scenario: Concurrent activation applies exactly once
- **WHEN** two live sessions submit `creation.activate` for the same pending character around the same time
- **THEN** the first commit flips `creation_pending` to false and clears the draft, the second fails its re-checked pending or ownership validation, and the character activates exactly once

#### Scenario: Invalid draft input is rejected without mutation
- **WHEN** a custom draft is saved with a name containing a markup delimiter, an out-of-range age value, an unknown race, an incompatible or missing subrace, an over-bound background, a malformed persona block, allocations outside the profile bounds or budget, an affinity set that violates the race-dependent maximum, or a `sex` outside `SEX_VALUES` or outside the selected race's declared set
- **THEN** the save is rejected with a stable reason, no value is persisted, and the character remains pending with its prior draft unchanged

#### Scenario: A pre-version draft is treated as absent
- **WHEN** the draft service loads a stored draft whose `DRAFT_VERSION` predates the sex-carrying version
- **THEN** it is treated as no saved draft rather than partially accepted, and the browser resumes at the initial stage

#### Scenario: Reset is idempotent
- **WHEN** `creation.reset` succeeds on a pending character with and without a saved draft
- **THEN** the draft is absent in both cases, the character remains pending, and a repeated reset reports the same success

#### Scenario: The preset-mode draft stores exactly its accepted values
- **WHEN** a preset draft saves
- **THEN** it stores the stage `preset_selected` and the accepted `preset_key`

#### Scenario: The custom-mode draft stores exactly its accepted values
- **WHEN** a custom draft saves
- **THEN** it stores the stage `custom_filled`, `display_name`, `age`, `apparent_age`, `race`,
  `subrace`, the `allocations` (one entry per `ALLOCATABLE_AXES` axis), the optional
  `affinity_elements` (bounded by the race-dependent maximum, elf `none`), an optional bounded
  `background` text, a required nullable `persona` block (`personality`, `life_story`, `habit`
  bounded text fields) accepted only through the custom-save payload, and the accepted `sex`

#### Scenario: An unknown sex member is rejected at save time
- **WHEN** a custom draft saves with a `sex` that names a member outside `SEX_VALUES`, or a
  `SEX_VALUES` member the selected race does not permit
- **THEN** the save rejects — normalization at save time only maps an absent or null value to the
  race-permitted default, yielding a concrete `SEX_VALUES` member

#### Scenario: No concept stage exists
- **WHEN** the draft stages are enumerated
- **THEN** no concept stage exists between preset selection and custom fill

#### Scenario: Preflight covers every accepted custom value
- **WHEN** a custom draft save runs its preflight validation
- **THEN** it checks a required, registered, race-compatible subrace, a bounded optional
  background, the nullable persona block, and the race-aware sex normalization before persisting

#### Scenario: The persona is stored verbatim with no carry-over
- **WHEN** a custom draft saves a persona block after an earlier draft held a different one
- **THEN** the submitted persona is stored verbatim with no carry-over or comparison against any
  earlier value

#### Scenario: Activation revalidates inside one atomic transaction
- **WHEN** activation runs
- **THEN** the draft and the actor's ownership and pending state are re-validated inside one
  deterministic `transaction.atomic()` block and the existing all-or-nothing activation service is
  called, clearing the draft in the same transaction so a completed character never retains a
  draft and two concurrent activations cannot both apply

#### Scenario: Activation persists persona and sex canonically
- **WHEN** the activation service commits a draft carrying a persona block, a player background,
  and an accepted sex
- **THEN** the persona block and any player background persist into `entity.db.persona` in the
  import-card shape when present, and the accepted `sex` persists on the character entity

#### Scenario: Undeclared client controls are not accepted
- **WHEN** a draft write would take a value from a client control the server did not declare
- **THEN** no value is accepted from it

#### Scenario: The draft service writes no canonical state
- **WHEN** a draft saves, is rejected, or is cancelled
- **THEN** the draft sets no canonical identity attributes, traits, or `creation_pending` on the
  character, and the canonical identity attributes, the trait set, and any previously validated
  draft remain unchanged

### Requirement: Creation actions are exact, allowlisted, and server-authoritative
The production action registry SHALL register exactly `creation.preset`, `creation.custom`, `creation.concept`, `creation.roll_name`, `creation.activate`, `creation.reset`, and `creation.portrait.generate` for the creation surface. No adapter SHALL assign `.db`, traits, identity attributes, or `creation_pending` directly, and no action SHALL route an action ID or payload through the text command parser.

#### Scenario: Preset selection reaches the deterministic registry
- **WHEN** a pending character submits `creation.preset` with a registered synthetic preset key
- **THEN** the adapter validates the key against the immutable preset registry, saves the `preset_selected` draft, and refreshes the `creation` panel

#### Scenario: Preset selection is a two-step confirmation in the browser
- **WHEN** a browser player chooses a preset card and then confirms it
- **THEN** the flow submits `creation.preset` with the preset key and then `creation.activate`, sharing the same deterministic activation service the `character preset <key>` command uses while keeping the browser confirmation step explicit

#### Scenario: Custom submission runs the existing preflight
- **WHEN** a pending character submits `creation.custom` with a complete valid custom request including a registered subrace, an optional bounded background, a persona block or null, `affinity_elements` within the race-dependent maximum, and an optional `sex`
- **THEN** the adapter builds the request and validates it through `preflight_character_creation`, saves the `custom_filled` draft including the submitted persona and the normalized sex, and reports success

#### Scenario: Custom submission without a sex field normalizes to the default
- **WHEN** a pending character submits `creation.custom` with no `sex` key or an explicit null `sex`
- **THEN** the deterministic service accepts the request and the saved draft stores `DEFAULT_SEX`

#### Scenario: A custom submission with an unknown sex is rejected
- **WHEN** a client submits `creation.custom` with a `sex` string outside `SEX_VALUES`
- **THEN** the deterministic service rejects with a stable reason and no draft, trait, or identity value changes

#### Scenario: A missing or incompatible subrace is rejected before activation
- **WHEN** a client submits `creation.custom` with no `subrace`, an empty `subrace`, or a subrace key that does not belong to the submitted race
- **THEN** the deterministic service rejects with a stable reason and no draft, trait, or identity value changes

#### Scenario: An overlong display name is rejected before the deterministic service
- **WHEN** a client submits `creation.custom` with a `display_name` longer than 64 characters
- **THEN** the adapter rejects it structurally without invoking the deterministic service

#### Scenario: An over-bound background is rejected
- **WHEN** a client submits `creation.custom` with a `background` longer than the declared persona-field bound
- **THEN** the adapter or deterministic service rejects it before activation and the character remains pending

#### Scenario: A concept submission delivers a transient proposal
- **WHEN** a pending character submits `creation.concept` with a bounded concept and the guarded layer returns a valid proposal
- **THEN** the adapter stores the proposal in the session-scoped transient slot with zero persistent writes, returns the applied outcome, and refreshes the `creation` panel carrying the proposal

#### Scenario: A roll-name submission returns a display name with zero writes
- **WHEN** a pending character submits `creation.roll_name` with a valid race, subrace, and sex (or nulls)
- **THEN** the adapter returns outcome `success` with `data.display_name` from `roll_name_for_race`, no draft, trait, identity, `creation_pending`, or session-slot value changes, and no panel refresh is emitted

#### Scenario: An activated character cannot roll names
- **WHEN** `creation.roll_name` is submitted for an owned character whose `creation_pending` flag is no longer set
- **THEN** the adapter rejects with the established `already_complete` code and Traditional Chinese message, the roller is never invoked, no result `data` slot is emitted, and no panel refresh is published

#### Scenario: An unregistered roll-name race is rejected instead of falling back
- **WHEN** `creation.roll_name` is submitted with a structurally valid 1..64-character `race` key that is not a `RACE_REGISTRY` member
- **THEN** the adapter rejects with a stable validation code and Traditional Chinese message, the roller is never invoked, and no result `data` slot is emitted

#### Scenario: An unselected race falls back only to the rule-layer bound packs
- **WHEN** `creation.roll_name` is submitted with `race` and `subrace` both null (the player never chose a race)
- **THEN** the adapter calls `roll_name_for_race(None, ...)` and the result's `data.display_name` is drawn exclusively from the packs bound in `NAME_PACK_BY_RACE` as configured by the rule layer, never from an unbound pack

#### Scenario: A mismatched subrace pair is rejected before the roller
- **WHEN** `creation.roll_name` is submitted with a `subrace` whose registry `race_key` differs from the submitted `race`, a `subrace` absent from `SUBRACE_REGISTRY`, or a non-null `subrace` beside a null `race`
- **THEN** the adapter rejects with a stable validation code, the roller is never invoked, and no result `data` slot is emitted

#### Scenario: An invalid roll-name sex is rejected before the roller
- **WHEN** `creation.roll_name` is submitted with a `sex` string outside `SEX_VALUES`, or with any field exceeding the structural identifier bound, or with an extra field
- **THEN** exact payload validation rejects with a stable code and Traditional Chinese message, the roller is never invoked, and no result `data` slot is emitted

#### Scenario: An abnormal puppet cannot reach a write path
- **WHEN** an adapter is dispatched with a puppet that has no accessible owning account, is not a `PlayerCharacter`, or is not in `account.characters`
- **THEN** the adapter rejects with a stable ownership/creation reason before any deterministic write and no draft, trait, or identity value changes

#### Scenario: An unknown field cannot sneak past activation
- **WHEN** a client submits any creation action carrying an actor, account, session, skills, equipment, starting-magic, or calculated-stat field
- **THEN** exact-schema validation rejects the request without invoking the adapter or the deterministic service

#### Scenario: A skipped or incomplete draft cannot activate
- **WHEN** `creation.activate` is submitted while no valid draft exists or the draft stage is incomplete
- **THEN** the adapter rejects before `activate_player_character`, the character remains pending, and no trait or identity is written

#### Scenario: An over-bound affinity set on an elf is rejected
- **WHEN** a client submits `creation.custom` with a synthetic race permitting no player-selected affinity and a non-empty `affinity_elements`
- **THEN** the deterministic service rejects the request before persistence and no draft or identity value changes

#### Scenario: The preset payload accepts exactly a registry key
- **WHEN** `creation.preset` validates its payload
- **THEN** it accepts exactly `preset_key`, a 1..64-character non-empty string that exists in the
  player-preset registry

#### Scenario: The custom payload carries the exact required fields
- **WHEN** `creation.custom` validates its payload
- **THEN** it accepts exactly `display_name` (1..64 characters), `age` and `apparent_age`
  (integers in 0..10000 excluding booleans; the deterministic creation service independently
  enforces the 0..10000 age range on every submission), `race` (a 1..64-character registry key),
  `subrace` (a 1..64-character registry key belonging to the race; the deterministic service
  rejects a missing or incompatible subrace), `allocations` (an object whose exact keys match
  `ALLOCATABLE_AXES`, each an integer in 0..10000 excluding booleans), and the required nullable
  `background`, `affinity_elements`, and `persona` keys; only `sex` is optional

#### Scenario: The custom optional fields carry their exact bounds and defaults
- **WHEN** `creation.custom` validates its required nullable fields and optional sex
- **THEN** `affinity_elements` is null or an array of at most the schema-bound number of lowercase element keys, each a registered element (the deterministic creation service enforces each race's declared maximum), `background` is null or a string of at most the declared persona-field
  bound (blank normalizes to null), and `sex` is null or a `SEX_VALUES`
  member (a missing value is treated as `DEFAULT_SEX` by the deterministic service)
- **AND** the required `persona` is null or an object containing exactly `personality`,
  `life_story`, and `habit`, each a non-empty string of at most the declared persona-field bound
  (the browser convention ships null when all three fields are empty)

#### Scenario: The concept payload runs the guarded generative layer
- **WHEN** `creation.concept` validates and runs
- **THEN** it accepts exactly `concept` (a non-empty string of at most the declared bound) and
  runs the guarded `character_creation` generative layer with the injected client, storing a
  validated proposal only in the session-scoped transient slot with zero persistent writes

#### Scenario: The roll-name payload accepts exactly registry-bound values
- **WHEN** `creation.roll_name` validates its payload
- **THEN** it accepts exactly `race` (null or a `RACE_REGISTRY` key), `subrace` (null, or a
  `SUBRACE_REGISTRY` key whose registry `race_key` equals the submitted race; a null `race`
  requires a null `subrace`), and `sex` (null or a `SEX_VALUES` member)
- **AND** every value outside those registries is rejected with a stable validation code through
  the existing validation-error channel before the roller runs — the roller's bound-pack random
  fallback serves only a genuinely unselected race (`race: null`) and NEVER turns a dirty key
  into a success

#### Scenario: The roller draws from one private unseeded source with zero writes
- **WHEN** a roll-name payload is admitted
- **THEN** the name is drawn through `roll_name_for_race` using the adapter module's single
  private unseeded `random.Random()` instance (read only on the roll-name path), zero persistent
  writes are performed and no panel is refreshed, and the rolled name is returned as
  `display_name` inside the result envelope's conditional `data` slot

#### Scenario: Activate and reset accept empty payloads only
- **WHEN** `creation.activate` or `creation.reset` validates its payload
- **THEN** each accepts exactly an empty payload

#### Scenario: Adapters derive authority from the session puppet
- **WHEN** any creation adapter runs
- **THEN** it obtains the account from the authenticated session's puppet and rejects any
  actor/account/session/puppet/calculated-stat/unknown field

#### Scenario: Adapters validate through the deterministic service
- **WHEN** any creation adapter processes an admitted payload
- **THEN** it validates through the existing deterministic creation service
  (`preflight_character_creation`, `activate_player_character`, the creation-wizard draft
  service, or `request_draft_portrait`); `creation.roll_name` uses its read-only roller and
  `creation.concept` uses the guarded transient generative layer followed by proposal validation

### Requirement: Creation actions reject stale, duplicate, and tampered input without mutation
Every creation action SHALL pass the existing dispatcher's epoch, base revision, in-flight, and request-ID checks before adapter invocation; a `presentation_epoch` or `base_revision` that does not equal the newest values issued for the live session SHALL return the dispatcher's `stale` outcome with a fresh full snapshot and SHALL invoke no adapter.

#### Scenario: Stale revision cannot double-activate
- **WHEN** `creation.activate` is rendered at revision N and submitted with an older `base_revision`
- **THEN** the dispatcher returns outcome `stale`, calls no adapter, and emits a full snapshot without changing the draft or activating

#### Scenario: Duplicate activation executes once
- **WHEN** the same live request ID for `creation.activate` is delivered twice
- **THEN** `activate_player_character` runs once, the character activates once, and the duplicate receives the cached first result

#### Scenario: Unknown preset cannot be selected
- **WHEN** a tampered `preset_key` is submitted for `creation.preset`
- **THEN** the adapter rejects before saving any draft and the character remains pending with its prior draft unchanged

#### Scenario: Already-activated request is rejected
- **WHEN** a creation action is admitted but the character is no longer creation-pending at commit
- **THEN** the adapter rejects with a stable already-complete reason and performs no write

#### Scenario: Duplicate request IDs serve the cache
- **WHEN** a live request ID is seen again while still live
- **THEN** the dispatcher returns its cached result without re-executing

#### Scenario: Tampered values fail revalidation without mutation
- **WHEN** a tampered `preset_key`, `race`, `subrace`, or allocation fails current deterministic
  revalidation
- **THEN** it is rejected with a stable code and Traditional Chinese message, and no draft, trait,
  identity, or `creation_pending` value changes

#### Scenario: A render-to-submit activation cannot open a second activation
- **WHEN** a pending character is already activated between render and submit
- **THEN** the request is rejected as already-complete without opening a second activation

### Requirement: The age-range gate is server-authoritative for both age fields
The creation service SHALL reject missing, malformed, and out-of-range (`age < 0`, `age > 10000`, `apparent_age < 0`, or `apparent_age > 10000`) values through the existing deterministic creation validation on every `creation.custom` submission, independently for each field. A rejected out-of-range request SHALL leave the character pending with no trait or identity written.

#### Scenario: Out-of-range actual age is permanently rejected
- **WHEN** a client sends `age=-1` with an in-range apparent age through `creation.custom`, including when client-side validation is disabled
- **THEN** the deterministic service rejects the request, the character remains pending, and no trait or identity is written

#### Scenario: Out-of-range apparent age is rejected independently
- **WHEN** a client sends `apparent_age=-1` with an in-range actual age through `creation.custom`
- **THEN** the deterministic service rejects the request, the character remains pending, and no trait or identity is written

#### Scenario: Missing age fields cannot activate
- **WHEN** `creation.custom` omits either age field or sends a non-integer, boolean-like, or oversized value
- **THEN** exact-schema validation or the deterministic service rejects before activation and the character remains pending

#### Scenario: The panel advertises the age bounds
- **WHEN** the creation panel renders the age fields
- **THEN** it advertises the 0 minimum and the 10000 maximum to the player

#### Scenario: Client-side tampering cannot unlock an invalid record
- **WHEN** client-side constraints, hidden or removed age fields, altered HTML constraints, or
  direct `creation.activate` calls are used to bypass the gate
- **THEN** none of them permits an out-of-range or malformed record to activate

### Requirement: Activation is all-or-nothing and hands off to exploration
Successful `creation.activate` SHALL remain all-or-nothing for character state: either the pending gate is removed with the full deterministic initialization committed, or the character stays pending with no partial trait, identity, or progression state. After a committed activation the adapter SHALL publish a full `exploration` snapshot so the browser atomically replaces the creation dock.

#### Scenario: Successful activation moves the shell to exploration
- **WHEN** `creation.activate` commits
- **THEN** the full snapshot mode is `exploration`, the creation dock unloads, the character stands in the start room resolved for its subrace, and `creation_pending` is false

#### Scenario: A failed activation transaction leaves the character pending
- **WHEN** a write failure is injected into the activation transaction
- **THEN** the whole activation rolls back, the character remains pending with its prior draft and its original location and `home`, and no partial trait, identity, or progression state is persisted

#### Scenario: The activated character stays home in 虛境
- **WHEN** an activation commits
- **THEN** the character no longer stays in 虛境: its `home` is the start room it was placed
  in, never 虛境

#### Scenario: No affected-panel set can strand the shell in creation mode
- **WHEN** a creation adapter publishes after a successful activation
- **THEN** it publishes no affected-panel set that leaves the shell in creation mode

### Requirement: Web activation confirms the exact draft shown
The system SHALL ensure the `creation.activate` flow activates the draft whose save was confirmed, and SHALL surface a stable error when the stored draft changed between confirmation and activation.

#### Scenario: Activation after successful save activates the saved draft
- **WHEN** the player confirms after a successful custom save
- **THEN** the character is activated from that saved draft and `creation_pending` becomes false

#### Scenario: Save rejection followed by activation is refused
- **WHEN** the player confirms while the last save was rejected and an older draft remains stored
- **THEN** the activation is refused with a stable code and no character is activated

### Requirement: The creation dock is keyboard-first, form-capable, and confirmation-protected
In `creation` mode the action dock SHALL present preset cards and the custom form rather
than exploration or service menus, keyboard-first: Arrow keys SHALL navigate finite lists
and buttons, Tab and Shift+Tab SHALL move focus through text/numeric fields, Enter SHALL
activate the focused control or submit a complete server-declared form, and Escape SHALL
pop exactly one menu level without discarding the saved server wizard draft.

#### Scenario: Custom form completes without typed commands
- **WHEN** a player uses arrows and Tab/Shift+Tab to choose race and subrace, reviews the
  allocation briefing, types name, ages, allocations, and an optional background into the
  fields, picks a sex from the select, confirms, and activates
- **THEN** the flow submits exactly `creation.custom` once with the expected payload
  (including the required subrace, the chosen sex, and any background), then
  `creation.activate` once, and the exploration snapshot follows

#### Scenario: The custom form cannot submit without a subrace
- **WHEN** a player leaves the subrace unselected in the custom form and confirms
- **THEN** the form reports the missing subrace against the subrace field and sends no
  `creation.custom` mutation

#### Scenario: The sex select renders server-declared options only
- **WHEN** the custom form renders with a panel whose `custom.sex` carries the three labelled options
- **THEN** the select below the name field offers exactly those server keys and labels in order with `DEFAULT_SEX` preselected on a fresh form, and no option label is hardcoded in the browser bundle

#### Scenario: The name-roll button dispatches and backfills by request id
- **WHEN** a player clicks the `creation-roll-name` button and a success result carrying that submitted request id arrives with `data.display_name`
- **THEN** exactly one `creation.roll_name` payload `{race, subrace, sex}` was dispatched, the button was disabled while in flight, and the display-name input is backfilled with the rolled name which the player can then edit

#### Scenario: The custom tab stays pinned through in-flight name-roll republishes
- **WHEN** a player pointer-selects the custom tab and clicks `creation-roll-name`, the
  name-roll dispatch is admitted and synchronously publishes the store view, and a
  success result carrying the submitted request id and `data.display_name` commits
- **THEN** the presented tab remains the custom tab for the whole in-flight window,
  including the dispatch publish, result settlement, and dispatch-gate release; the
  display-name input receives the rolled name, the button re-enables, and subsequent
  unchanged-stage republishes do not replace the custom tab with the preset tab

#### Scenario: A failed or foreign roll result never rewrites the name field
- **WHEN** the in-flight roll settles with a non-success outcome or a result whose request id does not match the submitted one
- **THEN** the in-flight state settles, the button re-enables, and the display-name input keeps whatever the player typed

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
- **WHEN** a player types or presses Tab, modifier, or IME-composition keys while the custom form owns focus
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

#### Scenario: An in-flight concept apply shows a prominent waiting state
- **WHEN** a player submits a concept and the generative layer has not yet settled
- **THEN** the concept tab shows a large spinner with an explicit waiting message, the
  concept input and apply button are disabled so no second concept is submitted, and the
  waiting state clears exactly when a fresh proposal is applied or a non-success result
  bearing the submitted request id settles the request

#### Scenario: A synchronously failed dispatch never sticks the waiting state
- **WHEN** a concept dispatch is admitted but its transport send fails synchronously (the
  store releases its mutation gate without ever emitting an action result), or the gate
  releases while no proposal has arrived
- **THEN** the waiting state clears with the concept tab restored to an editable form, and
  an apply rejected by the single-in-flight gate never enters the waiting state at all

#### Scenario: The concept tab stays pinned through in-flight republishes
- **WHEN** a concept apply is in flight and the store commits panel updates or draft
  re-syncs whose stage signal would otherwise mirror onto the presented tab
- **THEN** the presented tab remains the concept tab for the whole in-flight window, and
  the waiting state clears without ever being replaced by the preset tab

#### Scenario: A proposal-only panel refresh never navigates the dock
- **WHEN** a concept apply completes and the store commits a `creation` panel with no draft
  and a `proposal` slot
- **THEN** the creation dock's stage is unchanged (the player is not moved to the preset
  stage), and any tab movement comes solely from the overlay's own completion navigation

#### Scenario: The custom form requires a subrace selection
- **WHEN** the custom form is rendered
- **THEN** a subrace selection is required and no "無子種族" radio is rendered

#### Scenario: The custom form fields beyond the keyboard map
- **WHEN** the custom form renders
- **THEN** it displays an allocation briefing (total budget, seven-axis count, each axis's
  0–span, and the sum-must-equal-budget rule) above the allocation fields
- **AND** it provides a bounded optional background text field
- **AND** it renders a sex `<select>` directly below the display-name field whose options come
  verbatim from `custom.sex` (no browser-side label literals, the `DEFAULT_SEX` key preselected
  for a fresh form)
- **AND** it renders a name-roll button carrying test id `creation-roll-name` adjacent to the
  display-name input

#### Scenario: The name-roll button gates in flight and backfills by request id
- **WHEN** a name roll is in flight
- **THEN** the button is disabled through the shared dispatch gate
- **AND** a settled success result carrying the submitted request id backfills the display-name
  input with `data.display_name` — the player may then freely edit it and the final value is
  validated only by `creation.custom`
- **AND** a non-success or non-matching result settles the in-flight state without touching the
  input

#### Scenario: Form action buttons work by pointer and pre-empt the keyboard bridge
- **WHEN** the form action buttons (confirm, reset, cancel, and concept-apply) are presented
- **THEN** they are operable by pointer through the shared focus/disabled/submission gate as
  well as by keyboard
- **AND** they pre-empt the keyboard bridge (a capture-phase listener) while the form owns
  focus, so keys the form owns are claimed by the form and none reach the bridge's fall-through
  text path
- **AND** the capture listener is removed when the form closes

#### Scenario: An in-flight concept apply presents the prominent waiting state
- **WHEN** a concept apply is in flight
- **THEN** the concept tab presents a prominent in-progress state — a visible large spinner
  with an explicit waiting message — and disables the concept input and the concept-apply
  button until a fresh proposal revision is applied, a result carrying the submitted request id
  with a non-success outcome settles the request, or the global dispatch gate releases without a
  matching settlement (the safety net for a synchronous transport failure or a lost mutation)
- **AND** the in-progress state is only ever entered after the dispatch was admitted, so a
  gate-rejected apply never shows it

#### Scenario: The presented tab is pinned through the form's own in-flight request
- **WHEN** a creation form's own admitted request is in its in-flight loading state (concept
  apply or name roll)
- **THEN** no store publish or draft re-sync moves the presented tab — the tab is pinned while
  that loading state is alive

#### Scenario: A settled apply has no completion affordance beyond the custom-tab switch
- **WHEN** a concept apply settles successfully
- **THEN** the browser presents no other completion affordance beyond the custom-tab switch —
  the confirmation toast is surfaced through the action-feedback queue by the form's apply path,
  and the failure toast by the action-feedback result slice, not by any form-embedded banner

#### Scenario: Activation and reset require explicit confirmation panels
- **WHEN** the player triggers the final activation or the destructive custom reset
- **THEN** each requires an explicit confirmation panel

#### Scenario: Accessibility of disabled entries and validation messages
- **WHEN** the dock renders a disabled entry or a field error
- **THEN** disabled entries remain focusable with their explanation and submit nothing, and
  validation messages are associated with the field they concern and announced through the
  accessible live region

#### Scenario: A stale revision preserves typed values without resubmitting
- **WHEN** the dock observes a stale revision
- **THEN** typed unsent values are preserved locally where safe, server-declared choices are
  refreshed, and the player is asked to review rather than the form being automatically resubmitted

#### Scenario: The panel signature ignores proposals for stage navigation
- **WHEN** a committed `creation` panel carries no draft and only a transient proposal
- **THEN** it does not reset the creation dock's stage — the panel signature covers presets,
  races, and the draft only, so a proposal delivery alone never navigates the player

#### Scenario: No creation state lives in localStorage
- **WHEN** the creation surface runs in the browser
- **THEN** no canonical service or creation state is stored in localStorage

### Requirement: Creation browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise the creation journey using keyboard
controls only. Tests SHALL use deterministic fixtures and SHALL make no remote, LLM, or
image-generation request. Test waits SHALL gate on deterministic state — polling the committed
store view and the creation-surface DOM with a bounded deadline — rather than on the raw
`#action-dock` element becoming visible, so the suite stays stable under a loaded CI runner.

#### Scenario: Preset journey completes in Chromium
- **WHEN** a seeded pending character uses arrows and Enter to open a preset card, confirms, and activates
- **THEN** the flow submits `creation.preset` then `creation.activate` once each and the refreshed snapshot shows exploration mode with the creation dock removed

#### Scenario: Underage custom journey is rejected end to end
- **WHEN** a browser fills the custom form with `age=17` after disabling the client-side minimum
- **THEN** the server rejects, the character stays pending, and the error is announced without leaving the creation dock

#### Scenario: Reconnect restores the saved stage in Chromium
- **WHEN** the transport disconnects after a validated `creation.custom` save and reconnects
- **THEN** the new-epoch snapshot rebuilds the form at the `custom_filled` stage and no automatic activation is sent

#### Scenario: Minimum viewport retains creation essentials
- **WHEN** the creation dock renders at the 1451x790 reference viewport with a focused disabled control
- **THEN** the player can read the preset cards, the form fields, the disabled explanation, and the confirmation controls without overlap preventing operation

#### Scenario: Creation dock is the sole owner in creation mode and re-renders in exploration
- **WHEN** the browser is in creation mode with the `creation` panel available
- **THEN** exactly one `#action-dock` element is rendered with `data-mode="creation"` (the creation dock is its sole owner), and after activation hands off to exploration no creation-mode dock remains: the shared dock re-renders as `data-mode="exploration"` when `context_actions` is available, so the shared DOM node may persist rather than being fully removed

#### Scenario: The dock panel is the persistent node across a mode change
- **WHEN** the browser hands off from creation mode to exploration mode after activation
- **THEN** the same single `#action-dock` panel element persists with its `data-mode` switched from `creation` to `exploration`, and it is not removed and re-created

#### Scenario: Creation mode renders no root command list and no breadcrumb
- **WHEN** the dock is rendered in creation mode
- **THEN** it renders the creation surface with no root command list, no count, and no breadcrumb line, and the creation form keeps its own key capture exactly as before

#### Scenario: The suite covers the full journey at both viewports
- **WHEN** the acceptance suite runs at 1451x790 and 2560x1440
- **THEN** it exercises preset selection, confirmation, activation, and the exploration
  snapshot; custom finite controls and free-text field focus; reconnect at each saved draft
  stage; server rejection of both out-of-range age fields despite bypassed client validation;
  the destructive reset confirmation; and stale and duplicate submission behavior

#### Scenario: The suite asserts dock ownership and no import fields
- **WHEN** the acceptance suite asserts on the creation surface
- **THEN** it asserts the creation dock is the sole action-dock owner in creation mode and
  re-renders on exploration (the shared `#action-dock` node may persist with `data-mode`
  switching), and asserts no persona/import field is rendered

#### Scenario: The shared dock panel keeps its chrome across a mode change
- **WHEN** the dock renders in creation mode on the persistent shared `#action-dock` node
- **THEN** the floating dock panel itself is never remounted at a mode change; the node renders
  neither the tab bar's tabs nor the breadcrumb — the creation surface is a modal form rather
  than a router frame — while keeping its own chrome, its `data-mode="creation"` attribute, and
  its role as the surface's documented focus target

### Requirement: Creation race display names travel with opaque keys
Each custom.races option SHALL contain exactly key, display_name_zh, description and subraces, with display_name_zh a non-empty string of at most 128 code points sourced from the race registry. Every preset race key SHALL resolve to one such option. Clients SHALL render that display name in race controls, presets and confirmation while preserving keys in actions.

#### Scenario: Preset and custom agree
- **WHEN** a preset and a custom option use the same race key
- **THEN** both show the supplied registry display name and selection still submits only the original key

#### Scenario: Invalid label is rejected
- **WHEN** a race label is absent/blank/overlong or a preset names an absent race option
- **THEN** both exact validators reject the panel and no raw-key fallback is invented

### Requirement: Creation resource and offense labels are distinguishable
Creation allocation and preview prose SHALL distinguish the mana resource axis from magic offense using canonical localized labels, while preserving all allocation keys, bounds and totals.

#### Scenario: Both axes are present
- **WHEN** a creation profile carries mana and magic offense
- **THEN** their labels are distinguishable and changing either control updates only its existing axis

### Requirement: Preset cards carry a server-built artwork descriptor
Every preset card's `artwork` SHALL be one canonical artwork descriptor built by the server from the card's own preset key. It SHALL offer the preset's official default image as its only image attempt when the mounted catalog admits one, and SHALL always carry the built-in alpha terminal. Building it SHALL create no character, gallery record, job or stored file.

#### Scenario: A preset with official artwork offers it
- **WHEN** the panel is built while the mounted catalog admits a default image for a synthetic preset's content reference
- **THEN** that card's descriptor carries exactly one image attempt whose resource origin is `official` and whose URL is the catalog's fingerprinted same-origin URL, plus an alpha terminal

#### Scenario: A preset without official artwork resolves the built-in figure
- **WHEN** the panel is built while the catalog holds nothing for a synthetic preset
- **THEN** that card's descriptor carries no image attempt and no fault, and its terminal is the built-in figure named by the preset's declared fallback key, or by the band rule on the preset's declared sex and apparent age when it declares none

#### Scenario: A preset descriptor claims no generation
- **WHEN** any preset card's descriptor is inspected
- **THEN** its `generation_subject` and `generation_state` are null and its `retention_sources` list is empty

#### Scenario: Building preset artwork writes nothing
- **WHEN** the panel is built for a pending character
- **THEN** the gallery record count, the gallery job count, the character's `portrait_policy` and the art store's file set are unchanged

#### Scenario: A malformed preset descriptor rejects the panel
- **WHEN** a preset card omits `artwork`, carries a null, or carries a descriptor whose resource URL does not name the same-origin art route
- **THEN** both the presenter validator and the mirrored browser validator reject the panel

### Requirement: The custom descriptor carries the silhouette table
`custom.silhouettes` SHALL be a list of 1..16 entries, each with exactly `sex`, `apparent_age_minimum`, `apparent_age_maximum` and `artwork`. For every advertised sex the entries SHALL cover the advertised apparent-age range exactly once, with no gap and no overlap. Each `artwork` SHALL be a canonical descriptor carrying no image attempt and the alpha terminal the built-in band rule resolves for that sex and age range.

#### Scenario: Every sex covers the whole apparent-age range
- **WHEN** the silhouette table ships
- **THEN** for each `custom.sex` key the entries naming it, ordered by `apparent_age_minimum`, start at `custom.age.apparent_age_minimum`, end at `custom.age.apparent_age_maximum`, and each entry starts one above the previous entry's maximum

#### Scenario: An entry resolves the band rule's figure
- **WHEN** a pending character whose sex and apparent age fall inside one entry is later resolved by the built-in fallback resolver with no declared key
- **THEN** the resolver's key equals the key of that entry's alpha terminal

#### Scenario: A silhouette entry offers no image attempt
- **WHEN** any silhouette entry's descriptor is inspected
- **THEN** its `attempts` list is empty, its `generation_subject` and `generation_state` are null, and its terminal kind is the alpha mask

#### Scenario: A malformed table rejects the panel
- **WHEN** the table is empty, exceeds 16 entries, names a sex outside `custom.sex`, leaves a gap or an overlap for a sex, or carries a malformed descriptor
- **THEN** both the presenter validator and the mirrored browser validator reject the panel

### Requirement: Preset browsing is local until deliberate selection
The preset wall SHALL keep expanded-card state separate from the saved draft. Pointer opening, horizontal arrows and digit shortcuts SHALL only expand a supplied card. The expanded card’s primary action or Enter SHALL run the existing preset-save and explicit activation-confirmation flow once, subject to dispatch admission.

#### Scenario: Opening sends nothing
- **WHEN** a player opens another supplied card by pointer, a horizontal arrow or its displayed ordinal digit
- **THEN** the card expands locally, no action or narrative mutation echo is sent, and the server draft is unchanged

#### Scenario: Deliberate selection preserves confirmation
- **WHEN** the player activates the expanded card’s primary action or presses Enter in its wall context
- **THEN** exactly one preset save names that card’s key, confirmation opens only after its matching successful save, and activation waits for explicit confirmation

#### Scenario: Entry restores a valid expansion
- **WHEN** preset mode opens or its supplied cards change
- **THEN** a surviving saved preset key is expanded on entry, otherwise the first supplied card is expanded; a surviving local browse selection is kept during equal-content republication

#### Scenario: Unavailable ordinal is inert
- **WHEN** a shortcut names no supplied card, an input or drawer owns the key, or the event is composing, modified or repeated
- **THEN** no wall selection or action occurs and native text entry remains intact

#### Scenario: Accessible opening and motion
- **WHEN** a keyboard user browses cards or changes motion preference
- **THEN** collapsed cards are named native buttons, the expanded card exposes aria-current and visible focus, and reduced/off motion switches without interpolating the card transition

### Requirement: Pending characters request portraits from exact draft values
`creation.portrait.generate` SHALL accept exactly `race`, `subrace`, `sex`, `apparent_age` and `custom_prompt` for the authenticated account's pending character. Invalid input, in-flight work or known service unavailability SHALL reject before policy, receipt or queue writes. Admission SHALL preserve canonical identity, draft, proposal and activation confirmation while requesting one image on that character's named subject.

#### Scenario: A valid draft request needs no saved form
- **WHEN** an owned pending character submits registered compatible race/subrace, a race-permitted sex, integer apparent age in 0..10000 excluding booleans and an accepted prompt with a successful server connectivity verdict
- **THEN** one fresh image job is enqueued on `portrait:character:<character pk>`, with no canonical identity, trait, wizard-draft or concept-proposal write and no activation

#### Scenario: Admission serializes receipt discovery through commit
- **WHEN** a draft request contends with settlement of its preceding image
- **THEN** queue serialization precedes database writes and covers receipt/card discovery through policy/job/receipt commit; admission either rejects the in-flight request or retains the committed preceding card, and callbacks that reacquire locks run only after release

#### Scenario: Known-unavailable service refuses retryably before mutation
- **WHEN** an otherwise valid creation portrait request receives a failed server connectivity verdict, even if the browser's displayed state was stale or bypassed
- **THEN** it returns `portrait_service_unavailable` and publishes the safe unavailable reason without a policy, portrait receipt/state, draft, confirmation or queue write; existing art survives, and a later valid successful verdict permits explicit retry

#### Scenario: Offline portrait does not block creation or play
- **WHEN** art and LLM services are unavailable
- **THEN** preset and custom creation, activation and deterministic gameplay remain available; no connectivity gate is added to gallery, ensure/autogen, queue or worker paths

#### Scenario: Exact payload rejects before mutation
- **WHEN** any required key is missing, an extra field names a subject, actor, age, binding, fields or calculated stat, a key is blank/overlong/unknown, subrace is incompatible, sex is forbidden, or apparent age is malformed/out of range
- **THEN** the request is rejected with a stable reason and no policy, receipt, gallery job, card or file changes

#### Scenario: Free text uses the gallery contract
- **WHEN** the prompt is empty, whitespace-only, over its declared bound, non-text or control-bearing
- **THEN** empty and whitespace-only normalize to the legal no-op; the other values reject through the same gallery prompt validator before any render or write

#### Scenario: The subject cannot be changed by a caller
- **WHEN** an unowned, non-player or no-longer-pending character requests a draft portrait, or two sessions request one while its subject has an in-flight job
- **THEN** ownership/pending or in-flight validation rejects and no second job or replacement policy is written

#### Scenario: Portrait requests do not authorize activation
- **WHEN** a portrait request succeeds or rejects while a saved-draft confirmation exists
- **THEN** its fingerprint and the saved draft are unchanged, and the existing activation gate remains authoritative

### Requirement: Custom step navigation preserves unsent form authority
The custom form SHALL keep its current step locally, preserve unsent field values across step changes, and display the descriptor-derived remaining allocation points on the step rail. Existing validation SHALL route focus to the first invalid field’s step without introducing new creation rules.

#### Scenario: Free navigation keeps values
- **WHEN** a player moves directly between nonadjacent steps or uses the previous/next controls
- **THEN** unsent values survive, no server action is sent, and the footer confirmation remains usable on every step

#### Scenario: Validation reveals the first invalid field
- **WHEN** existing native or custom submission validation identifies invalid fields
- **THEN** the step containing the first invalid field in identity/story/allocation display order opens, receives focus at that field, and the step has a non-color error indicator and associated message

#### Scenario: Remaining points are presentation arithmetic
- **WHEN** allocations or the selected server profile change while any step is open
- **THEN** the rail displays the profile budget minus the entered allocation sum without clamping invalid input or authorizing submission

#### Scenario: Empty portrait follows the table
- **WHEN** sex or apparent age changes before live portrait integration
- **THEN** the persistent slot selects the matching server silhouette interval, shows the current name or an unnamed label, and offers no generation control

### Requirement: Concept guide completion follows proposal fields
The concept guide SHALL derive completion indicators from present values in the current proposal contract, excluding sex and portrait. A fresh concept apply SHALL return the custom form to its identity step without submitting the form or copying concept text into a portrait prompt.

#### Scenario: A partial proposal marks only supplied values
- **WHEN** a synthetic proposal omits some optional fill fields
- **THEN** guide indicators distinguish present values from absent ones and claim neither sex nor portrait completion

#### Scenario: Existing proposal does not navigate on rebuild
- **WHEN** a rebuild or remount re-renders an unchanged proposal revision
- **THEN** existing revision-gated fill behavior remains and there is no new navigation, submission or success toast
