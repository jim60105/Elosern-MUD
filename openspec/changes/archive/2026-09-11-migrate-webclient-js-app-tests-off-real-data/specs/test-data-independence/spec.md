## ADDED Requirements

### Requirement: Webclient javascript tests resolve game data through synthetic fixtures
Behavior tests in the 22 test files enumerated in this change's migration
manifest SHALL exercise game mechanics through the synthetic test-data kit, file-local
synthetic fixtures, production-owned wire constants, or values read from the committed
payload fixture objects at runtime, instead of restating shipped catalog identifiers or
shipped display prose in test source, and
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
- **THEN** every test passes while the payload catalogs the tests author resolve from
  synthetic content, and any shipped content a test still renders arrives only through a
  committed fixture object the test reads (never a literal in test source)

#### Scenario: Data rework cannot break the area again
- **WHEN** shipped identifiers, display prose, or catalog sizes change in the game-data
  rework
- **THEN** the migrated webclient javascript tests keep passing unchanged

