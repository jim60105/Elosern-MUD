# Tasks: align-openspec-cli-1-13-0

## 1. CI pin

- [x] 1.1 Edit `.github/workflows/quality-gate.yml` "Install OpenSpec" step to `npm install --global @fission-ai/openspec@1.13.0`; verify the step YAML parses (`uv run --locked python -c "import yaml; yaml.safe_load(open('.github/workflows/quality-gate.yml'))"`) and no other CLI version literal remains in the workflow.

## 2. Contract-test pin

- [x] 2.1 In `tests/test_quality_gate_contract.py`, add one test method (or extend the existing preflight assertions) asserting the "Install OpenSpec" step's `run` text equals exactly `npm install --global @fission-ai/openspec@1.13.0`, annotated `@covers_requirement("openspec-cli-version-pinning::the-quality-gate-workflow-installs-the-pinned-openspec-cli-version")` (copy the exact slug from the delta heading at implementation time). Scope the assertion to that step's `run` text only — other steps legitimately contain other `@vMAJOR.MINOR.PATCH` action pins. No new test module, no `.github/evennia-shards.json` change.
- [x] 2.2 Confirm the workflow contract tests pass: `uv run --locked python -m unittest tests.test_quality_gate_contract tests.test_browser_verification_contract -v`.

## 3. Purpose backfill (30 specs, Purpose-prose-only edits)

- [ ] 3.1 For each of the 10 art/import specs — `art-asset-lifecycle`, `art-gallery-kind-capabilities`, `art-queue-worker`, `art-stable-key-contract`, `art-staff-commands`, `art-subject-model`, `internal-art-worker`, `import-loader`, `import-reference-example`, `import-schema` — read the spec's requirement headings and text, then replace the `TBD - created by archiving change …` line under `## Purpose` in `openspec/specs/<capability>/spec.md` with one-to-three factual English sentences derived from those requirements; verify each file's diff touches only the Purpose section (`git diff` shows no `### Requirement:` line changed) and `openspec validate <capability> --type spec --strict` reports no WARNING for it.
- [ ] 3.2 For each of the 11 combat/action specs — `action-resolution-pipeline`, `battlefield-action-context`, `buff-handler-integration`, `combat-modifier-table`, `combat-resolution`, `damage-effect-handlers`, `dice-roller`, `effect-context-validation`, `overwhelm-threshold`, `single-shot-resolution`, `targeting-validation` — perform the same read-then-rewrite-and-verify as 3.1.
- [ ] 3.3 For each of the 9 remaining specs — `entity-sex-vocabulary`, `event-log`, `event-log-compression`, `rulebook-schema`, `sexual-transition-rulebook`, `sexual-vocabulary`, `skill-category-registry`, `webclient-frame-resolution`, `import-validation` — perform the same read-then-rewrite-and-verify as 3.1, except `entity-sex-vocabulary`: its `## Purpose` already carries real requirement-derived prose beneath a stale `TBD - created by syncing change entity-sex-field. Update Purpose after archive.` line — delete only the stale TBD line, keep the existing prose, and verify with `openspec validate entity-sex-vocabulary --type spec --strict` (no WARNING before/after diff).

## 4. Integration verification

- [ ] 4.1 Run `openspec validate --all --strict` under the 1.13.0 CLI; verify `Totals: 225 passed, 0 failed` (or the then-current item count with zero failures) with no placeholder-Purpose warnings.
- [ ] 4.2 Run `uv run --locked python -m tools.spec_traceability check` twice: (a) on the feature tree before the new capability is synced into `openspec/specs/` — the ONLY reported errors may be the expected `unknown-requirement-id` entry for the `openspec-cli-version-pinning::…` ID, proving the 30 Purpose edits touched no requirement text or IDs; note that this error makes CI preflight red for this window — expected and temporary, do not chase; (b) as part of archiving, sync the capability into `openspec/specs/` carrying the delta's real `## Purpose` prose into the new main spec (a fresh `TBD` is forbidden — that habit created the 30 placeholders this change removes), after which the check exits 0.
- [ ] 4.3 Keep `git diff --check` clean across the whole change.
