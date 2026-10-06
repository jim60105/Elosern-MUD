# GM Portal S4 Design: Authored World Data Browser

- Date: 2026-10-06
- Status: Approved design
- Parent: `docs/superpowers/specs/2026-10-06-gm-portal-design.md` (sub-project S4)
- Depends on: S1 (portal skeleton), S3 (`GmEntityLink`, `GmJsonTree`, readers
  read-only contract)

S4 lets the operator browse the authored world data the server has loaded and
follow references between registry entries in both directions. Authored data
stays read-only source in git; S4 never writes a source file.

## 1. Terminology

The authored data lives in module-level Python registries: immutable mappings
from a stable `key` to a frozen dataclass entry, built at import time. They are
not database tables. The design keeps the project's existing vocabulary:

- **registry (登錄表)**: one module-level mapping, for example
  `RACE_REGISTRY`.
- **entry (條目)**: one value in a registry.
- **key**: the entry's stable identifier.
- **reference**: a field whose value is the key of an entry in another
  registry.

The reference model is borrowed from database foreign keys (declared on the
referencing field, with a named inverse and an integrity check), but no name in
code, API, or UI uses table or foreign-key vocabulary. This keeps registries
distinct from the Django models that S3 inspects.

## 2. Scope decisions

S4 was reviewed for over-design and trimmed. Out of scope:

- Enforcing reference integrity at server startup. The roughly 97 existing
  per-registry validations already guard startup; integrity of declared
  references is a CI contract instead (§3.3).
- Composite references (an entry's key that must also agree with another of
  its fields) and prefixed or parsed keys. Existing validators keep covering
  these; such fields are not declared as references.
- Heuristic discovery of registries. The index is maintained by hand; a
  registry missing from it is simply not browsable.
- Refactoring `world/lore/sync.py`. `_ALL_REGISTRIES` stays as is.
- Per-rulebook adapters that render loaded config objects. Rulebooks and
  prompts are shown as source text; keyed rulebook data is browsable through
  the registry index.
- A dedicated prompt diagnostics page (`world.prompts.validate` exists) and
  an integrity report page.
- Reverse lookups from authored entries into runtime state (for example the
  living individuals of a species).

## 3. Model

### 3.1 `world/lore/registry_refs.py`

A leaf module with no game imports, so every registry module can use it
without import cycles.

```python
def ref(registry: str, *, inverse: str, nullable: bool = False) -> Mapping[str, Any]
def ref_many(registry: str, *, inverse: str) -> Mapping[str, Any]
```

Both return a `dataclasses.field` metadata mapping:

```python
@dataclass(frozen=True)
class MonsterSite:
    species: str = field(metadata=ref("monster_species", inverse="sites"))
```

- `ref`: the field holds one key (or `None` when `nullable`).
- `ref_many`: the field holds a tuple, list, or frozenset of keys.
- `inverse`: the name under which the target entry lists its referrers.
- Nested dataclasses inside an entry (for example quest stages or item effect
  rows) may declare references; the walk recurses into them.
- Adding metadata changes no field type, default, or value.

### 3.2 `world/lore/registry_index.py`

```python
@dataclass(frozen=True)
class RegistrySpec:
    name: str                      # snake_case, unique
    label: str                     # zh-TW display name
    group: str                     # 世界, 生物, 物品與經濟, 聚落, 人物, 技能, 任務, 規則書
    loader: Callable[[], Mapping[str, Any]]   # lazy; returns key -> frozen dataclass
    source_path: str               # repository-relative source file or directory
    summary_fields: tuple[str, ...] = ()
```

- `REGISTRY_INDEX: tuple[RegistrySpec, ...]` lists every registry. Loaders are
  lazy so `world/lore` does not import `world/rules`, `world/skills`, or
  `world/quests` at import time.
- Coverage: all `world/lore` registries (the 21 in `_ALL_REGISTRIES` plus
  items, NPC profiles, dialogue rows, assortments, player presets, starting
  kits, NPC tiers, scene archetypes), skills, sexual acts, quest definitions,
  and keyed rulebook data (professions, guild exam profiles, shop configs,
  service host rows, monster behaviour profiles).
- Parameter-only rulebooks (`combat.yaml`, `clock.yaml`, ...) are not
  registries; they appear only in the source viewer (§4.3).
- `build_reference_index()` walks every entry, collects declared references,
  and returns forward and inverse maps. Registries are immutable at runtime,
  so the result is cached for the process lifetime with no invalidation.
- `check_references() -> list[DanglingReference]` reports every declared
  reference whose target registry has no such key:
  `(registry, key, field_path, target_registry, missing_key)`.

### 3.3 First batch of reference declarations

References are declared only where reverse lookup is useful now:

- Monster species, variants, sites, and ambient placements.
- Quest definitions.
- Items.
- Places, settlements, and shops.
- NPC profiles.

All other registries are browsable without reference links; declarations are
added later as needed.

If declaring the first batch exposes a dangling reference in shipped data, the
same change fixes the data or records it as an explicit task.

### 3.4 Contract tests (`world/lore/tests/`)

- `check_references()` returns an empty list against shipped data.
- Every `ref`/`ref_many` names a registry present in `REGISTRY_INDEX`.
- No two references into the same target registry share an `inverse` name.
- Every registry in `world/lore/sync.py` `_ALL_REGISTRIES` is present in
  `REGISTRY_INDEX`.
- Registry names are unique; every loader returns a mapping whose values are
  dataclass instances.
- Unit tests over small fake registries cover `ref`, `ref_many`, `nullable`,
  nested dataclasses, and the `DanglingReference` shape.

## 4. Portal

The portal always shows the data loaded in the server process, which is what
the game is using, not a fresh read from disk. Every page names the source
path and states that changes are made in source and applied by restart.

### 4.1 Pages

```
世界資料
├ 登錄表 list grouped by group (label, name, entry count, source path)
├ /gm/world/<registry>         entries: key + summary fields, filter, text search
├ /gm/world/<registry>/<key>   entry detail
│    ├ 欄位   every dataclass field; reference fields render as links
│    ├ 引用   entries this entry references, by field
│    └ 被引用 referrers grouped by inverse name
└ /gm/world/sources/<name>     source viewer (§4.3)
```

- Entry values are serialised with the rules of `world/lore/sync.py`
  `_db_safe` (enum to value, tuple to list), recursing into nested dataclasses,
  and rendered with `GmJsonTree`.
- Without `summary_fields`, lists show the key and the first string field.

### 4.2 Search

Cross-registry search matches registry keys and string field values across all
indexed registries in memory.

### 4.3 Source viewer

Read-only, monospace, line-numbered text of `world/rules/rulebook/*.yaml`
(including `commerce/`) and `prompts/*.yaml`. The file name must be in an
allowlist built from those directories at request time; arbitrary paths are
rejected.

### 4.4 Links from S3

Runtime fields that hold registry keys (a character's `race`, a monster's
`species` and `variant`, a quest record's `definition_key`, ...) render through
`GmEntityLink` as links to the S4 entry page.

## 5. API

| Route | Purpose |
| --- | --- |
| `GET /gm/api/registry/` | Registry index (name, label, group, entry count, source path); with `?q=`, cross-registry search |
| `GET /gm/api/registry/<registry>?cursor=&limit=&q=` | Entry list |
| `GET /gm/api/registry/<registry>/<key>` | Entry detail: fields, references, referrers |
| `GET /gm/api/sources/` | Source viewer allowlist |
| `GET /gm/api/sources/<name>` | One source file's text |

- Unknown registry: `404` `registry_not_found`. Unknown key: `404`
  `entry_not_found`. Name outside the allowlist: `404` `source_not_found`.
- The readers live in `web/gm/readers/world.py` and fall under the S3
  read-only AST contract.

## 6. Tests

- §3.4 contract and unit tests.
- API: shapes, pagination, search, unknown registry and key, source allowlist
  (including traversal attempts such as `../`).
- Vitest: field, reference, and referrer section rendering. Storybook stories
  for new components.
- New Python test modules registered in `.github/evennia-shards.json`.
