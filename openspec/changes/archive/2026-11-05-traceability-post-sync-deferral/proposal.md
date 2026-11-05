# Proposal

## Why

The traceability guide told implementations to annotate tests for requirements that
exist only in a change's delta with the "closest current requirement" as a stand-in.
Those claims were false, and the archive sync often moved them onto the wrong
requirement. Separately, a change that removes or renames a requirement deleted the
requirement's tests while the requirement itself stayed in `openspec/specs/` until the
sync, so the pre-archive check reported a gap that the change was already resolving.

## What Changes

- Add retirement derivation to the traceability tool: only `## REMOVED Requirements`
  headings and `## RENAMED Requirements` `- FROM:` lines of an active change's delta
  specs retire main-spec IDs; `ADDED` and `MODIFIED` never do.
- Add an opt-in pre-archive tolerance, `spec_traceability check --change <change>`:
  uncovered retiring IDs are excluded from the failure set and reported separately,
  every other uncovered requirement and every annotation error still fails, and the
  check without `--change` stays strict.
- Reject a malformed or unknown change name with exit status 2 before any report is
  produced.
- Forward the change name from `contract_gate --change <change>` to the traceability
  gate only, rejecting malformed or duplicated arguments before any gate runs, and
  forward it from the pre-archive phase of `scripts/openspec-gates.sh` when supplied.
- Document the contributor policy: delta-requirement tests carry no stand-in
  annotation, the change hands off a test-to-requirement mapping, and annotation,
  remounting of retired IDs, and any missing behavior test happen in the archive
  stage after the sync with tool-produced identifiers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `spec-test-traceability`: add the pre-archive retirement tolerance and gate
  forwarding requirements, and narrow the "Every current requirement is associated
  with a test" requirement to name the pre-archive exception while keeping the
  post-sync check strict.

## Impact

Files: `tools/spec_traceability.py` (delta parsing, report field, CLI option),
`tools/contract_gate.py` (argument parsing and gate forwarding),
`scripts/openspec-gates.sh` (pre-archive gate invocation),
`docs/development/spec-test-traceability.md` and `AGENTS.md` (contributor policy and
pre-archive command guidance). New contract tests live in
`tests/test_spec_traceability.py::PreArchiveRetirementTests` and
`tests/test_contract_gate.py::ContractGateTests`. No production game behavior, data,
or main-spec files are changed by this change.

This is a retroactive record: the implementation, documentation, and tests already
landed on `master` in `e5c62609`. The artifacts describe that work and are checked
off; no new code is written.
