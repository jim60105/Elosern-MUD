# player-character-creation delta

## ADDED Requirements

### Requirement: The preset registry declares a full persona in import-card shape
Every `PlayerPreset` SHALL declare a keyword-only `persona` field holding a
frozen `PresetPersona` whose shape mirrors the persona record
`world/rules/persona.py` renders: `identity` (a `PresetIdentity` with `public`
and `hidden` layers), `personality`, `life_story`, `habit`, `appearance` (a
`PresetAppearance` carrying exactly the seven `_SUBKEY_ORDER` sub-keys
`height`, `weight`, `measurement`, `style`, `overview`, `attire`, `feature`),
`social_connection` (a tuple of name/relationship string pairs), and
`background`. `PlayerPreset` SHALL NOT carry a separate top-level `background`
field: the registry SHALL hold that prose exactly once, inside the persona.

`PresetPersona.to_record()` SHALL return the storage shape written to
`entity.db.persona`, matching the record shape custom activation and
`world/rules/persona_edit.py` already produce: all six `PERSONA_IMPORT_CARD_KEYS`
(`identity`, `personality`, `life_story`, `habit`, `appearance`,
`social_connection`) SHALL always be present, unauthored prose keys holding `""`
and unauthored structured keys holding `{}`; `identity.hidden` SHALL be omitted
when empty; and `background` SHALL be included only when non-empty, exactly as a
custom draft without a background omits the key. Every persona value SHALL be
optional and default to empty, so a card can be authored incrementally without a
code change, and a minimally authored card still produces a record
`PersonaStore.flatten()` and `PersonaStore.public_view()` read without error.

A preset whose persona is structurally malformed — a non-string prose value, a
non-`PresetIdentity` identity, a non-`PresetAppearance` appearance, or a
`social_connection` entry that is not a pair of strings — SHALL fail at registry
load, never at player activation, matching the existing skill-kit, identity,
affinity, and starting-item validators. Duplicate `social_connection` names
SHALL be rejected the same way, because the stored name/relationship mapping
would otherwise silently drop the earlier pair.

Because `world/lore/` SHALL NOT import `world/rules/`, the prose length bound
SHALL be enforced by a load-time sweep in `world/rules/character_creation.py`,
the module owning `MAX_PERSONA_FIELD_LENGTH`: every persona prose value of every
registered preset SHALL be at most that bound, and a violation SHALL raise at
import.

The selection-card blurb SHALL be derived from `persona.background`, and
`PresetCardView`'s field set, the creation panel payload, and the
`creation.preset` action payload SHALL be unchanged. Because the WebClient
preset-card descriptor bounds `background` at `MAX_BACKGROUND_CODE_POINTS`
(256) while the persona bound is 600, a repo-wide contract test SHALL pin every
shipped preset's `persona.background` at or under the card bound, so an author
spending the full persona budget cannot silently overflow the card contract.
This one bound is deliberately a contract test rather than a load-time
validator, unlike every other preset constraint: the constant lives in
`web/webclient/presentation/creation.py`, and neither `world/lore/` nor
`world/rules/` may import the web layer to reach it. The test is the only place
the two bounds can be compared without inverting a layering rule.

Activation behavior is unchanged by this requirement: a preset activation still
writes no persona record. The requirement covering that write is introduced
separately.

#### Scenario: A shipped preset carries its background inside the persona
- **WHEN** `PLAYER_PRESET_REGISTRY` is inspected
- **THEN** no entry has a top-level `background` attribute, and every entry's `persona.background` holds the prose that the selection card renders

#### Scenario: to_record produces a PersonaStore-readable record
- **WHEN** `PresetPersona.to_record()` is called on a fully authored persona
- **THEN** the result is a mapping whose `identity` carries `public` and `hidden` sub-keys and whose `appearance` carries the declared sub-keys, and `PersonaStore.flatten()` renders it without raising

#### Scenario: An empty persona still yields the six-key import-card record
- **WHEN** `PresetPersona.to_record()` is called on a persona whose values are all empty
- **THEN** the result carries exactly the six `PERSONA_IMPORT_CARD_KEYS` with empty strings and empty containers, omits `background` and `identity.hidden`, and `PersonaStore.flatten()` over it returns `None` rather than raising

#### Scenario: The public view prunes the hidden identity layer
- **WHEN** a preset persona declaring a non-empty `identity.hidden` is written into a record and read through `PersonaStore.public_view()`
- **THEN** the hidden layer is absent from the public view while `identity.public` survives

#### Scenario: A structurally malformed persona is rejected at load
- **WHEN** a preset declares a non-string persona prose value, a non-`PresetAppearance` appearance, or a `social_connection` entry that is not a pair of strings
- **THEN** importing `world.lore.player_presets` raises, so the malformed persona can never reach a player's activation

#### Scenario: An over-long persona field is rejected at load
- **WHEN** a registered preset declares a persona prose value longer than `MAX_PERSONA_FIELD_LENGTH`
- **THEN** importing `world.rules.character_creation` raises from its registry sweep, naming the offending preset and field

#### Scenario: The card blurb stays inside the WebClient descriptor bound
- **WHEN** the repo-wide creation contract test inspects every shipped preset
- **THEN** each `persona.background` is at most `MAX_BACKGROUND_CODE_POINTS` code points

#### Scenario: The preset card contract is unchanged
- **WHEN** `build_preset_cards()` runs after the background moves into the persona
- **THEN** every `PresetCardView` carries the same field set and the same background text as before the move
