## Why

A scan of the 597 test files shows 348 reference shipped game-content identifiers
(`fire_ball` 69 files, `healing_potion` 61, `guild_branch_altoria` 48, `capital_altoria`
39, CJK display labels like `治療藥水`/`林間小徑` in ~60 more) — behavior tests silently
coupled to data the upcoming full-content rework will rename, renumber, and reword.
There is no mechanism that classifies the legitimate data-contract tests, blocks new
coupling, or makes the debt visible, so every future data edit pays an audit tax and
behavior coverage silently rots into data echo.

## What Changes

- Add `tools/test_data_lint` — a deterministic, stdlib-AST (Python) + regex-token
  (JS/TS) gate that flags test sources referencing shipped-content identifiers or shipped
  display prose. Shipped content is discovered by importing the locked registry and
  rulebook catalogs at lint time (the same technique `spec_traceability list` uses), so
  the token universe can never drift from the data itself.
- Add the machine-readable exemption ledger `tools/test_data_freeze.json` with two entry
  kinds: `contract` (permanent, requires the file's module docstring first line to carry
  the exact tag `Data-contract test:`) and `debt` (temporary migration ledger; a lint
  flag makes any NEW debt entry a violation, so the ledger is shrink-only). A
  `check --seed` subcommand is the only way debt entries may ever be created, and only
  for files that currently violate — the pre-existing 291-file debt corpus.
- Seed the ledger from the completed scan of the 341 flagged files: all 54 classified
  data-contract test files (including 4 that currently scan clean) become `contract`
  entries and receive the `Data-contract test:` tag; the remaining 291 flagged files
  become `debt` entries. Day-one gate is green; the per-area migration
  changes remove entries as they migrate, and `check` fails on any stale, duplicate,
  non-flagging contract, or newly added debt entry.
- Wire `uv run --locked python -m tools.test_data_lint check` into the CI quality gate
  beside the observability lint and traceability check.
- Write the rule into `AGENTS.md` and `docs/development/evennia-testing-guide.md`:
  behavior tests use synthetic fixtures (the kit from `add-test-synthetic-data-kit`);
  only `Data-contract test:`-tagged files may name shipped content; new tests that need
  content semantics extend the synthetic kit instead.

## Capabilities

### New Capabilities

- `test-data-independence`: the classification contract (tag + ledger), the lint gate
  semantics (shipped-token universe, exemption kinds, shrink-only ledger), the CI
  wiring, and the documented authoring rule. Synthetic-kit requirements and the
  per-area closure requirements are added by their own changes under this capability.

### Modified Capabilities

(none)

## Impact

- New: `tools/test_data_lint.py`, `tools/test_data_freeze.json` (345 seed entries:
  54 `contract` + 291 `debt`),
  `tests/test_test_data_lint.py` (top-level repository check, not an Evennia shard).
- Touched: `.github/workflows/quality-gate.yml`, `AGENTS.md`,
  `docs/development/evennia-testing-guide.md`, plus a tag docstring line in the 54
  contract files.
- No production code or shipped-data changes. The ledger is the handoff
  artifact for the 17 migration changes (`migrate-*-off-real-data`), which own its
  shrink-down to the 54 contract entries.
