# Proposal: human-subrace-lineage-rework

## Why

`SUBRACE_REGISTRY`'s five human entries encode a wealth ladder with discriminatory
vocabulary (「底層平民」), contradict the lore on three axes (occupational determinism
against `docs/lore/overview.md:39`'s fixed-at-birth stats; agriculture as the empire's
dominant industry per `docs/lore/overview.md:77` while the farmer group got the smallest
kit; English `specialty` prose leaking to players through
`commands/character_creation.py:191` and
`web/static/webclient/js/elosern/creation_menu.js:247`), and break synonymy between the
English keys and the Chinese display fields (`human_laborer` vs 底層平民;
`common_name_zh` holding an occupation list for humans only).

## What Changes

- **BREAKING** Rename three human subrace keys to a geographic-lineage axis:
  `human_wealthy` → `human_coastal`, `human_commoner` → `human_plains`,
  `human_laborer` → `human_highland`; `human_royal` and `human_noble` keep their keys.
- Set the zh-TW `display_name_zh`/`common_name_zh` pairs per the approved naming table:
  王族/王室血脈, 貴族/貴族血脈, 濱海民/濱海血脈, 平原民/平原血脈, 山地民/山地血脈. The
  English key, `display_name_zh`, and `common_name_zh` are synonymous for every human
  subrace; 農民 is no longer a subrace but an occupation practised inside 平原民.
- Keep all five zero-sum `StatModifiers` values unchanged (including the 王族 MP override
  120–220) and rewrite their lore rationale onto the lineage axis in
  `tmp/story_settings/world_info.md` via a new human 〈數值傾向〉 block mirroring the
  beastfolk block.
- Replace the five human `specialty` strings with the approved zh-TW lineage prose verbatim.
- Rework the three commoner-lineage starting kits into equal COMMON-rarity triads
  (濱海民 普通劍+皮甲+鐵短刀, 平原民 普通劍+皮甲+銀髮簪, 山地民 普通劍+皮甲+狩獵擲斧);
  王族/貴族 kits unchanged; 木製棍棒 disappears from every kit.
- Update tests, fixtures, main-spec text, lore docs, and `world_info.md` to the new keys
  and names. No `### Requirement:` heading is renamed, so every `@covers_requirement`
  slug stays valid.
- **No save-data compatibility layer**: no alias table, no migration script. There are no
  existing characters and the database is rebuilt (precedent: commit `1fa6ea5
  feat(traits)!: retype magic_level counter as magic_power static trait`). The DB rebuild
  retires the three orphan `lore:subraces:*` Scripts left by the rename
  (`world/lore/sync.py::sync_all` creates and overwrites but never prunes).

## Out of scope

- Translating the ten remaining elf/beastfolk `specialty` values and adding the
  registry-wide rule that `specialty` SHALL be zh-TW for all 15 entries — successor
  change `subrace-specialty-localization` (Change 2).
- Wearing custom-kit items at activation and the validator hardening it requires —
  successor change `custom-kit-worn-at-activation` (Change 3).
- Adding prune capability to `world/lore/sync.py::sync_all` (a genuine gap, explicitly
  out of scope; the DB rebuild removes the orphans).
- Replacing `Subrace` with a separate `Origin`/`Lineage` concept — rejected alternative
  (design §6), recorded so the question is not reopened.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `lore-registries`: the human `Subrace` entries become the specified lineage contract —
  the `Subrace registry covers elf branches, beastfolk subspecies, and human bloodline
  subraces with stat modifiers` requirement is modified in place (renamed keys, zh-TW
  synonym naming, lineage-rationale stat scenarios, five zh-TW `specialty` strings), and
  a new requirement fixes the §3.4 human starting-kit table. No requirement heading is
  renamed.

## Impact

- **Code**: `world/lore/races.py` (five human `Subrace` entries),
  `world/lore/starting_kits.py:32-36`, `world/lore/player_presets.py:278` (艾莉莎's
  subrace).
- **Tests**: `world/lore/tests/test_races.py`, `world/lore/tests/test_player_presets.py`,
  `world/lore/tests/test_starting_kits.py`. No test modules added or renamed, so
  `.github/evennia-shards.json` needs no update.
- **Fixtures**: `world/imports/examples/example_character.json:10`,
  `web/browser_support/browser_fixtures_data.py:61` (`SHIPPED_BASE_SUBRACE`).
- **Specs/docs**: `openspec/specs/lore-registries/spec.md`, `docs/lore/overview.md:39`,
  `docs/development/adding-player-presets.md`, `tmp/story_settings/world_info.md`.
- **Side effect**: the rename dissolves the pre-existing double meaning of
  `human_commoner` — afterwards the key names only the `StaticTier`, an unrelated
  concept whose occurrences (design §3.6) are deliberately untouched.

## Batch:

depends-on: (none — Change 1 of 3; run first)
conflicts-with: `subrace-specialty-localization` — touches the same `specialty` fields in
`world/lore/races.py` (elf+beastfolk entries) and the same `lore-registries` spec file,
but on disjoint entries/requirements; must land AFTER this change so Change 2's
localization requirement covers this change's five zh-TW human strings.
conflicts-with: `custom-kit-worn-at-activation` — references this change's three new
human kits as collision-clean in its feasibility audit; must land AFTER this change.
