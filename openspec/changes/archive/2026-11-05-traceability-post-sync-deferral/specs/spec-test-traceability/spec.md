## ADDED Requirements

### Requirement: Pre-archive traceability tolerates only requirements the named change retires

The traceability check SHALL accept an optional active change name. With a name it
SHALL derive retiring identifiers only from that change's `## REMOVED Requirements`
headings and `## RENAMED Requirements` `FROM` lines, tolerate those identifiers when
they are uncovered, and report them separately from uncovered requirements. `ADDED`
and `MODIFIED` requirements MUST NOT retire an identifier. Without a change name the
check MUST stay strict.

#### Scenario: Removed and renamed identifiers retire

- **WHEN** a change's delta spec has a `## REMOVED Requirements` heading for one main requirement and a `## RENAMED Requirements` `FROM` line for another
- **THEN** the check reports exactly those two main identifiers as retiring

#### Scenario: Modified requirements never retire

- **WHEN** a delta spec also declares a `## MODIFIED Requirements` heading for an uncovered main requirement
- **THEN** the check leaves that modified identifier out of the retiring set

#### Scenario: Only retiring gaps pass

- **WHEN** every uncovered indexed requirement is in the named change's retiring set and no verification error exists
- **THEN** the check exits successfully

#### Scenario: Other gaps still fail

- **WHEN** one indexed requirement is retired by the named change, one is declared only as `MODIFIED`, and neither is covered
- **THEN** the check exits nonzero and lists the modified requirement as uncovered

#### Scenario: Retiring identifiers are reported separately

- **WHEN** the check runs with a change name and finds uncovered retiring identifiers
- **THEN** the traceability report carries those identifiers in a field separate from its uncovered identifiers

#### Scenario: No change name stays strict

- **WHEN** the check runs without a change name against a tree whose only uncovered requirement is retired by an active change
- **THEN** the retiring set is empty, that requirement is listed as uncovered, and the check exits nonzero

#### Scenario: Unknown or malformed change name exits 2

- **WHEN** the supplied change name contains characters outside lowercase letters, digits, and hyphens, or names no active change directory
- **THEN** the check exits with status 2 and produces no traceability report

#### Scenario: Change without delta specs retires nothing

- **WHEN** the named active change has no delta spec files
- **THEN** the retiring set is empty

### Requirement: Pre-archive gates forward the change name only to traceability

The contract gate SHALL accept `--change <name>` or `--change=<name>` exactly once
and forward it only to the traceability gate. The pre-archive phase of the archive
gate script SHALL pass a supplied change name to that check. Malformed, empty, or
duplicated change arguments MUST exit 2 before any gate runs.

#### Scenario: Change reaches only the traceability check

- **WHEN** the contract gate selects traceability with `--change <name>` or `--change=<name>`
- **THEN** the traceability invocation receives `--change <name>` and the gate's other invocations remain unchanged

#### Scenario: Malformed change argument is rejected before any gate

- **WHEN** `--change` has no value, has an empty or option-looking value, or is given more than once
- **THEN** the contract gate exits 2 and runs no gate

#### Scenario: Strict check without a change name

- **WHEN** the contract gate selects traceability without `--change`
- **THEN** it invokes the strict traceability check with no change argument

#### Scenario: Archive-gate phases split by sync

- **WHEN** the archive gate script runs its pre-archive phase with a change name and later its post-archive phase
- **THEN** the pre-archive phase runs the traceability check with `--change <change>` and the post-archive phase runs it without one

## MODIFIED Requirements

### Requirement: Every current requirement is associated with a test

The CI verification command MUST fail when any indexed main-spec requirement lacks
a valid, successfully executed test association, reporting every gap in
deterministic order with no baseline, waiver, or allowlist. Pre-archive only,
`check --change <change>` MAY exclude identifiers the named change removes or
renames; that tolerance MUST NOT cover any other requirement or any annotation
error, and the post-sync command MUST omit it.

#### Scenario: Complete traceability passes

- **WHEN** every indexed requirement has at least one valid test annotation with matching successful execution evidence and no verification error exists
- **THEN** verification exits successfully and reports requirement and association totals

#### Scenario: Every gap is reported

- **WHEN** a verification run without retirement tolerance finds one or more indexed requirements with no valid test annotation
- **THEN** verification exits nonzero and lists every uncovered requirement with its spec source location

#### Scenario: Existing test coverage is reused without fabricating tests

- **WHEN** the initial audit finds an existing test whose assertions cover a requirement
- **THEN** that test may be annotated without changing its assertions or behavior

#### Scenario: Named pre-archive retirement is the only tolerated gap

- **WHEN** every uncovered requirement is removed or renamed by the named active change's delta and no annotation error exists
- **THEN** the named check exits successfully, reports the tolerated identifiers separately, and the gap is closed by the archive sync

#### Scenario: Post-sync verification keeps no waiver

- **WHEN** the archive sync has published a change's delta and its retirement of main requirements
- **THEN** the post-sync command runs without a change name and fails for any remaining uncovered requirement
