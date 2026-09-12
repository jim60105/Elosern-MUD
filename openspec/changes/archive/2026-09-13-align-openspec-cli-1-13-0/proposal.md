# Proposal: align-openspec-cli-1-13-0

## Why

The CI preflight job installs npm `@fission-ai/openspec@1.6.0` (`.github/workflows/quality-gate.yml` "Install OpenSpec"), while the project has standardized on CLI 1.13.0 locally. Under 1.13.0, `openspec validate --all --strict` fails on 30 specs whose Purpose section is still the `TBD - created by archiving change … Update Purpose after archive.` placeholder that 1.6.0 tolerates. CI must move to 1.13.0, and the 30 placeholder Purposes must be replaced with real prose so strict validation is green under the new pin.

## What Changes

- Move the CI npm pin in `.github/workflows/quality-gate.yml` from `@fission-ai/openspec@1.6.0` to `@fission-ai/openspec@1.13.0` (a literal pin in the install step, matching how the workflow already pins its other global tooling).
- Pin the exact install command with an assertion in the existing workflow contract test (`tests/test_quality_gate_contract.py`), so any future drift away from `1.13.0` fails the top-level suite.
- Backfill real `## Purpose` prose for all 30 main specs currently carrying a `TBD … Update Purpose after archive.` placeholder line, derived from each spec's own requirements, in English (29 read `created by archiving change …`; `entity-sex-vocabulary` reads `created by syncing change …` and already has real prose below the stale line — there the fix is deleting the stale line and keeping the existing prose). Only the Purpose section of each affected `openspec/specs/<capability>/spec.md` is edited — no requirement text or requirement IDs change, keeping `tools.spec_traceability check` green.
- No change to the OpenSpec schema, validation strictness, `scripts/openspec-gates.sh`, or any product-behavior spec.

## Capabilities

### New Capabilities

- `openspec-cli-version-pinning`: the quality-gate workflow installs the OpenSpec CLI at the single project-standardized version (currently `1.13.0`), and a repository contract test pins the exact install command so version drift fails the top-level suite.

### Modified Capabilities

<!-- None. The 30 Purpose backfills edit main-spec Purpose sections directly (a delta `## Purpose` is read only when a capability is created, so it cannot replace an existing placeholder); no requirement text or IDs change, so no requirement-level deltas exist. -->

## Impact

- `.github/workflows/quality-gate.yml` — "Install OpenSpec" step pin `1.6.0` → `1.13.0` (the only CLI install step in any workflow).
- `tests/test_quality_gate_contract.py` — one new assertion on the install step's `run` text (existing module; no `.github/evennia-shards.json` change — top-level tests are not sharded).
- 30 main specs under `openspec/specs/` get Purpose-prose-only edits. Verified list (captured with CLI 1.13.0, `openspec validate --all --strict`, 195 passed / 30 failed of 225 items; each failure is exactly one placeholder-Purpose WARNING):
  1. `action-resolution-pipeline`
  2. `art-asset-lifecycle`
  3. `art-gallery-kind-capabilities`
  4. `art-queue-worker`
  5. `art-stable-key-contract`
  6. `art-staff-commands`
  7. `art-subject-model`
  8. `battlefield-action-context`
  9. `buff-handler-integration`
  10. `combat-modifier-table`
  11. `combat-resolution`
  12. `damage-effect-handlers`
  13. `dice-roller`
  14. `effect-context-validation`
  15. `entity-sex-vocabulary` (stale `syncing`-variant TBD line above already-written prose; fix = delete the stale line)
  16. `event-log`
  17. `event-log-compression`
  18. `import-loader`
  19. `import-reference-example`
  20. `import-schema`
  21. `import-validation`
  22. `internal-art-worker`
  23. `overwhelm-threshold`
  24. `rulebook-schema`
  25. `sexual-transition-rulebook`
  26. `sexual-vocabulary`
  27. `single-shot-resolution`
  28. `skill-category-registry`
  29. `targeting-validation`
  30. `webclient-frame-resolution`
- Gates after this change: `openspec validate --all --strict` under 1.13.0 (CI), `uv run --locked python -m tools.spec_traceability check`, and the top-level contract test suite.
- Existing workflow contract tests (`tests/test_quality_gate_contract.py`, `tests/test_browser_verification_contract.py`) assert step names and other `run` substrings of `quality-gate.yml`; none assert the `Install OpenSpec` command text, so the pin edit breaks nothing until the new assertion is added in the same change.

## Batch

depends-on: none (single change; no sibling changes in this batch)
conflict-note: touches `quality-gate.yml` only in the `Install OpenSpec` step, so overlap with workflow-editing changes is limited to that step; Purpose backfills touch only `## Purpose` sections of the 30 listed specs.
