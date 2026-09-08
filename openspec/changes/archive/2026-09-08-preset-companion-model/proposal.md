## Why

Some signature characters are written as a pair. `yuna_darknight` and
`yuka_darknight` are twin sisters who left 暗影谷村 together — 悠奈's own
background prose says so — but the registry can only ship them as two
alternatives. A player who picks one starts alone, and the other exists only as
a card they did not choose.

The game already has every mechanism the pairing needs: `world/rules/party.py`
binds companions, `world/rules/affinity.py` holds the relationship, `LLMNPC`
carries the conversation, and `PlayerPreset` now carries a full character sheet.
What is missing is a way for a preset to say "this character does not arrive
alone", and a builder that turns the partner's own card into a live NPC.

This change ships the declaration and the builder. The change that binds the
companion into the party at activation follows separately.

## What Changes

- New frozen `StartingCompanion` dataclass in `world/lore/player_presets.py`:
  `preset_key` (the companion's own preset), `affinity` (the seeded value), and
  `relationship` (the persona `social_connection` label).
- `PlayerPreset` gains a keyword-only `starting_companions` tuple, defaulting to
  empty.
- `yuna_darknight` and `yuka_darknight` declare each other symmetrically at
  affinity **95** — well above the `invite_threshold` of 70, inside the 至愛
  stage, with headroom so a single friendly-fire point cannot drop a stage.
- Lore-side load validation rejects an unknown `preset_key`, a self-reference,
  or the same partner declared twice. Because `world/lore/` must not import
  `world/rules/`, the bounds that derive from rules constants —
  `len(starting_companions) <= PARTY_MAX_COMPANIONS` and
  `1 <= affinity <= NATURAL_CAP` — are swept at `world/rules/` import time
  instead, the same split `preset-persona-model` established for the persona
  prose cap.
- New module `world/rules/starting_companions.py` with a builder that turns one
  declaration into a live, fully-configured `LLMNPC` mirroring the attribute set
  `world/imports/loader.py::_instantiate_validated_character` writes. It does
  **not** seed affinity or bind the party; that is the next change.
- `LLMNPC`, not plain `NPC`, because `commands/invite.py` accepts only an
  `LLMNPC` — a companion the player dismisses must be re-invitable.
- The builder derives its trait values from `resolve_preset_values(preset)`,
  the shared pure helper `preset-value-resolver` extracts, so the companion and
  the player version of the same card cannot drift. That extraction is a
  prerequisite change, not part of this one.
- The companion is deliberately **untitled**. `npc_title` is an authored
  identity every other production NPC-creation path supplies from its own
  registry (roster rows, examiner ranks, import records), and neither
  `PlayerPreset` nor `StartingCompanion` carries a title source. A starting
  companion is a player's twin, not a service host, so it degrades to the plain
  name through the title capability's own fallback. Adding a title source is a
  separate decision, matching the parent design's exclusion of `title` from
  preset field parity.
- A name already held by another entity takes a `-{pk}` suffix, following
  `world/rules/guild_exams.py::_key_taken_by_other`.

No backward compatibility or data migration: the project has no released users.

Interim boot note: nothing in the runtime import graph pulls
`world/rules/starting_companions.py` until `preset-companion-activation` wires
the builder into activation, so within this change the rules-side bounds sweep
runs wherever the module is imported (its tests) rather than at server boot;
the delta scenario pins the sweep to this module's import deliberately.

## Capabilities

### New Capabilities

- `starting-companions`: a preset may declare NPC companions built from their
  own preset cards — the declaration model, its load-time validation, and the
  deterministic builder.

### Modified Capabilities

None. The activation binding and the party join are introduced by
`preset-companion-activation`; the affinity seed writer by
`affinity-seed-writer`.

Prerequisite changes: `preset-persona-model` (the companion persona comes from
`PresetPersona`), `preset-sex-field`, and `preset-value-resolver` (the shared
trait computation).

## Impact

- `world/lore/player_presets.py` — `StartingCompanion`, the
  `starting_companions` field, its lore-side validator, and the two twin cards.
- `world/rules/character_creation.py` — untouched by this change; the companion
  bounds sweep lives in the new module. `resolve_preset_values()` is consumed
  read-only and comes from `preset-value-resolver`.
- `world/rules/starting_companions.py` — new module holding the builder.
- `world/rules/equipment.py`, `world/rules/progression.py`,
  `world/art/service.py`, `typeclasses/npcs.py` — read-only reuse.
- `world/lore/tests/test_player_presets.py`, and a new
  `world/rules/tests/test_starting_companions.py` that MUST be registered in
  exactly one shard of `.github/evennia-shards.json` in this same change.
- Unaffected until the next change: activation, party membership, affinity, and
  every player-facing surface.
