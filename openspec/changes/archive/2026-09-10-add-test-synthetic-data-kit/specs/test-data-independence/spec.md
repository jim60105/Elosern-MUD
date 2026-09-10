## ADDED Requirements

### Requirement: The synthetic test-data kit provides registry-compatible catalogs
The repository SHALL provide a shared synthetic game-data kit at
`world/tests/synthetic_data.py`: per-catalog dicts built from the real definition
dataclasses, covering at least items, skills, races/subraces, player presets, NPC and
monster tiers, anchors, wilderness regions, city gates, scene archetypes, shops/economy,
quests, titles, dialogue, buffs, and sexual acts, whose keys carry the reserved `t_`
prefix and whose display fields are invented Traditional-Chinese prose that occurs
nowhere in shipped data. The kit SHALL only carry catalog entries that at least one
test consumes; migration changes add exotic shapes through the kit's `make_*` factories
with local registration rather than growing shared catalogs with unused entries. The kit
itself and its mirrors SHALL be clean under the test-data lint gate.

#### Scenario: Kit content is gate-clean
- **WHEN** the test-data lint scanner evaluates `world/tests/synthetic_data.py` and the
  JavaScript mirror files
- **THEN** it reports zero shipped-content flags for those files

#### Scenario: Kit keys cannot collide with shipped data
- **WHEN** the kit self-test compares every kit key and display label against the shipped
  catalog token universe
- **THEN** no kit key or label matches a shipped token, and the test fails the moment a
  future rename or new prose would collide

#### Scenario: Local fixture path is first-class
- **WHEN** a test needs an entity shape absent from the shared synthetic catalogs
- **THEN** it builds one with the kit's `make_*` factory and registers it for its own
  scope only, without editing the shared catalogs

### Requirement: The kit patches and restores registries exactly
The kit SHALL expose a scoped patch helper usable as both a context manager and a
class/test decorator that replaces the selected shipped catalogs with the synthetic
catalogs for the decorated scope and restores the previous state exactly on exit —
`patch.dict` semantics for mutable registries and attribute-swap semantics (including
consumer-module bindings that name-imported the registry, discovered from the source
tree rather than a hand-maintained list) for frozen `MappingProxyType` catalogs —
driven by a single registry-target table maintained only inside the kit, including the
import-time captures in `world/lore/sync.py`.

#### Scenario: Patch scope ends with the shipped registry intact
- **WHEN** a test decorated with the kit helper resolves `t_iron_fang` through production
  code inside the scope, and an undecorated test then resolves the same registry
- **THEN** the decorated test sees only synthetic entries and the subsequent test sees
  the shipped registry byte-identical to its pre-test state

#### Scenario: Frozen catalogs are substitutable
- **WHEN** a behavior test activates the synthetic catalogs for a `MappingProxyType`
  registry such as `NPC_TIER_REGISTRY`
- **THEN** production code consuming that registry through its name-imported binding
  resolves only synthetic tiers for the duration of the scope, for every binding the
  kit's discovery pass finds (a binding discovered by the pass but left unpatched is a
  self-test failure)

### Requirement: The kit installs process-wide for separate test processes
The kit SHALL expose an idempotent process-scoped install bootstrap that the
browser-test settings module activates under its dedicated opt-in flag, so the
managed-browser seed process, the managed Evennia server, and their startup
world-bootstrap mirror synthetic catalogs into their private database instead of
shipped content.

#### Scenario: Harness processes complete under the install flag
- **WHEN** the managed browser seed process and the managed Evennia server run with the
  synthetic-install flag set against a private database
- **THEN** the seed completes with a `t_`-keyed base character, the server completes
  startup, and the mirrored lore rows carry `t_`-prefixed keys (plus only the
  documented runtime seams) instead of shipped content

### Requirement: JavaScript test corpora share an equivalent synthetic mirror
The Vitest and Node-gate test corpora SHALL share a synthetic payload mirror (module
files under the respective test support directories, excluded from test collection)
carrying the same `t_` identifiers and display prose as the Python kit, and a
Node-gate self-test SHALL fail if either mirror drifts from the shared literals.

#### Scenario: JS mirror matches the Python kit
- **WHEN** the Node gate and the Python kit self-test run against the mirrored literals
- **THEN** the JavaScript mirror payloads and the Python kit entries agree on every `t_`
  id and display label, and a deliberate drift in either side turns one of the two red
