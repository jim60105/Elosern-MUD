## Why

A preset-created character owns no persona record at all. In
`activate_player_character`, the persona builder has exactly two branches — a
supplied custom persona block, or a non-null `validated.background` — and
`preflight_character_creation` hard-writes `background = None` for preset mode,
so neither branch fires and `character.attributes.add("persona", ...)` never
runs.

The consequence is visible in play: `world/ai/npc_dialogue.py`'s
`PLAYER_PERSONA_FIELDS` (`identity`, `appearance`, `social_connection`) resolves
to nothing for a preset character, so NPCs converse with a blank slate. A
hand-built custom character is richer in AI narrative than a shipped signature
character — the opposite of the intent.

`preset-persona-model` gave the registry a validated persona. This change makes
activation persist it.

## What Changes

- The two persona branches in `activate_player_character` are unified into one
  helper, `_persona_record_for(...)`, which returns the record to write or
  `None`. Custom-mode output is byte-identical to today's.
- Preset mode returns `preset.persona.to_record()`, so a preset activation
  persists the registry's persona inside the same all-or-nothing transaction
  that writes identity, traits, skills, and inventory.
- The persona write stays inside that transaction, so a failure rolls the whole
  activation back — the existing custom-path guarantee now covers preset mode
  too.
- `persona` is already in `_CREATION_ATTRIBUTE_KEYS`, so the snapshot/restore
  path needs no widening.

No backward compatibility or data migration: the project has no released users.
Existing preset characters, if any exist in a developer database, simply have no
persona; nothing reads a version marker.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-character-creation`: a new requirement that preset activation persists
  the preset's declared persona record.
- `creation-persona-persistence`: the activation requirement widens from
  "custom drafts only" to both creation modes, with one shared record builder.

## Impact

- `world/rules/character_creation.py` — the persona branch of
  `activate_player_character` and a new `_persona_record_for` helper. No other
  activation write changes.
- `world/rules/tests/test_character_creation.py` — preset persona persistence,
  shape equality with the custom path, and rollback on an injected persona-write
  failure.
- Unaffected: the custom path's observable output, `world/rules/persona_edit.py`
  (which still creates a record when none exists), the import loader, and every
  WebClient payload schema.
