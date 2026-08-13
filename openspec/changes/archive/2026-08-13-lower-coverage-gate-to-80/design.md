## Context

The quality gate enforces aggregate branch coverage of at least 90% in two
places: `pyproject.toml` (`[tool.coverage.report] fail_under = 90`) and the
"Enforce aggregate coverage threshold" step in `.github/workflows/quality-gate.yml`
(`coverage report --fail-under=90`). Historical evidence in the archived
`stabilize-and-accelerate-quality-gate` change shows the last green run sat at
exactly 90% with zero headroom, so every feature change that adds code must
first push the combined report back across the line before CI can pass. The
gate is meant to catch coverage regressions, not to demand near-exhaustive
branch coverage as a prerequisite for gameplay work.

This change lowers the enforced hard gate to 80% and keeps 90% as a documented
target. 80% is a common regression-floor convention that leaves roughly ten
points of headroom while still failing CI on a genuine, material coverage
collapse. The current contract (specs, contract tests, docs, AGENTS.md) pins
"90%" in eight live files plus three main specs; this design enumerates every
edit and leaves historical records untouched.

## Goals / Non-Goals

**Goals:**

- Enforce the aggregate branch-coverage hard gate at 80% in both the workflow
  and the project coverage configuration, with local and CI runs agreeing.
- Keep 90% visible as the project's aspirational coverage target in
  documentation and in the spec contract, explicitly unenforced by CI.
- Keep all other quality-gate semantics byte-for-byte identical: coverage
  sources and roots, omission policy, evidence verification, aggregation
  missing-artifact failures, parallel/browser profiles, and Codecov
  publication.

**Non-Goals:**

- Changing coverage scope, root set, or omission policy.
- Changing requirement-level traceability or its evidence pipeline.
- Editing historical records (archived OpenSpec changes, dated
  `docs/superpowers/specs/*.md` design documents). They describe the gate as it
  existed at their design time and remain historical evidence.
- Introducing a coverage-trend or differential-gate mechanism.

## Decisions

### D-1. Hard gate value is 80%, enforced in both configuration and workflow

`pyproject.toml` changes `fail_under = 90` → `fail_under = 80`, and the gate
job step changes `--fail-under=90` → `--fail-under=80`. Both are updated
together because they serve different readers: the config file makes any local
`coverage report` fail identically to CI, and the workflow flag pins the gate
explicitly at the enforcement step, which is what the existing contract tests
assert.

Alternatives considered:

- **85%** — still within a few points of the measured aggregate and preserves
  most of the no-headroom problem; rejected.
- **75% or lower** — weakens the regression signal to the point where a
  meaningful collapse could pass; rejected.
- **Config-only enforcement** (drop the workflow flag) — technically
  redundant since `coverage report` reads `fail_under` from config, but it
  changes the contract tests and the step's explicit intent; rejected for this
  small change.

### D-2. 90% remains a documented target, never enforced

The spec contract (`spec-test-traceability` "Continuous integration enforces
both quality dimensions") states the workflow fails below 80% **and** that the
project SHALL target 90% as a documented, unenforced goal. The target lives in
`docs/development/spec-test-traceability.md` (the canonical coverage-commands
doc, next to the `--fail-under=80` command) and `AGENTS.md` (the agent-facing
project guide). Wording must make the asymmetry explicit: "the hard gate is
80%; the project targets 90%". A contract test (see D-3) asserts both numbers
in their respective homes so neither drifts.

Alternatives considered:

- **Record the target only in prose, outside the spec** — loses the contract
  guarantee that the target stays documented; rejected.
- **Keep 90% enforced but add a waiver mechanism** — the traceability contract
  explicitly forbids waivers/allowlists for the requirement gate, and a
  coverage waiver would be the same anti-pattern; rejected.

### D-3. Contract tests pin the gate and the target

`tests/test_quality_gate_contract.py` updates the assertions that currently
pin `fail_under == 90` in `pyproject.toml` and `--fail-under=90` in the
workflow, and `tests/test_evennia_test_optimization_contract.py` updates its
`fail-under=90` assertion. `tests/test_browser_verification_contract.py`
extends one of its tests annotated for
`webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps`
to assert the "Enforce aggregate coverage threshold" step runs
`--fail-under=80`, so the browser-verification requirement's own evidence pins
the new numeric contract directly. A new assertion (or assertions) in
`test_quality_gate_contract.py` verifies that the documentation states the 90%
target while the enforced numbers are 80% — this is the substantively matching
test for the spec's "Coverage target remains visible without enforcement"
scenario. These tests already carry `covers_requirement` annotations for the
amended requirements; no annotation changes are needed because requirement IDs
derive from requirement names, which do not change.

### D-4. Scope of edited references

The grep-verified inventory of live "90% coverage gate" references:

| File | Change |
| --- | --- |
| `.github/workflows/quality-gate.yml` | `--fail-under=90` → `--fail-under=80` |
| `pyproject.toml` | `fail_under = 90` → `fail_under = 80` |
| `tests/test_quality_gate_contract.py` | pin `--fail-under=80`, `fail_under == 80`, 90% target doc |
| `tests/test_evennia_test_optimization_contract.py` | `fail-under=90` → `fail-under=80` |
| `tests/test_browser_verification_contract.py` | assert `--fail-under=80` in the gate step under the browser-verification annotation |
| `AGENTS.md` | gate wording → 80% hard gate, 90% target |
| `docs/development/spec-test-traceability.md` | command and gate wording → 80% gate, 90% target |
| `docs/development/evennia-testing-guide.md` | zh-TW prose → 80% gate (preserve zh-TW style) |
| `docs/development/evennia-test-performance.md` | gate wording → 80% |
| `openspec/specs/spec-test-traceability/spec.md` | amended by delta spec |
| `openspec/specs/evennia-test-optimization/spec.md` | amended by delta spec |
| `openspec/specs/webclient-browser-verification/spec.md` | amended by delta spec |

Explicitly **not** edited: `openspec/changes/archive/` (historical evidence per
AGENTS.md) and `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` (a
dated design record describing "the existing 90% branch-coverage gate" at its
design time).

### D-5. Everything else about the gate stays identical

Coverage roots (`commands`, `server`, `typeclasses`, `web`, `world`), branch
measurement, the `*/tests/*` omission, three-entry-point combination,
missing-artifact failure behavior, coverage-root verification, Codecov XML
publication, browser sharding, and the parallel profile are all untouched.
Verification for this change is therefore the top-level contract suite
(`uv run --locked python -m unittest discover -s tests -t .`), the spec
traceability check, and `openspec validate --strict`; a full coverage re-run is
not needed because no production code changes.

## Risks / Trade-offs

- [Configuration and workflow drift out of sync] → the contract test asserts
  both numbers every CI run; a change to one side without the other fails the
  top-level suite.
- [Readers mistake the 90% target for an enforced gate] → all wording states
  the asymmetry explicitly ("hard gate 80%, target 90%"), and the spec's
  scenario pins the documentation requirement.
- [A regression between 80% and 90% now passes CI] → accepted trade-off; this
  is precisely the headroom being purchased. The Codecov badge still exposes
  the trend publicly, the target is documented, and anything below 80% still
  fails hard.
- [A stray "90%" reference survives the edit] → tasks include a final
  repo-wide grep over live files (`openspec/changes/archive/` and
  `docs/superpowers/specs/` excepted) plus `git diff --check`.

## Migration Plan

Single commit; no data or schema migration. Rollback is reverting the commit,
which restores `fail_under = 90` and `--fail-under=90` together with the
contract tests and specs. Because the project is unreleased with zero users, no
compatibility layer is needed.

## Open Questions

None.
