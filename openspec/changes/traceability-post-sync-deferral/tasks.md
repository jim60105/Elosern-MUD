# Tasks

Retroactive record of work already landed on `master` in `e5c62609`
(`fix(traceability): defer delta coverage to post-sync archive`). Every task below
describes that commit; none remain open.

## 1. Retirement derivation

- [x] 1.1 In `tools/spec_traceability.py`, add `DELTA_SECTION`, `RENAMED_FROM`, and `CHANGE_NAME` and implement `retiring_requirements(repo_root, change)` over `openspec/changes/<change>/specs/*/spec.md`: collect `### Requirement:` names only under `## REMOVED Requirements` and `- FROM:` names only under `## RENAMED Requirements`, qualify each as `<capability>::<normalized-name>`, and raise `ValueError` for a name failing `^[a-z0-9][a-z0-9-]*$` or naming no active change directory. Check: `retiring_requirements` returns only the removed and renamed IDs for a synthetic delta, an empty set for a change without delta specs, and raises for `absent` and `../x`.
- [x] 1.2 Add `retiring: tuple[str, ...] = ()` to `TraceabilityReport`, serialize it as `"retiring"`, add the `retiring: frozenset[str] = frozenset()` parameter to `verify`, report `uncovered - retiring` as uncovered and `uncovered & retiring` as retiring, and print tolerated identifiers under their own console heading. Check: JSON and console list retiring IDs separately while `report.ok` still ignores them.
- [x] 1.3 Add `--change` to the `check` subcommand in `build_parser` and resolve it in `main` before calling `verify`; on `ValueError` print `spec traceability: <message>` to stderr and return 2. Check: `main(["check", "--change", "absent"])` and `main(["check", "--change", "../x"])` return 2; only-retiring gaps return 0 while the plain check returns 1.

## 2. Contract gate forwarding

- [x] 2.1 In `tools/contract_gate.py`, add `_split_change` to remove one `--change <name>` or `--change=<name>` and raise `ValueError` on a missing, empty, option-looking, or duplicated value, add `_traceability(change=None)`, and override only `gates["traceability"]` when a change was parsed; return 2 on `ValueError` before any gate runs. Check: `--change` reaches only the traceability invocation, other gates keep their argv, and malformed forms exit 2 with `subprocess.run` never called.

## 3. Archive gate script

- [x] 3.1 In `scripts/openspec-gates.sh`, run `spec_traceability check --change "${change}"` in the pre-archive `archive` phase when a change name is supplied, and keep the plain strict `check` otherwise and in the post-archive phase. Check: the script's pre-archive traceability gate names the change only when one is given; the post-archive gate never does.

## 4. Contributor policy

- [x] 4.1 In `docs/development/spec-test-traceability.md`, replace stand-in annotation guidance: delta `ADDED` tests carry no annotation, the change records a test-to-delta-requirement/scenario mapping, and annotation plus any missing behavior test happen in the archive stage after the sync with tool-produced identifiers; move retirement/remounting of `REMOVED` or `RENAMED` IDs to the same post-sync stage; document `check --change <change>` as pre-archive-only and the post-sync check as change-free.
- [x] 4.2 In `AGENTS.md`, extend the handoff/archive gate guidance to add `--change <change>` on a feature worktree before archive sync and never after it.

## 5. Tests and handoff

- [x] 5.1 Extend `tests/test_spec_traceability.py` with `PreArchiveRetirementTests` covering: retirement from REMOVED and RENAMED FROM only; retiring tolerated while a modified gap still fails; strict output without `--change`; CLI success when only retiring IDs are uncovered (strict run returns 1); a change without delta specs retiring nothing; and exit 2 for unknown and unsafe change names. Leave every one of these tests unannotated until the archive sync.
- [x] 5.2 Extend `tests/test_contract_gate.py` with `test_change_is_forwarded_only_to_the_traceability_check`, `test_traceability_without_change_stays_strict`, and `test_malformed_change_is_rejected_before_anything_runs`. Leave them unannotated until the archive sync.
- [x] 5.3 Record the test-to-delta-requirement handoff in `design.md` §D6 and annotate these tests only after the archive sync with the canonical IDs from `uv run --locked python -m tools.spec_traceability list`. Do not add `covers_requirement` decorators in this proposal.
- [x] 5.4 Run `uv run --locked openspec validate traceability-post-sync-deferral --strict` and `uv run --locked python -m tools.spec_traceability check --change traceability-post-sync-deferral`. Check: both exit 0; the change's retiring set is empty because the delta has no REMOVED or RENAMED entries.
