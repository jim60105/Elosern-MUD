## Why

`PlayerPreset` carries a single free-text `background` field and nothing else
resembling a persona. The persona system that landed later defines a much
richer character sheet — `identity` (with a public and a hidden layer),
`personality`, `life_story`, `habit`, `appearance` (seven sub-keys), and
`social_connection` — and `world/rules/persona.py` already declares those exact
shapes in `_SUBKEY_ORDER` and `_SUBKEY_LABELS`. The eight shipped signature
characters can express one seventh of what a hand-authored import card can.

Worse, the preset's `background` prose never reaches the character at all: it is
consumed only as selection-card display text by `creation_wizard.build_preset_cards()`
and discarded at activation. This change gives the registry somewhere to put a
real persona; the change that makes activation persist it follows separately.

## What Changes

- New frozen dataclasses in `world/lore/player_presets.py`: `PresetIdentity`
  (public/hidden), `PresetAppearance` (the seven `_SUBKEY_ORDER` sub-keys), and
  `PresetPersona` (the seven persona keys) with a `to_record()` method producing
  the storage shape `PersonaStore` reads.
- `PlayerPreset` gains a keyword-only `persona: PresetPersona` field.
- **BREAKING (internal)**: `PlayerPreset.background` is removed; its content
  moves into `persona.background`, so the registry has one source for that prose
  instead of two. Both current readers move with it:
  `creation_wizard.build_preset_cards()` (the WebClient preset cards) and
  `commands/character_creation.py::creation_start_screen()` (the Telnet
  no-arg `character` screen, reused by `Account.at_post_login`), which reads
  `preset.background` directly today. `PresetCardView` and every downstream wire
  shape are unchanged.
- Removing the positional `background` slot shifts the trailing positional
  arguments, so the eight cards convert `active_skills`, `passive_skills`, and
  `affinity_elements` to keyword arguments.
- A load-time validator rejects a malformed persona: wrong types, or a
  `social_connection` entry that is not a name/relationship string pair. Empty
  values are always legal so a card can be authored incrementally.
- The persona prose cap (`MAX_PERSONA_FIELD_LENGTH`, 600) is enforced by a
  load-time sweep in `world/rules/character_creation.py` — the module that owns
  the constant — because `world/lore/` must not import `world/rules/`.
- A repo-wide contract test pins `persona.background` for every shipped preset
  at or under `MAX_BACKGROUND_CODE_POINTS` (256), the bound the WebClient preset
  card descriptor already declares. Without it, an author using the full 600-code-point
  persona budget would silently overflow the creation panel's card contract.
- `to_record()` omits empty strings and empty containers, so a minimally
  authored card still yields a valid import-card-shaped record.

Activation still writes no persona for a preset; that is `preset-persona-activation`.
This change ships the validated data model and the card-source switch only —
a deliberate forward-declared seam, not a fake implementation.

No backward compatibility or data migration: the project has no released users.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-character-creation`: a new requirement making the preset registry
  declare a full persona in import-card shape, validated at load, with the
  card-blurb bound pinned against the WebClient descriptor.

`character-creation-ux` needs **no** delta: its "presents preset previews"
requirement says the background one-liner is "derived from immutable registry
data (the player-preset catalog and the race registry)", which is field-name
agnostic and stays true after the move. Only the reading code changes.

## Impact

- `world/lore/player_presets.py` — three new dataclasses, the `persona` field,
  removal of `background`, a new validator, eight card literals.
- `world/rules/character_creation.py` — a load-time persona-prose-cap sweep over
  `PLAYER_PRESET_REGISTRY`. No activation behavior changes.
- `world/rules/creation_wizard.py` — `build_preset_cards()` reads
  `preset.persona.background`.
- `commands/character_creation.py` — `creation_start_screen()` reads
  `preset.persona.background`. Missing this would raise `AttributeError` on the
  first screen every pending player sees.
- `world/lore/tests/test_player_presets.py`,
  `world/rules/tests/test_creation_wizard.py`,
  `world/rules/tests/test_persona.py`,
  `commands/tests/test_character_creation.py` (two existing assertions on
  `preset.background`), and a new contract test in
  `tests/test_creation_parity_contract.py`.
- Unaffected wire contracts: `PresetCardView`'s field set, the creation panel
  payload, `creation.preset`, custom creation, and the import path.
