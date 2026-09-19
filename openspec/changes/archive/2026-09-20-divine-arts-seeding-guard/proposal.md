## Why

狀態偽裝 is the root node of the divine-mystery lineage and declares
`requires_divine_arts=True`, so only a race whose `RaceProfile.can_use_divine_arts` is true can cast
it. The setting rule that follows is exact: an entity that cannot use divine arts cannot have a veil,
because nothing else in this world can place one.

That rule is enforced at CAST time and nowhere else. Three seeding boundaries let an authored
declaration create the state the cast gate forbids:

- `world/lore/player_presets.py::_validate_preset_disguised_stats` validates only shape — pair
  structure, a text axis key, an exact `int` value, no duplicate keys. It never consults the preset's
  race, so a non-divine preset declaring `disguised_stats` loads cleanly.
- `world/imports/validate.py::_check_disguised_stats_subset` checks only that each disguised key also
  appears in `stats`. `can_use_divine_arts` does not appear anywhere in that module.
- `world/imports/validate.py::_check_skills` checks only that a declared key exists in the registry,
  so an import can grant a non-divine entity ownership of `status_disguise` itself. The cast gate
  refuses the cast, but the ownership persists and appears in the character's skill list.

The shipped reference example is already in violation: `world/imports/examples/example_character.json`
is `race: "human"` and carries `disguised_stats`. The three preset cards that do declare a veil are
elves holding `status_disguise`, but that is an authoring coincidence — nothing checks it.

This also matters for `collapse-veil-reveal-line`, whose argument is that this world admits exactly
one grade of veil because only a bloodline-gated mystery can write one. That premise is true of the
cast path and merely conventional at the seeding boundaries. This change makes it an enforced
invariant.

## What Changes

- Establish one invariant across every seeding boundary: an entity whose race cannot use divine arts
  SHALL NOT be seeded with a disguise layer, and SHALL NOT be declared as owning a skill that
  requires divine arts.
- `_validate_preset_disguised_stats` gains the race check and raises at lore-registry import, matching
  the load-time stance `_validate_preset_skill_kits` already takes for divine-arts skill ownership.
- `world/imports/validate.py` gains two rejections: a disguise layer declared for a record whose race
  cannot use divine arts, and a `skills`/`passives` entry requiring divine arts on such a record. Both
  are rejections rather than warnings — the record describes state the engine would refuse to produce.
- **BREAKING** (authored example content): `world/imports/examples/example_character.json`'s
  `disguised_stats` becomes empty (`{}`), because a human reference record may not carry a populated
  layer — `CHARACTER_SCHEMA_V1` requires the key itself, so it stays present but empty. The example
  keeps its human race, since that is what makes it a useful baseline reference. The
  `import-reference-example` requirement that asserted the field non-empty is replaced accordingly.
- `docs/development/adding-player-presets.md` gains the new rejection rows in its validator table.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `disguised-stats-boundary`: gains a requirement bounding WHO may carry a disguise layer. The
  capability currently bounds the layer's readers, its writers, and its companion record, but never
  states that the wearer must be able to produce a veil in the first place.
- `import-validation`: gains two rejection requirements, one for a bloodline-inconsistent disguise
  layer and one for bloodline-inconsistent skill ownership.
- `import-reference-example`: the "exercises every major schema branch" requirement's disguised_stats
  scenario is replaced — the human baseline record can no longer demonstrate a populated layer, so the
  scenario now demonstrates the field staying empty instead.

## Impact

- `world/lore/player_presets.py` — one validator gains a race check.
- `world/imports/validate.py` — one new check function, one extended check function, both wired into
  the existing rejection pipeline.
- `world/imports/examples/example_character.json` — `disguised_stats` emptied (key stays, schema
  requires it).
- `world/imports/tests/test_reference_example.py` — the assertion that the example's
  `disguised_stats` is truthy is replaced with an assertion that it is empty.
- `docs/development/adding-player-presets.md` — validator table rows; contract-tested by
  `tests/test_preset_authoring_docs_contract.py`, which must stay green.
- `world/lore/tests/`, `world/imports/tests/` — behavior tests over synthetic presets and synthetic
  records; no new test module, so `.github/evennia-shards.json` is unchanged.
- **Relationship to `collapse-veil-reveal-line`**: independent files, no conflict, either order works.
  Landing this one first is preferable, because it converts that change's stated premise from a
  convention into an enforced invariant.
