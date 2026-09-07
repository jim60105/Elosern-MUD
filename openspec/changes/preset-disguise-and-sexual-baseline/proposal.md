## Why

Two more import-card fields have no preset counterpart.

`disguised_stats` is the display-only layer that lets a character appear
stronger or weaker than it is — the mechanism `elosia_shadowmoon`'s authored
`status_disguise` mastery exists to use. Activation never writes the attribute,
so a preset character always appears exactly as strong as it is.

`sexual_baseline` seeds the `SexualState` handler. When `entity.db.sexual` is
absent, `SexualState` falls back to `_generic_default_baseline()`, so every
preset character starts sexually identical. For an adult game whose roster
includes `yuna_darknight` — authored as a hedonist who has taken sexual magic
to its limit — a registry with no way to say so is a real expressive gap, and
the import card has had the field since `import-contract`.

## What Changes

- `PlayerPreset` gains a keyword-only `disguised_stats` field, a tuple of
  `(axis_key, value)` pairs, defaulting to empty. Validation requires string
  keys and integer values only — `CHARACTER_SCHEMA_V1` constrains the field the
  same way (`additionalProperties: {"type": "integer"}`), and parity is the
  point.
- A new frozen `PresetSexualBaseline` dataclass mirrors the import card's
  `sexual_baseline` object (`arousal`, `virgin`, `sensitivity` required;
  `wetness`, `shame`, `exposure`, `climax_phase` optional) with a `to_record()`
  producing the storage shape `SexualState` reads.
- `PlayerPreset` gains a keyword-only `sexual_baseline: PresetSexualBaseline | None = None`.
  `None` preserves today's behavior exactly: nothing is written and
  `SexualState` keeps applying its generic default lazily.
- A load-time validator checks every level against its tuple in
  `world/lore/sexual_vocab.py` and every `sensitivity` key against `BODY_PARTS`
  plus `GENERIC_BODY_PART`.
- Activation writes `disguised_stats` as `dict(...) or None` (mirroring the
  import loader) and writes `sexual` only when the preset declares a baseline.
- `_CREATION_ATTRIBUTE_KEYS` gains `disguised_stats` and `sexual` so both are
  restored on a rolled-back activation.
- Creation activation joins the import loader as a sanctioned **writer** of
  `disguised_stats`. The read-side boundary is untouched: the forbidden-module
  list and the two sanctioned readers are unchanged.

No backward compatibility or data migration: the project has no released users.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-character-creation`: a new requirement covering both registry fields,
  their load-time validation, the activation writes, and the widened rollback
  snapshot.
- `disguised-stats-boundary`: the consumer requirement gains an explicit
  writer/reader distinction, naming creation activation alongside the import
  loader as a writer while the reader set stays at exactly two.
- `sexual-state-handler`: the baseline-construction requirement names preset
  activation as a second producer of `entity.db.sexual` beside the import path.

## Impact

- `world/lore/player_presets.py` — `PresetSexualBaseline`, the two new fields,
  two new validators.
- `world/rules/character_creation.py` — two activation attribute writes;
  `_CREATION_ATTRIBUTE_KEYS` gains `disguised_stats` and `sexual`.
- `world/rules/sexual_state.py` — read-only; the existing construction path
  already handles a populated `db.sexual`.
- `world/lore/tests/test_player_presets.py`,
  `world/rules/tests/test_character_creation.py`,
  `world/rules/tests/test_disguise_boundary.py`.
- Unaffected: the disguise read boundary and its forbidden-module list, the
  sexual act catalogue, custom creation, and the import path.
