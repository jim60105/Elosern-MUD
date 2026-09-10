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
