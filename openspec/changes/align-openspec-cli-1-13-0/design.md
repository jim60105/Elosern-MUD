# Design: align-openspec-cli-1-13-0

## Context

See proposal.md — Why. Current state, verified on this machine with CLI 1.13.0:

- CI: `.github/workflows/quality-gate.yml` "Install OpenSpec" step runs `npm install --global @fission-ai/openspec@1.6.0`; the "Validate OpenSpec" step then runs bare `openspec validate --all --strict`.
- Archive gate: `scripts/openspec-gates.sh` runs `uv run --locked openspec validate …`. The locked uv environment contains **no** `openspec` package (`uv.lock` has no entry; `.venv/bin/openspec` does not exist), so `uv run` simply falls through to the `openspec` binary found on `PATH` — whatever global Node install the developer happens to have. The `--locked` flag creates a false impression that the CLI version is locked.
- Under 1.13.0 the tree validates 195 passed / 30 failed; every failure is exactly one `WARNING overview: Purpose section is still a placeholder`, failing `--strict`. Under 1.6.0 the same tree passes.
- No repository test asserts the text of the `Install OpenSpec` step (checked `tests/test_quality_gate_contract.py`, `test_browser_verification_contract.py`, `test_evennia_test_optimization_contract.py`, `test_frontend_toolchain_contract.py`, `test_test_data_lint.py`); no docs mention the pinned version outside archived change artifacts.

## Goals / Non-Goals

**Goals:**
- One authoritative CLI version declaration, consumed by every validation entry point.
- Any entry point invoking a CLI whose version differs from the pin must fail loudly, not silently disagree.
- Strict validation green under the pinned 1.13.0.

**Non-Goals:**
- Changing the OpenSpec schema, artifact layout, or validation strictness.
- Adding an npm/package.json-managed devDependency for the CLI (the repo's Node side is pnpm-locked for the webclient toolchain; the CLI is a build-time global, matching how CI already installs it).
- Touching the `generatedBy: "1.6.0"` metadata in `.agents/skills/openspec-*/SKILL.md` — provenance stamps of the older generator, not version pins.
- Splitting work across changes: the pin work is ~1 hour, the 30 Purpose backfills are mechanical reads-plus-two-sentences each; the whole set fits one workday, so this stays a single change.

## Decisions

### D1: Authoritative version story — a `openspec/CLI_VERSION` pin file

Single file `openspec/CLI_VERSION`, contents exactly `1.13.0\n`, mirroring the repo's existing `.python-version` pattern (the workflow already does `uv python install "$(<.python-version)"`).

- CI install step becomes `npm install --global "@fission-ai/openspec@$(<openspec/CLI_VERSION)"`.
- `scripts/openspec-gates.sh` asserts `openspec -V` output equals the file contents before running any gate; mismatch → non-zero exit with a message naming both versions.

Alternatives considered:
- *Pin only in the workflow and hope the gate script matches* — status quo; it is exactly how the 1.6.0/1.13.0 split was born. Rejected.
- *Add a Python dev dependency providing an `openspec` entry point* — no such package exists; the CLI ships on npm. `uv add` cannot express an npm pin. Rejected.
- *Declare the version in `pyproject.toml` tool table* — would mislead readers into thinking the Python environment owns it, and still duplicates the workflow string. Rejected.

### D2: Gate script calls `openspec` directly, dropping the `uv run --locked` wrapper

`uv run --locked openspec` resolves nothing from the lockfile (see Context) — the wrapper adds zero version management and actively obscures where the binary comes from. The gate script becomes:

1. read the pin, 2. `openspec -V` equality assertion, 3. bare `openspec validate …` calls.

The sibling `uv run --locked python -m tools.spec_traceability check` line stays — there, `uv run --locked` is meaningful (the Python environment is genuinely locked). CI's "Validate OpenSpec" step already calls bare `openspec` after the global install, so both entry points now invoke the same kind of binary under the same declared version.

### D3: Drift prevention via a top-level contract test

`tests/test_openspec_cli_version_contract.py` (discovered by the existing `unittest discover -s tests` entry point; no shard-manifest change) asserts, against the committed files only — no network, no CLI invocation:

1. `openspec/CLI_VERSION` matches `^[0-9]+\.[0-9]+\.[0-9]+$` and equals `1.13.0`;
2. the workflow's `Install OpenSpec` step run-command embeds `$(<openspec/CLI_VERSION)` and contains no literal other-version pin;
3. `scripts/openspec-gates.sh` contains the version-assertion logic referencing `openspec/CLI_VERSION`.

The test carries `@covers_requirement` annotations for the new capability's requirements so `tools.spec_traceability check` counts them as associated the moment the capability is archived into `openspec/specs/` (identifiers are `openspec-cli-version-pinning::<requirement-slug>`; the implementer copies the exact slugs produced by the delta headings — same convention as every other contract test in `tests/`).

Alternative considered: have CI invoke the version assertion itself instead of a test — kept *both* is the decision: the script assertion protects the archive gate at runtime, the contract test protects the repo at every push.

Sync ordering is load-bearing: from the moment the test lands until the capability is synced into `openspec/specs/`, the three annotated IDs are `unknown-requirement-id` errors and `spec_traceability check` — the archive gate's first command and a CI preflight step — exits 1. Green CI is reached only when archiving syncs the capability; the archive gate itself must therefore run *after* the sync (the standard archive flow orders them that way; "archive without syncing" is forbidden for this change). When syncing, the new main spec's `## Purpose` MUST carry the delta's real prose — the repo sync skill's "can be brief, mark as TBD" suggestion is exactly the habit that produced the 30 placeholders this change removes and MUST NOT be followed.

### D4: Purpose backfill edits main specs directly

1.13.0's warning states the constraint: a delta `## Purpose` is read only when the capability is created — it cannot replace an existing placeholder. Therefore each of the 30 specs gets its `## Purpose` section rewritten in place in `openspec/specs/<capability>/spec.md`, with prose derived from that spec's own requirement headings and text (English, one to three sentences, factual, no invented capabilities). One variant: `entity-sex-vocabulary` carries the stale `TBD - created by syncing …` line *above* already-written, requirement-derived prose — there the fix is deleting the stale line and keeping the existing prose, not rewriting it. No `### Requirement:` line is added, removed, renamed, or reworded, so requirement identifiers the traceability tool indexes are untouched and no delta spec is possible or needed for the backfill.

To keep future placeholders from reappearing: 1.13.0 itself fails strict validation on any placeholder Purpose, and the `openspec-propose`/archive flow already requires a `## Purpose` in new-capability deltas — the version alignment is itself the prevention mechanism; no extra tooling is added.

## Risks / Trade-offs

- [1.13.0 may format or interpret artifacts differently than 1.6.0 for in-flight changes] → Verified on this machine: `openspec validate --all --strict` under 1.13.0 passes every item except the 30 placeholder-Purpose specs (195/225; remaining failures are the known warnings). No other breakage observed.
- [The contract test pins the literal `1.13.0`, so a future version bump must touch the test] → Intentional: bumping the CLI is a deliberate act; the test makes every file that must change obvious. The bump ritual is exactly two edits: `openspec/CLI_VERSION` and the test's expected literal (the delta-spec scenario is worded to match).
- [A developer's PATH `openspec` differs from the pin while the archive gate runs] → The script assertion fails fast with both versions named; previously this scenario silently validated with the wrong version.
- [Purpose prose could drift from what requirements actually say] → Each Purpose is derived from that spec's requirement list (tasks require reading requirements first); reviewers can diff Purpose text against headings; `--strict` plus `tools.spec_traceability check` keep structure and coverage honest.
- [Editing 30 spec files touches many files at once] → Edits are confined to `## Purpose` sections; the traceability tool indexes only requirement headings, so gate risk is nil; `validate --all --strict` is the mechanical check.

## Migration Plan

Ordinary change flow: implement on the feature branch, gates run in CI under the new pin, archive merges the capability. Rollback = revert the commit; nothing persists state.

## Open Questions

None.
