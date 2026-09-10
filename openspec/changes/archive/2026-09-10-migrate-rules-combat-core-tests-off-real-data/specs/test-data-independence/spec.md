## ADDED Requirements

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

