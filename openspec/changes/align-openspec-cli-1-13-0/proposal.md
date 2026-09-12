# Proposal: align-openspec-cli-1-13-0

## Why

The repository validates OpenSpec artifacts through two entry points that silently disagree about the CLI version: the CI preflight job installs npm `@fission-ai/openspec@1.6.0`, while `scripts/openspec-gates.sh` calls `uv run --locked openspec`, which resolves nothing from the locked uv environment (the venv contains no `openspec` package — the name falls through to whatever `openspec` is on `PATH`, i.e. the developer's global install). Locally that resolves to 1.13.0, where `openspec validate --all --strict` fails on 30 specs whose Purpose section is still the `TBD - created by archiving change … Update Purpose after archive.` placeholder that 1.6.0 tolerates. The team has standardized on 1.13.0; CI must move to it, and the 30 placeholder Purposes must be replaced with real prose so strict validation is green under the version we actually use.

## What Changes

- Move the CI npm pin from `@fission-ai/openspec@1.6.0` to the `1.13.0` declared in a new pin file, by deriving the install step's version from `openspec/CLI_VERSION`, in `.github/workflows/quality-gate.yml`.
- Establish one authoritative version-management story (detailed in design.md): a single machine-readable pin file `openspec/CLI_VERSION` (contents `1.13.0`) consumed by the CI install step, and a version-match assertion in `scripts/openspec-gates.sh` so the archive gate fails when the invoked CLI reports a version other than the pin. This closes the `uv run --locked openspec` ambiguity without adding a Python-side dependency.
- Add a top-level repository contract test that keeps the pin file, the workflow install command, and the gate-script version assertion in lockstep (drift prevention).
- Backfill real `## Purpose` prose for all 30 main specs currently carrying a `TBD … Update Purpose after archive.` placeholder line, derived from each spec's own requirements, in English (29 read `created by archiving change …`; `entity-sex-vocabulary` reads `created by syncing change …` and already has real prose below the stale line — there the fix is deleting the stale line and keeping the existing prose). Only the Purpose section of each affected `openspec/specs/<capability>/spec.md` is edited — no requirement text or requirement IDs change, keeping `tools.spec_traceability check` green.
- No change to the OpenSpec schema, validation strictness, or any product-behavior spec.

## Capabilities

### New Capabilities

- `openspec-cli-version-pinning`: a single authoritative OpenSpec CLI version declaration consumed by every validation entry point (CI install step, archive gate script), with a mismatch-fails-the-gate contract and a repository contract test that detects pin drift.

### Modified Capabilities

<!-- None. The 30 Purpose backfills edit main-spec Purpose sections directly (a delta `## Purpose` is read only when a capability is created, so it cannot replace an existing placeholder); no requirement text or IDs change, so no requirement-level deltas exist. -->

## Impact

- `.github/workflows/quality-gate.yml` — "Install OpenSpec" step (pin → consumed from `openspec/CLI_VERSION`).
- `scripts/openspec-gates.sh` — pre-flight CLI version assertion against the pin.
- New: `openspec/CLI_VERSION` (single source of truth), `tests/test_openspec_cli_version_contract.py` (drift-prevention contract test, owned by the top-level test entry point; no `.github/evennia-shards.json` change).
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
- Gates after this change: `openspec validate --all --strict` under the pinned 1.13.0 (CI + archive gate), `uv run --locked python -m tools.spec_traceability check`, and the top-level contract test suite (which picks up the new pin-drift test automatically via `unittest discover -s tests`).
- Existing workflow contract tests (`tests/test_quality_gate_contract.py`, `tests/test_browser_verification_contract.py`) assert step names and other `run` substrings of `quality-gate.yml`; none assert the `Install OpenSpec` command text, so the pin edit does not break them.

## Batch

depends-on: none (single change; no sibling changes in this batch)
conflict-note: touches `quality-gate.yml` only in the `Install OpenSpec` step, so overlap with workflow-editing changes is limited to that step; Purpose backfills touch only `## Purpose` sections of the 30 listed specs.
