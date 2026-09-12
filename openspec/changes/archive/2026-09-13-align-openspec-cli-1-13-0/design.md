# Design: align-openspec-cli-1-13-0

## Context

See proposal.md — Why. Current state, verified on this machine with CLI 1.13.0:

- CI: `.github/workflows/quality-gate.yml` "Install OpenSpec" step runs `npm install --global @fission-ai/openspec@1.6.0`; the "Validate OpenSpec" step then runs bare `openspec validate --all --strict`. This is the only CLI install step in any workflow.
- Under 1.13.0 the tree validates 195 passed / 30 failed; every failure is exactly one `WARNING overview: Purpose section is still a placeholder`, failing `--strict`. Under 1.6.0 the same tree passes.
- No repository test asserts the text of the `Install OpenSpec` step today (checked `tests/test_quality_gate_contract.py`, `test_browser_verification_contract.py`, `test_evennia_test_optimization_contract.py`, `test_frontend_toolchain_contract.py`, `test_test_data_lint.py`); no docs mention the pinned version outside archived change artifacts.
- `scripts/openspec-gates.sh` calls `uv run --locked openspec …`, and `uv.lock` contains no `openspec` entry, so the invocation falls through to the `openspec` binary on `PATH`. Out of scope for this change (see Non-Goals).

## Goals / Non-Goals

**Goals:**
- CI installs and validates with CLI 1.13.0.
- Strict validation green under 1.13.0 (the 30 placeholder Purposes backfilled with real prose).
- The exact install command pinned by a committed test so a future edit away from `1.13.0` fails loudly.

**Non-Goals:**
- Changing the OpenSpec schema, artifact layout, or validation strictness.
- Any `scripts/openspec-gates.sh` change or a repo-wide version-declaration mechanism (pin file, gate-script assertion, dedicated drift suite). The requirement is the CI pin; drift protection is one assertion in the existing workflow contract test.
- Touching the `generatedBy: "1.6.0"` metadata in `.agents/skills/openspec-*/SKILL.md` — provenance stamps of the older generator, not version pins.

## Decisions

### D1: Literal `1.13.0` pin in the workflow install step

`npm install --global @fission-ai/openspec@1.13.0`, replacing the `1.6.0` literal in place. This mirrors how the workflow already pins everything else (setup-uv action versions, etc.) and is the smallest change that satisfies "CI on the same version". Bumping later is one workflow edit plus the test's expected string.

### D2: Drift prevention is one assertion in the existing contract test

`tests/test_quality_gate_contract.py` already loads `quality-gate.yml` with `yaml.safe_load` and asserts exact `run` text for other preflight steps (e.g. the observability lint step). A new assertion pins the `Install OpenSpec` step's `run` to exactly `npm install --global @fission-ai/openspec@1.13.0`. No new test module, no new capability plumbing beyond the requirement itself, no shard-manifest change (top-level `tests/` is not sharded).

Traceability: the new capability's requirement is annotated on this assertion's test method with `@covers_requirement("openspec-cli-version-pinning::the-quality-gate-workflow-installs-the-pinned-openspec-cli-version")` (the implementer copies the exact slug produced by the delta heading). While the capability is not yet synced into `openspec/specs/`, `tools.spec_traceability check` reports this ID as `unknown-requirement-id` — an expected, temporary red window between this change landing and its archive sync; CI reaches green when archiving syncs the capability. When syncing, the new main spec's `## Purpose` MUST carry the delta's real prose — the sync habit of writing `TBD` is what produced the 30 placeholders this change removes and MUST NOT be followed.

### D3: Purpose backfill edits main specs directly

1.13.0's warning states the constraint: a delta `## Purpose` is read only when the capability is created — it cannot replace an existing placeholder. Therefore each of the 30 specs gets its `## Purpose` section rewritten in place in `openspec/specs/<capability>/spec.md`, with prose derived from that spec's own requirement headings and text (English, one to three sentences, factual, no invented capabilities). One variant: `entity-sex-vocabulary` carries the stale `TBD - created by syncing …` line *above* already-written, requirement-derived prose — there the fix is deleting the stale line and keeping the existing prose, not rewriting it. No `### Requirement:` line is added, removed, renamed, or reworded, so requirement identifiers the traceability tool indexes are untouched and `tools.spec_traceability check` stays green across the backfill.

Placeholder prevention going forward: 1.13.0 itself fails strict validation on any placeholder Purpose, and CI now runs 1.13.0 — the version alignment is the prevention mechanism; no extra tooling is added.

## Risks / Tradeoffs

- [1.13.0 may format or interpret artifacts differently than 1.6.0 for in-flight changes] → Verified on this machine: `openspec validate --all --strict` under 1.13.0 passes every item except the 30 placeholder-Purpose specs (195/225; remaining failures are the known warnings). No other breakage observed.
- [A developer's PATH `openspec` (used by `scripts/openspec-gates.sh`) may differ from CI's pinned version] → Accepted: that ambiguity predates this change and the local gate is advisory; CI's pinned validation stays authoritative. If it bites, it gets its own change.
- [Purpose prose could drift from what requirements actually say] → Each Purpose is derived from that spec's requirement list (tasks require reading requirements first); reviewers can diff Purpose text against headings; `--strict` plus `tools.spec_traceability check` keep structure and coverage honest.
- [Editing 30 spec files touches many files at once] → Edits are confined to `## Purpose` sections; the traceability tool indexes only requirement headings, so gate risk is nil; `validate --all --strict` is the mechanical check.

## Migration Plan

Ordinary change flow: implement on the feature branch, gates run in CI under the new pin, archive syncs the capability and closes the traceability red window. Rollback = revert the commit; nothing persists state.

## Open Questions

None.
