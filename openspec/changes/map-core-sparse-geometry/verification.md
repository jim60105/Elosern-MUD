# Planning verification

These are observed planning-gate results, not claims of implemented map-editor behavior.

## Change validation

All twenty new changes pass `openspec validate <change> --strict` with no warnings. The acceptance-only change reports the expected informational skip_specs message. The first strict run detected omitted inherited scenario titles in five ownership deltas. Those deltas were corrected to retain every inherited scenario title while expressing the approved new ownership/mechanism and avoiding production count/coordinate/prose approval pins; the five repaired changes then passed. No validation flag was weakened.

## Repository contract gate

`uv run --locked python -m tools.contract_gate` passed.

- Traceability, 2581 requirements and 11660 associations; 2581 covered, zero uncovered/errors.
- Observability, 801 scanned, zero frozen files and zero violations.
- Test-data lint, 1454 scanned and zero violations. The existing runtime-dependent world.lore.sync import is reported as skipped by that linter.
- Manifests passed.
- Eighteen repository contract tests passed in 1.081 seconds.

Active change requirements are excluded from the current main-spec traceability index. This passing gate does not claim implementation coverage for new proposals; each design names future substantive discoverable evidence and requires canonical IDs at effective-spec cutover.

## Repository-wide strict gate blocker

`openspec validate --all --strict` returned nonzero, with 414 passing and six failing items. Every new proposal passed. The six failures are unchanged current main-spec requirement bodies longer than 500 characters:

| Main capability | Requirement index reported by CLI |
| --- | --- |
| canonical-wilderness-destination | requirements[0] |
| map-districts | requirements[2] |
| map-knowledge | requirements[1] |
| village-ciaran-map | requirements[0] |
| wilderness-map-provider | requirements[1] |
| wilderness-terrain | requirements[0] |

These warnings are failures and are not waived. The proposal-only assignment permits commits only under each new change directory and forbids main-spec edits/archive, so changing those current main specs is outside the allowed floor. Applicable future deltas already shorten affected bodies, but they cannot make current main specs pass before archive. Remaining main-spec shape repair is a separate prerequisite for a globally green strict gate. The flag remains strict.

## Writing-style gate

The writing-style linter checked 116 Markdown artifacts with zero hard errors. Its warning categories were reviewed. Metadata labels such as depends-on/code-conflicts and implementation-owner labels use intentional machine-readable/technical colons; lore mirroring is the actual registry synchronization operation, not an emotional metaphor. Retained source-independent scenario text is not a claim of changed content.

## Not executed

No implementation builds, feature tests, game/browser smoke runs, package installation, archives, branches or worktrees were created during planning. The eighteen contract tests above ran solely inside the explicitly required planning contract gate. Full managed browser and complete traceability evidence remain CI-owned after implementation.
