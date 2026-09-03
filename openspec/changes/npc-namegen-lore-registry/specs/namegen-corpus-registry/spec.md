# namegen-corpus-registry — Delta Spec

## ADDED Requirements

### Requirement: Name pack registry freezes the vendored corpus at import time
`world/lore/names.py` SHALL parse the five pack JSON files under `third_party/fantasy-namegen/data/packs/`
and the translit table `third_party/fantasy-namegen/data/translit/fantasy.json` at module import, and
expose the results as `NAME_PACK_REGISTRY` wrapped in `MappingProxyType`. It SHALL define frozen
`NamePart` dataclass with fields `text` (original-language spelling), `zh` (Traditional Chinese
translit rendering), and `meaning_zh` (etymology/imagery note, empty string when the corpus part
carries none), and frozen `NamePack` dataclass with fields `key`, `race_key: str | None`,
`surnames: tuple[NamePart, ...]`, `given` (a `Mapping[str, tuple[NamePart, ...]]` with exactly the
keys `"m"`, `"f"`, `"u"`), and `naming_note_zh` (taken from the pack's `rules.naming.note`).
`NAME_PACK_REGISTRY` SHALL contain exactly the five pack keys `fantasy-human`, `fantasy-elf`,
`fantasy-dwarf`, `fantasy-orc`, `fantasy-halfling`, carrying every corpus part exactly once —
1,274 part occurrences across the current vendored snapshot. `NamePart.text` SHALL NOT be
required to be globally unique: a source spelling may legitimately appear in several packs or
several `given` pools (1,261 distinct spellings across 1,274 occurrences), and every occurrence
is carried as its own `NamePart`. `NamePack.given` values SHALL be plain `dict`
instances (never `MappingProxyType`) so `dataclasses.asdict` can deepcopy them on the sync mirror
path.

#### Scenario: Registry has exactly the five vendored packs
- **WHEN** `NAME_PACK_REGISTRY` is inspected
- **THEN** it contains exactly the keys `fantasy-human`, `fantasy-elf`, `fantasy-dwarf`,
  `fantasy-orc`, and `fantasy-halfling`, each a `NamePack` with non-empty `surnames` and a
  `given` mapping that has exactly the keys `"m"`, `"f"`, and `"u"`, and the registry object is a
  `MappingProxyType`

#### Scenario: Part coverage matches the vendored corpus array by array
- **WHEN** every pack's `surnames` and each `given` pool (`m`, `f`, `u`) is compared against the
  corresponding source array in the vendored pack JSON
- **THEN** per pack and per source array the registry contents match the source element-for-element
  in length and order, and the total number of registry occurrences equals the total number of
  parts in the vendored JSON files (1,274 on the current snapshot), with no occurrence duplicated
  or dropped — global uniqueness of `NamePart.text` is NOT required, since 1,261 distinct
  spellings legitimately yield 1,274 occurrences across packs and pools

#### Scenario: Every part carries a Chinese rendering and never leaks raw text into zh
- **WHEN** every `NamePart` in the registry is inspected
- **THEN** `zh` is the non-empty value the translit table maps its `text` to, and `meaning_zh` is
  a string (empty allowed when the corpus part has no `meaning`); no part's `zh` contains ASCII
  letters, i.e. no lookup silently fell back to the untranslated original

### Requirement: Race binding maps the three playable races and leaves the spare packs unbound
`world/lore/names.py` SHALL expose `NAME_PACK_BY_RACE` as a `MappingProxyType` mapping exactly
`"human"` → `"fantasy-human"`, `"elf"` → `"fantasy-elf"`, and `"beastfolk"` → `"fantasy-orc"`,
with every value a key of `NAME_PACK_REGISTRY` and every key a key of `RACE_REGISTRY`. The
`fantasy-dwarf` and `fantasy-halfling` packs SHALL be registered with `race_key=None` and SHALL NOT
appear as values of `NAME_PACK_BY_RACE`.

#### Scenario: The three races bind to their packs
- **WHEN** `NAME_PACK_BY_RACE` is inspected
- **THEN** it has exactly the three keys `human`, `elf`, and `beastfolk` bound to
  `fantasy-human`, `fantasy-elf`, and `fantasy-orc` respectively, and each bound pack's `race_key`
  equals its race key

#### Scenario: Dwarf and halfling packs exist but bind to no race
- **WHEN** `NAME_PACK_REGISTRY["fantasy-dwarf"]` and `NAME_PACK_REGISTRY["fantasy-halfling"]` are
  inspected
- **THEN** each has `race_key is None`, and neither pack key appears in `NAME_PACK_BY_RACE.values()`

### Requirement: Registry load enforces the corpus invariants at import time
Loading `world.lore.names` SHALL validate, at module import, three invariants and raise a named
error (never silently accepting deviating data): (1) the translit table covers every corpus part,
with the missing words enumerated in the error message; (2) every pack's `m`, `f`, and `u` pools are
non-empty, every pack's `surnames` is non-empty, and every `NAME_PACK_BY_RACE` value names a
registered pack; (3) the longest composed
display name (the maximum-length `given.zh` plus separator plus `surname.zh` across all packs)
passes `world/rules/character_creation.py::_validate_name`, reached via a function-local deferred
import so `lore` gains no top-level dependency on `rules`.

#### Scenario: Full translit coverage holds on the vendored snapshot
- **WHEN** the translit table is checked against every `text` value of every pack part
- **THEN** the missing-word set is empty, which is why importing `world.lore.names` succeeds

#### Scenario: A translit gap names the missing words and fails the import
- **WHEN** the loader runs against corpus data containing a part the translit table does not map
- **THEN** loading raises a named error whose message enumerates the missing words, and no
  partially-built registry is left bound

#### Scenario: Pools are non-empty and race mappings resolve
- **WHEN** every registered pack's `surnames` and `m`, `f`, and `u` pools and every
  `NAME_PACK_BY_RACE` value are inspected
- **THEN** each source array contains at least one `NamePart` and each mapping value is a key of
  `NAME_PACK_REGISTRY`

#### Scenario: The longest composed name passes the creation name validator
- **WHEN** the longest `given.zh・surname.zh` combination across all packs is passed through
  `_validate_name`
- **THEN** it returns without raising, so every composed display name fits the 1-to-64-character
  display-name rule

### Requirement: Display names compose from Chinese renderings with the middle-dot separator
`world/lore/names.py` SHALL define `NAME_SEPARATOR = "・"` (U+30FB KATAKANA MIDDLE DOT) as the only
composition constant in the registry layer, and `compose_display_name(given: NamePart, surname:
NamePart) -> str` returning `f"{given.zh}{NAME_SEPARATOR}{surname.zh}"`. The original-language
`text` field SHALL never appear in the composed output.

#### Scenario: Composition format is given, separator, surname
- **WHEN** `compose_display_name` is called with a given part (`zh` 「加斯帕」) and a surname part
  (`zh` 「斯諾」)
- **THEN** it returns 「加斯帕・斯諾」 with the U+30FB separator between the two Chinese renderings

#### Scenario: Raw corpus text never reaches composed output
- **WHEN** composed display names are built for every given/surname pairing within one pack
- **THEN** no result contains any part's `text` value as a substring where a Chinese rendering is
  expected, i.e. every composed name is built solely from `zh` fields and the separator

### Requirement: NAME_PACK_REGISTRY is mirrored into LoreRecord Scripts idempotently
`world/lore/sync.py::_ALL_REGISTRIES` SHALL include `NAME_PACK_REGISTRY` under the category key
`"name_packs"`, so `sync_all()` mirrors it into `LoreRecord` Scripts exactly as it mirrors every
other lore registry, including idempotency across repeated calls and nested-field serialization via
the existing `_db_safe(asdict(entry))` path.

#### Scenario: sync_all mirrors all five name packs
- **WHEN** `sync_all()` runs
- **THEN** a `LoreRecord` Script exists for each of the five pack keys, keyed
  `"lore:name_packs:<pack key>"`, with `db.fields` matching the corresponding `NamePack` entry

#### Scenario: Repeated sync creates no duplicate name-pack records
- **WHEN** `sync_all()` is called twice in succession
- **THEN** exactly five `LoreRecord` Scripts exist under the `"name_packs"` category after the
  second call, with identical field contents

#### Scenario: lore-startup-sync's own spec is unmodified
- **WHEN** `openspec/specs/lore-startup-sync/spec.md` is inspected after this change lands
- **THEN** its text is unchanged — this change extends `sync_all()`'s behavior without altering any
  requirement or scenario that spec already documents
