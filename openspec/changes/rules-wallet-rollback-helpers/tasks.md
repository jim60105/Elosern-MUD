## 0. Ground rules (apply to every task)

- Behavior-preserving refactor: identical raises, messages, return values, log events.
- Evennia tests run with `MUD_TEST_SETTINGS=1` via the Bash tool's `env` input, e.g.
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb <label>`.
- No test file renamed; `.github/evennia-shards.json` untouched; event ids byte-identical;
  `tools/observability_freeze.json` shrink-only.

## 1. read_wallet extraction

- [ ] 1.1 Create `world/rules/wallet.py` with `read_wallet(entity: Any, error_cls: type[Exception]) -> int`
  copying `service_view.py:313-327` byte-for-byte (possession recursion calls
  `read_wallet(owner, error_cls)`; deferred imports of `world.rules.possession._resolve_live_object`
  and `typeclasses.characters.PlayerCharacter` stay deferred inside the body; refusal raises
  `error_cls("wallet is malformed")`).
- [ ] 1.2 Grep the private names for external references:
  `grep -rn "_read_wallet" world web commands tests` — replace the bodies of
  `service_view._read_wallet` and `status_query._read_wallet` with one-line delegates
  `return read_wallet(actor, ServicesViewError)` / `return read_wallet(entity, StatusQueryError)`;
  delete the private name and switch callers directly to `read_wallet(...)` ONLY where grep
  shows the sole references are its definition and same-module call sites. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_service_view` and
  `... world.rules.tests.test_status_query`.
- [ ] 1.3 Confirm the possession-recursion path stays covered: run
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_service_view_side_effects`
  (it exercises the possessed-actor wallet read). If neither suite names a malformed-wallet
  case, grep `wallet is malformed` under `world/rules/tests/` and run whichever module
  asserts it — that suite is the real regression proof.

## 2. Rollback restore helper

- [ ] 2.1 In `world/rules/clock.py`, generalize `_restore_registry_attribute` to accept a
  keyword-only `stage: str` used in the `rollback_restore_failed` context dict; keep the
  `# observability: ignore R2: cache invalidation is best-effort; ...` comment verbatim on
  the inner `except`. Update the clock call site (`clock.py:554`) to pass
  `stage="advance_registry_attribute"`. Rename to `restore_registry_attribute` (drop the
  leading underscore only if `cast_settlement.py` — the new importer — is the sole external
  caller; verify with grep).
- [ ] 2.2 In `world/rules/cast_settlement.py`, replace the body of
  `_restore_attribute_direct` (lines 203-238) with a delegate to the clock helper passing
  `stage="cast_registry_attribute"`; delete the duplicated try/except. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_cast_settlement` and
  `... world.rules.tests.test_clock`.
- [ ] 2.3 Pin the stage tags: run
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_rules_observability`
  and grep both suites for `rollback_restore_failed` context assertions; if none asserts the
  `stage` value, add one assertion to the EXISTING rollback-failure test in
  `world/rules/tests/test_cast_settlement.py` and one in `test_clock.py` (each fails pre-change
  only if the tag drifts, i.e. they defend the extracted parameter, not plumbing).

## 3. Wave close-out verification

- [ ] 3.1 `uv run --locked python -m tools.spec_traceability check` passes unchanged.
- [ ] 3.2 `uv run --locked python -m tools.observability_lint check` passes;
  `git diff tools/observability_freeze.json` shows no additions.
- [ ] 3.3 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`
  green without manifest edits.
- [ ] 3.4 `git diff --check` clean.
