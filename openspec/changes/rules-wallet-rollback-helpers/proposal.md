## Why

Two byte-identical duplications live in `world/rules/`, the single writer of game state:

- `_read_wallet` exists verbatim in `world/rules/service_view.py:313-327` and
  `world/rules/status_query.py:1530-1544` — integer-copper validation with possession
  recursion and the bool-guard (`isinstance(raw, bool) or not isinstance(raw, int) or raw <
  0` → malformed error); only the raised error class differs (`ServicesViewError` vs
  `StatusQueryError`). AGENTS.md pins integer-copper money as an architectural invariant; two
  copies means the malformed-wallet refusal can drift into two different acceptance rules
  for the same stored value.
- The registry-attribute rollback restore is duplicated between
  `world/rules/cast_settlement.py:203 `_restore_attribute_direct`` and
  `world/rules/clock.py:485 `_restore_registry_attribute``: identical try/except
  (direct `attributes.add`/`remove`, best-effort `reset_cache` fallback, `rollback_restore_failed`
  warn with a `stage` context tag); only the tag differs (`cast_registry_attribute` vs
  `advance_registry_attribute`). A third, RELATED copy exists —
  `world/rules/surfaces.py:41 restore_attribute_best_effort` (stage `"attribute"`) — but it is
  the DEEPCOPY variant (`restore_attribute` deepcopies the snapshot value), while these two
  deliberately write the snapshot directly because registry surfaces embed live database
  objects that `deepcopy` cannot copy. Folding it in would change behavior; it stays file-local
  and is listed as a non-goal.

## What Changes

- New `world/rules/wallet.py::read_wallet(entity, error_cls)` — the single money-read
  implementation, recursion included; `service_view._read_wallet` and
  `status_query._read_wallet` become one-line delegates (the private names stay so existing
  module-level patch targets, if any, keep resolving).
- New shared rollback helper (hosted in `world/rules/clock.py`, which already owns the
  advance-side restore and is imported by `cast_settlement.py`; signature gains a `stage: str`
  parameter) — both call sites pass their own stage tag so the logged `stage` context value
  stays byte-identical (`cast_registry_attribute` / `advance_registry_attribute`).
- No behavior change: same errors, same messages, same log events, same return values. No
  test file renamed; no shard-manifest edit.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None — `skip_specs: true`. The governed behaviors (services view read-model, status query
read model, cast-settlement atomic rollback, clock advance rollback) are already specified
in `service-view`, `status-query`-family and `cast-settlement-atomicity`/`world-clock`
capabilities; every requirement stays exactly as shipped and its traceability annotations
stay attached to the existing passing tests.

## Impact

`world/rules/service_view.py`, `world/rules/status_query.py`, `world/rules/clock.py`,
`world/rules/cast_settlement.py`; new `world/rules/wallet.py`. No command surface, no
payload, no event id changes. `.github/evennia-shards.json` unchanged (`world.rules.tests`
shard labels already cover the packages; `wallet.py` is a non-test module).

## Batch

- depends-on: (none)
- Independent of `webclient-presentation-push-factory`, `art-path-confinement-and-ai-guardrails`,
  `webclient-frontend-utils` (disjoint files).
- **Shares `world/rules/` with the in-flight change `rules-handler-dedup` (wave B) only at
  directory level — files are disjoint** (`service_view`/`status_query`/`clock`/
  `cast_settlement` vs `action.py`/`economy.py`), but `world/rules/tests/test_clock.py` and
  `test_cast_settlement.py` already carry the `_raw_attribute` helper that wave D's
  `test-infrastructure-dedup` will consolidate — land wave D after this change so the
  helper extraction sees the final caller set.
- No overlap with `martial-arts-catalog`, `elementless-damage-effect`,
  `divine-mystery-catalog`: those touch `world/skills/`, rulebook YAML, `world/lore/player_presets.py`,
  and `world/rules/tests/test_divine_mystery_gate.py` only; none name the four files this
  change edits.

## Non-goals

- The sibling `clock.py::_restore_advance_location` / `cast_settlement.py` location-restore
  pair is similar but not byte-identical (different stage tags AND different re-fetch
  prose/events); leaving both file-local.
- `world/rules/surfaces.py::restore_attribute_best_effort` stays file-local: it restores through
  the deepcopy path (`restore_attribute`), which the registry pair deliberately avoids because
  registry surfaces embed live DB objects. Same event id, different write discipline — merging
  them would be a behavior change, not a dedup.
- `world/rules/economy.py`'s own wallet arithmetic is the writer side; untouched here.
