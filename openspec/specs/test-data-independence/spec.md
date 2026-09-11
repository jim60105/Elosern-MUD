## Purpose

The test-data independence capability: a deterministic lint gate
(`tools.test_data_lint`) that blocks unregistered references to shipped game
content in test sources, a provably shrink-only exemption ledger seeded with
the pre-existing debt corpus, the `Data-contract test:` classification tag,
and the CI + documentation wiring that keeps behavior tests resolvable without
a database or shipped-content coupling.
## Requirements
### Requirement: Data-contract tests are explicitly classified
Every test file that intentionally asserts against shipped game content SHALL declare
its class in the source: the first non-blank line of its module docstring (or a leading
`//` comment for JavaScript/TypeScript test files) begins with the exact tag
`Data-contract test:` followed by a one-line rationale, and the file is registered in
the exemption ledger `tools/test_data_freeze.json` with that reason. A test file that is
not so tagged and registered SHALL NOT be treated as a data-contract test by any tool or
document.

#### Scenario: Tag and ledger agree
- **WHEN** the lint gate evaluates a test file registered as a data-contract exemption
- **THEN** the gate requires the `Data-contract test:` tag in the file and passes when
  present with a rationale equal to the registered ledger reason, and fails the run with
  an `untagged-contract` violation when the tag is absent, carries no rationale, or the
  rationale diverges from the ledger reason

#### Scenario: Classification is discoverable by humans
- **WHEN** a developer greps the repository for `Data-contract test:`
- **THEN** every data-contract test file is listed with its rationale, with no behavior
  test appearing in the result

### Requirement: The test-data lint gate blocks shipped-content references
`tools.test_data_lint check` SHALL scan every versioned test source (Python test files
by AST over statically resolvable string expressions — constants, literal-only
concatenation, and all-literal f-strings — plus catalog-symbol references, and
JavaScript/TypeScript test files by string/template-literal scan including literal-only
`+` concatenation) and exit non-zero listing, with stable violation codes,
any flagged test file that is not registered as `contract` or `debt` in the exemption
ledger. The shipped-content token universe SHALL be derived at lint time by importing the
locked content catalogs (`world/lore`, `world/skills`, `world/quests`, `world/maps`
registries, rulebook YAML keys, and their display-prose fields) rather than a hand-edited
list. Display-prose tokens SHALL be complete harvested label/name field values, never
sub-string fragments. Deny-list admission is rule-bound: a token qualifies only as a
schema/structural field name colliding with a catalog key, or a token the scanner proves
present in the non-test production corpus independent of any catalog lookup; every entry
carries a reason and a scanner regression pinning that shipped-key references remain
caught. A separate `quantity-pin` finding class SHALL report assertions that pin
data-derived counts.

#### Scenario: New behavior test hardcodes shipped content
- **WHEN** an unregistered test file contains `healing_potion`, `治療藥水`, or a
  `len(ITEM_REGISTRY) == 58` style pin and the gate runs
- **THEN** the gate exits non-zero and names the file with the offending literals or pin
  sites

#### Scenario: Token universe tracks the data
- **WHEN** a shipped catalog key is renamed or removed in the game-data rework
- **THEN** the gate's token universe follows the catalogs on the next run without any
  manual token-list update

#### Scenario: Synthetic fixtures are not flagged
- **WHEN** a test file references only kit/fixture identifiers (e.g. `t_ember_spray`) and
  synthetic display prose
- **THEN** the gate reports no violation for that file

#### Scenario: Concatenation cannot smuggle a shipped key
- **WHEN** an unregistered test file assembles a shipped identifier at scan time only,
  such as `"healing" + "_potion"` or an all-literal f-string
- **THEN** the gate still flags the file

### Requirement: The exemption ledger is provably shrink-only
The ledger SHALL carry the frozen seed list `seedDebtPaths` (the pre-existing debt
corpus), a `contract` list, and a `debt` list. The gate SHALL fail on any `debt` entry
absent from `seedDebtPaths` (any new debt is a violation), on ledger paths that no
longer exist, and on duplicates or same-path entries under both kinds. Removing a `debt`
entry SHALL be valid only for a file the gate no longer flags, and migration changes
SHALL remove entries in the same commit that makes the file clean. A seeded debt file
legitimately reclassified as a data-contract test SHALL be converted atomically:
removed from `debt` and added once to `contract` (tag + reason) in the same commit;
conversion of a path outside `seedDebtPaths` SHALL be rejected as `new-debt`.

#### Scenario: Re-adding a migrated file fails
- **WHEN** a branch adds a `debt` entry for a file that was not part of the seeded debt
  corpus
- **THEN** the gate exits non-zero with a `new-debt` violation

#### Scenario: Stale ledger entry fails
- **WHEN** a ledger path no longer exists on disk
- **THEN** the gate exits non-zero with a `stale-path` violation

### Requirement: The gate is wired into CI and the authoring rules are documented
The repository CI quality-gate workflow SHALL run
`uv run --locked python -m tools.test_data_lint check` on every branch, and
`AGENTS.md` and `docs/development/evennia-testing-guide.md` SHALL state the authoring
rule: behavior tests resolve game data through the synthetic test-data kit or
file-local synthetic fixtures; only tagged data-contract tests may name shipped
content; assertions SHALL establish mechanics rather than echo fixture or registry
content, and tests that only echo data are replaced rather than multiplied (the
aggregate coverage gate stays a floor, not a target).

#### Scenario: CI blocks a regression
- **WHEN** a pull request adds a behavior test that hardcodes a shipped identifier
- **THEN** the quality-gate workflow fails with the gate's violation output

#### Scenario: Authoring guide answers the new-test question
- **WHEN** a contributor follows the testing guide to add a behavior test that needs a
  potion, skill, or region
- **THEN** the guide directs them to the synthetic kit (or a local synthetic fixture)
  and explains the `Data-contract test:` tag for content-validating tests

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

### Requirement: Skills package behavior tests resolve game data through synthetic fixtures
Behavior tests in the 7 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.
A parser branch whose accepted payload is a closed production vocabulary with no
synthetic substitute MAY keep its positive shipped-value assertion in a
gate-tagged data-contract file instead; the migrated behavior file itself still
carries no shipped-content reference.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated skills tests keep passing unchanged

### Requirement: Quests and maps behavior tests resolve game data through synthetic fixtures
Behavior tests in the 28 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated quest and map tests keep passing unchanged

### Requirement: Combat core behavior tests resolve game data through synthetic fixtures
Behavior tests in the 18 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.
One manifest file whose assertions are exclusively shipped-content rulebook-row
bindings (combat modifier triggers) is exempted by atomic debt-to-contract
conversion under the exemption ledger's seeded-classification rule: it leaves the
`debt` list and joins the registered `contract` list in the same commit, and the
migrated behavior suites carry no shipped-content reference on its behalf.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated behavior files, and
  no freeze-list `debt` entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated combat-core tests keep passing unchanged

### Requirement: Creation progression and lineage behavior tests resolve game data through synthetic fixtures
Behavior tests in the 21 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated creation, progression, and lineage tests keep passing unchanged

### Requirement: Equipment and item behavior tests resolve game data through synthetic fixtures
Behavior tests in the 17 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.
One manifest file whose assertions are exclusively shipped-content buffs.yaml row
bindings (the one-test-per-key correspondence owner) is exempted by atomic
debt-to-contract conversion under the exemption ledger's seeded-classification rule:
it leaves the `debt` list and joins the registered `contract` list in the same commit,
and the migrated behavior suites carry no shipped-content reference on its behalf.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated behavior files, and
  no freeze-list `debt` entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated equipment and item tests keep passing unchanged

### Requirement: Guild shop and service behavior tests resolve game data through synthetic fixtures
Behavior tests in the 16 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated guild, shop, and service tests keep passing unchanged

### Requirement: Knowledge title and view behavior tests resolve game data through synthetic fixtures
Behavior tests in the 12 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated knowledge, title, and view tests keep passing unchanged

### Requirement: Monster and aftermath behavior tests resolve game data through synthetic fixtures
Behavior tests in the 14 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated monster and aftermath tests keep passing unchanged

### Requirement: Party quest delivery and companion behavior tests resolve game data through synthetic fixtures
Behavior tests in the 7 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated party, quest delivery, and companion tests keep passing unchanged

### Requirement: Sexual and status behavior tests resolve game data through synthetic fixtures
Behavior tests in the 14 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated sexual-state and status tests keep passing unchanged

### Requirement: Command and typeclass behavior tests resolve game data through synthetic fixtures
Behavior tests in the 27 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated command and typeclass tests keep passing unchanged

### Requirement: Art prompt and imports behavior tests resolve game data through synthetic fixtures
Behavior tests in the 23 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated art, imports, and prompts tests keep passing unchanged

### Requirement: Ai server and integration behavior tests resolve game data through synthetic fixtures
Behavior tests in the 17 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit or file-local
synthetic fixtures instead of shipped catalog identifiers or shipped display prose, and
SHALL NOT pin quantities derived from shipped content. After the migration, none of the
manifest files is flagged by the test-data lint gate, and every freeze-list debt entry
naming a manifest file is removed. Exemptions owned by other changes under the same
directories are outside this requirement. Converted assertions SHALL establish the
mechanics named by the OpenSpec requirements they annotate; an assertion that merely
echoes synthetic-fixture content is not a passing conversion.

#### Scenario: Area passes the gate with zero debt exemptions
- **WHEN** `uv run --locked python -m tools.test_data_lint check` runs after the migration
- **THEN** no flagged test file remains among this change's migrated files, and no
  freeze-list entry names a migrated file

#### Scenario: Suite is green on synthetic data
- **WHEN** the focused suites for the migrated files run on the retained-database Evennia
  profile (or the Node/Vitest/managed-browser profile for JS-owned files)
- **THEN** every test passes while skills, items, quests, regions, presets, titles, and
  prose resolve exclusively from synthetic catalogs

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated ai, server, and top-level tests keep passing unchanged
