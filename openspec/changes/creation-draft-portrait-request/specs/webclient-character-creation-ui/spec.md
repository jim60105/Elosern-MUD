# Spec Delta

## MODIFIED Requirements

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
  rejects a missing or incompatible subrace), and `allocations` (an object containing exactly
  `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense`, each an integer in 0..10000 excluding
  booleans)

#### Scenario: The custom optional fields carry their exact bounds and defaults
- **WHEN** `creation.custom` validates its optional fields
- **THEN** `affinity_elements` is an array of at most the schema-bound number of lowercase element keys, each a registered element (the deterministic creation service enforces each race’s declared maximum), `background` is a string of at most the declared persona-field
  bound (a missing value is treated as an empty background), and `sex` is null or a `SEX_VALUES`
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
  (`preflight_character_creation`, `activate_player_character`, and the creation-wizard draft
  service) except the read-only `creation.roll_name` roller call

## ADDED Requirements

### Requirement: Pending characters request portraits from exact draft values
`creation.portrait.generate` SHALL accept exactly `race`, `subrace`, `sex`, `apparent_age` and `custom_prompt` for the authenticated account’s pending character. Invalid identity, prompt or in-flight state SHALL reject before policy or queue writes. An admitted request SHALL preserve canonical identity, draft, proposal and activation confirmation while requesting one image on that character’s named subject.

#### Scenario: A valid draft request needs no saved form
- **WHEN** an owned pending character submits registered compatible race/subrace, a race-permitted sex, integer apparent age in 0..10000 excluding booleans and an accepted prompt
- **THEN** one fresh image job is enqueued on `portrait:character:<character pk>`, with no canonical identity, trait, wizard-draft or concept-proposal write and no activation

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
