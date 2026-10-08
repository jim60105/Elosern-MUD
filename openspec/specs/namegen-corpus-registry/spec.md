# namegen-corpus-registry Specification

## Purpose

Freeze the vendored CC BY 4.0 fantasy-namegen corpus (`third_party/fantasy-namegen/`) into an
import-time lore registry — `NAME_PACK_REGISTRY` / `NAME_PACK_BY_RACE` — with fail-fast corpus
invariants, the 「名‧姓」 Chinese display-name composition contract, the idempotent
`sync_all()` mirror, and the container-image packaging the runtime import depends on.

## Requirements

### Requirement: Name pack registry freezes the vendored corpus at import time
`world/lore/names.py` SHALL parse the five pack JSON files under `third_party/fantasy-namegen/data/packs/`
and the translit table `third_party/fantasy-namegen/data/translit/fantasy.json` at module import,
exposing the results as `NAME_PACK_REGISTRY` wrapped in `MappingProxyType`, built from frozen
`NamePart` and `NamePack` dataclasses. The registry SHALL contain exactly the five vendored pack
keys, carrying every corpus part exactly once.

#### Scenario: Registry has exactly the five vendored packs
- **WHEN** `NAME_PACK_REGISTRY` is inspected
- **THEN** it contains exactly the keys `fantasy-human`, `fantasy-elf`, `fantasy-dwarf`,
  `fantasy-orc`, and `fantasy-halfling`, each a `NamePack` with non-empty `surnames` and a
  `given` mapping that has exactly the keys `"m"`, `"f"`, and `"u"`, and the registry object is a
  `MappingProxyType`

#### Scenario: Mutating any exported pack data raises
- **WHEN** a consumer attempts `pack.given["m"] = ...`, `.clear()`, `.pop(...)`, or
  `.setdefault(...)` on any exported `NamePack.given`
- **THEN** each attempt raises `TypeError` and the registry contents are unchanged, and the
  mirror path (`_db_safe(asdict(pack))`) still yields plain dict fields equal to the frozen
  contents

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

#### Scenario: NamePart carries spelling, Chinese rendering, and etymology
- **WHEN** any `NamePart` field set is inspected
- **THEN** it has `text` (original-language spelling), `zh` (Traditional Chinese translit rendering),
  and `meaning_zh` (etymology/imagery note, empty string when the corpus part carries none)

#### Scenario: NamePack fields mirror the pack document
- **WHEN** any `NamePack` field set is inspected
- **THEN** it has `key`, `race_key: str | None`, `surnames: tuple[NamePart, ...]`, `given` (a
  `Mapping[str, tuple[NamePart, ...]]` with exactly the keys `"m"`, `"f"`, `"u"`), and
  `naming_note_zh` (taken from the pack's `rules.naming.note`)

#### Scenario: Corpus count and spelling multiplicity are stated
- **WHEN** the registry is compared against the current vendored snapshot
- **THEN** it carries 1,274 part occurrences, and `NamePart.text` is NOT required to be globally
  unique: a source spelling may legitimately appear in several packs or several `given` pools
  (1,261 distinct spellings across 1,274 occurrences), and every occurrence is carried as its own
  `NamePart`

#### Scenario: given pools are a concrete immutable dict subclass
- **WHEN** the type of `NamePack.given` is inspected
- **THEN** it is a concrete `dict` subclass (`FrozenDict`) that is never a `MappingProxyType`, so
  `dataclasses.asdict` can deepcopy it on the sync mirror path (deepcopy rebuilds the type via
  `__reduce__`), and it rejects every mutation
  (`__setitem__`/`__delitem__`/`update`/`pop`/`clear`/`setdefault` raise `TypeError`), so the
  frozen-registry invariant holds below the top-level mapping — a consumer can never empty a
  validated pool after import

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
Loading `world.lore.names` SHALL validate three invariants at module import and raise a named
error (never silently accepting deviating data): (1) the translit table covers every corpus part;
(2) the pool/surname non-emptiness, exact pack-set, and race-binding invariants enumerated in the
scenarios below; (3) each pack's representative longest composition passes
`world/rules/character_creation.py::_validate_name`. The whole load/validate step SHALL be a pure
builder function.

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
- **WHEN** each pack's representative longest composition (longest `given.zh` in its pools, the
  separator, and its longest `surname.zh`) is passed through `_validate_name`
- **THEN** it returns without raising, so every composed display name fits the 1-to-64-character
  display-name rule

#### Scenario: An injected invalid corpus fails through the same builder
- **WHEN** `_build_registry` is called with injected payloads whose translit table lacks a part,
  whose pools or `surnames` are empty, whose pack set deviates from the five vendored keys, whose
  race bindings name an unregistered race key or an unregistered pack, or whose longest composed
  `zh` rendering exceeds the validator bound
- **THEN** each call raises the named error instead of returning a registry, proving the import
  tail actually invokes every invariant on the constructed data

#### Scenario: Load validates pool, pack-set, and race-binding integrity
- **WHEN** invariant (2) is checked at import
- **THEN** every pack's `m`, `f`, and `u` pools are non-empty, every pack's `surnames` is
  non-empty, every pack set is exactly the five vendored pack keys, and every race-binding entry
  names a `RACE_REGISTRY` key and a registered pack

#### Scenario: The longest composition is the strict upper bound
- **WHEN** a pack's representative longest composition is formed for invariant (3)
- **THEN** it is the longest `given.zh` in that pack's pools plus the separator plus that pack's
  longest `surname.zh`, a strict upper bound over every pairing in the pack, and the validator is
  reached via a function-local deferred import so `lore` gains no top-level dependency on `rules`

#### Scenario: The builder is pure and injection-testable
- **WHEN** the load/validate step runs in production and in tests
- **THEN** the builder takes the pack payloads, the translit table, and the race bindings as
  explicit arguments, production passes the module constants at the import tail, and every
  rejection path is testable by injection without touching the filesystem or module globals

#### Scenario: The settings-required import chain is safe
- **WHEN** the deferred validator import executes the Django/Evennia import chain
- **THEN** this is safe because every consumer imports `world.lore.names` only inside a
  bootstrapped Evennia process (server startup, the lore test runner, and later rules/UI
  consumers)

### Requirement: Display names compose from Chinese renderings with the middle-dot separator
`world/lore/names.py` SHALL define `NAME_SEPARATOR = "‧"` (U+2027 HYPHENATION POINT) as the only
composition constant in the registry layer, and `compose_display_name(given: NamePart, surname:
NamePart) -> str` returning `f"{given.zh}{NAME_SEPARATOR}{surname.zh}"`. The original-language
`text` field SHALL never appear in the composed output.

#### Scenario: Composition format is given, separator, surname
- **WHEN** `compose_display_name` is called with a given part (`zh` 「加斯帕」) and a surname part
  (`zh` 「斯諾」)
- **THEN** it returns 「加斯帕‧斯諾」 with the U+2027 separator between the two Chinese renderings

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

### Requirement: The vendored name corpus ships in the runtime image
The `Containerfile` SHALL copy `third_party/` into the `app-layout` stage at `/app/third_party/`
so the final image (which copies the whole prepared `/app` tree) carries the corpus that
`world/lore/names.py` parses at import time, and `.containerignore` SHALL NOT exclude
`third_party/`. Without the corpus the container crashes at every startup when `world.lore.sync`
imports `names`.

#### Scenario: App-layout stage bakes the corpus
- **WHEN** `tests/test_container_contract.py` inspects the Containerfile
- **THEN** the `app-layout` stage contains `COPY --chown=root:0 third_party/ /app/third_party/`,
  and no `.containerignore` pattern mentions `third_party`
