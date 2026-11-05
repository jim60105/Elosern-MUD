# Design

## Context

This change records work that already landed on `master` in
`e5c62609` (`fix(traceability): defer delta coverage to post-sync archive`).
The behavior is therefore fixed; the decisions below document what that commit
chose and why, not an open implementation plan.

- `tools/spec_traceability.py` indexes only direct capability specs under
  `openspec/specs/`. `parse_requirements` returns requirement and parse errors;
  `verify(repo_root, evidence_path=None)` assembles a `TraceabilityReport` with
  `covered`, `uncovered`, and `errors`.
- `tools/contract_gate.py` exposes `GATES`, a `subprocess`-based `_run` closure, and
  a `main` that selects gates by name and runs every selected gate even after a
  failure.
- `scripts/openspec-gates.sh` runs a pre-archive `archive` phase and a separate
  post-archive phase; the pre-archive phase previously ran the strict check with no
  change argument.
- `docs/development/spec-test-traceability.md` previously instructed implementations
  to annotate delta-requirement tests with the closest current requirement as a
  stand-in and to remount it at archive time.

## Goals / Non-Goals

**Goals:** make the pre-archive traceability check honest about requirements a change
is retiring; make the tolerance opt-in and change-scoped; stop false stand-in
annotations and move annotation to a point where canonical identifiers exist.

**Non-Goals:** changing identifier normalization; tolerating `ADDED` or `MODIFIED`
requirements before sync; keeping any post-sync waiver, allowlist, or baseline;
retiring identifiers without an archive sync; changing the evidence mechanism; any
game behavior, data, or main-spec content.

## Decisions

### D1. Retirement is derived only from REMOVED headings and RENAMED FROM lines

`retiring_requirements(repo_root, change)` walks every
`openspec/changes/<change>/specs/*/spec.md`. It tracks the current delta section with
`DELTA_SECTION` (`## ADDED|MODIFIED|REMOVED|RENAMED Requirements`). In a `REMOVED`
section it collects `### Requirement:` headings; in a `RENAMED` section it collects
`- FROM: \`### Requirement: ...\`` lines via `RENAMED_FROM`. Each collected name is
normalized and qualified as `<capability>::<slug>`, matching main-spec identifiers.
`ADDED` and `MODIFIED` sections yield nothing.

Rationale: only a REMOVED heading or a RENAMED source name identifies a main-spec
requirement that the sync will delete. Anything else would tolerate a genuine gap.

### D2. The tolerance is opt-in and reported separately

`verify()` gains `retiring: frozenset[str] = frozenset()`. It computes
`uncovered = identifiers - covered`, reports `uncovered - retiring` as `uncovered`,
and `uncovered & retiring` as `retiring`. `TraceabilityReport.retiring` defaults to
`()`, and the JSON report gains a `"retiring"` list. Console output prints tolerated
identifiers under their own heading after the uncovered list.

`report.ok` stays `not errors and not uncovered`, so tolerated identifiers do not
fail the run and any annotation error still does. No other gate, count, or ordering
changes.

### D3. Malformed and unknown change names exit 2 before any gate

`retiring_requirements` validates the name with `CHANGE_NAME`
(`^[a-z0-9][a-z0-9-]*$`) and requires the active change directory to exist, raising
`ValueError` otherwise. `spec_traceability.main` catches that, prints the message to
stderr, and returns 2 without a report. This prevents path traversal and keeps an
unknown or archived change from silently tolerating nothing.

`contract_gate._split_change` parses `--change <name>` and `--change=<name>` once,
rejecting a missing value, empty value, option-looking value, or duplicate before any
gate is selected or run; `main` returns 2 on `ValueError`. The parsed name replaces
only `gates["traceability"]` with `_traceability(change)`; other gate callables and
the selection/unknown-gate logic are untouched.

### D4. The post-sync check omits `--change`

`scripts/openspec-gates.sh` passes `--change "${change}"` only in the pre-archive
`archive` phase when a name was supplied. The post-archive phase and the CI preflight
run the plain `check`, which has an empty retiring set and therefore remains the
authoritative no-waiver gate. `AGENTS.md` states the same rule: pass `--change` on a
feature worktree before sync, never after.

### D5. Delta-requirement tests stay unannotated until the archive sync

`ADDED` requirements have no canonical identifier before the sync, so any annotation
written during implementation must borrow an identifier and is therefore a false
claim. The documented policy replaces stand-in annotation with a handoff mapping:

1. Implementation writes the behavior test and leaves it unannotated.
2. The change records the test-to-delta-requirement/scenario mapping.
3. After the archive sync, the tool lists canonical identifiers, and the archive
   stage adds the annotation with the real identifier, remounts tests whose retired
   identifier disappeared, and adds any missing behavior test.

This is recorded as contributor policy in
`docs/development/spec-test-traceability.md` and `AGENTS.md` rather than as a new
requirement: no executable mechanism enforces it, and a requirement must be
test-establishable. The retirement mechanism in D1–D4 is the testable part.

### D6. Test handoff mapping

The tests added by `e5c62609` stay unannotated in this proposal. After the archive
sync publishes the two new requirements, annotate them with the tool-produced
identifiers as follows.

| Test (file::test) | Delta requirement / scenario |
| --- | --- |
| `tests/test_spec_traceability.py::PreArchiveRetirementTests.test_only_removed_and_renamed_from_requirements_retire` | `Pre-archive traceability tolerates only requirements the named change retires` / Removed and renamed identifiers retire; Modified requirements never retire |
| `tests/test_spec_traceability.py::PreArchiveRetirementTests.test_retiring_requirements_are_tolerated_but_others_still_fail` | same / Other gaps still fail; Retiring identifiers are reported separately |
| `tests/test_spec_traceability.py::PreArchiveRetirementTests.test_check_without_change_stays_strict` | same / No change name stays strict |
| `tests/test_spec_traceability.py::PreArchiveRetirementTests.test_cli_change_passes_when_only_retiring_requirements_are_uncovered` | same / Only retiring gaps pass; No change name stays strict |
| `tests/test_spec_traceability.py::PreArchiveRetirementTests.test_change_without_delta_specs_retires_nothing` | same / Change without delta specs retires nothing |
| `tests/test_spec_traceability.py::PreArchiveRetirementTests.test_cli_rejects_unknown_or_unsafe_change_names` | same / Unknown or malformed change name exits 2 |
| `tests/test_contract_gate.py::ContractGateTests.test_change_is_forwarded_only_to_the_traceability_check` | `Pre-archive gates forward the change name only to traceability` / Change reaches only the traceability check |
| `tests/test_contract_gate.py::ContractGateTests.test_traceability_without_change_stays_strict` | same / Strict check without a change name |
| `tests/test_contract_gate.py::ContractGateTests.test_malformed_change_is_rejected_before_anything_runs` | same / Malformed change argument is rejected before any gate |

The exact retiring set in `test_only_removed_and_renamed_from_requirements_retire`
establishes that the `MODIFIED` requirement is excluded; the separate-report scenario
is established by the `report.retiring` and `report.uncovered` assertions in
`test_retiring_requirements_are_tolerated_but_others_still_fail`.
`Every current requirement is associated with a test` keeps its existing annotation
on
`tests/test_spec_traceability.py::RuntimeEvidenceTests.test_matching_successful_evidence_counts`.

Accepted coverage gaps in this record, stated instead of claimed as tested: no test
exercises an `ADDED`-only delta, the console heading or JSON `"retiring"` key, a
second gate running alongside `--change`, the shell phase split, or the rejected-name
diagnostic; rejection tests assert only the exit status and that no gate ran. The
shell phase split is exercised by the `os-archive` workflow's
`scripts/openspec-gates.sh archive|post-archive` invocation, not by the CI workflows
in this repository. Adding assertions for these points is archive-stage work of the
same kind as the deferred annotations in D5, not a precondition of this record.

## Risks / Trade-offs

- [The retiring set can hide a real gap if a delta mislabels a requirement as REMOVED] -> the tolerance is limited to the named change, listed in output, and the post-sync check is strict.
- [Two new requirements are uncovered until annotation after the archive sync] -> intentional per D5; the archive stage must annotate with canonical IDs and add any missing test.
- [The pre-archive gate is weaker than the post-sync gate] -> `--change` is never passed after sync, and CI preflight keeps the strict check.

## Verification

Run `uv run --locked openspec validate traceability-post-sync-deferral --strict` and
`uv run --locked python -m tools.spec_traceability check --change traceability-post-sync-deferral`.
The change has no `REMOVED` or `RENAMED` delta entries, so the retiring set is empty
and only pre-existing main-spec coverage matters. After archive sync, annotate per
D6 and rerun the strict check.
