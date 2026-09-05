# Tasks: possession-validator-lockstep

## 1. Server panel validators

- [x] 1.1 `web/webclient/presentation/exploration.py`: replace the private `ACTION_IDS` tuple
  (:83-89) with a reference derived from the shared vocabulary's `ACTION_CODE_ALLOWLIST`
  (`affordances.py`); delete the stale `exploration_possession_affordance_dropped` swallow ONLY if
  it becomes unreachable for vocabulary-legal codes (keep it for genuinely foreign entries).
- [x] 1.2 `web/webclient/presentation/options.py`: extend the existing
  `from web.webclient.actions.exploration_actions import (...)` block (:20-29) with
  `validate_possess_payload` and `validate_possess_release_payload` and register both in
  `_ACTION_PAYLOAD_VALIDATORS`. NO relocation — the functions stay in `exploration_actions.py`
  (a move + back-re-export would create a real `options ⇄ exploration_actions` import cycle).
- [x] 1.3 `options.py:88`: bare `validators[action_id]` → `.get` + structured rejection naming
  the code (ProtocolValidationError-shaped, same lineage as the sibling rejections).

## 2. Client mirror

- [x] 2.1 `web/static/webclient/js/elosern/protocol.js`: add `explore.possess` +
  `explore.possess_release` to `CONTEXT_ACTIONS_ACTION_CODES` (:544) and `EXPLORATION_ACTION_IDS`
  (:3090); add the two `validateContextActionsAffordanceParams` (:1093) switch branches accepting
  exactly `{"npc_id": <positive integer ≤ MAX_SAFE_INTEGER>}` for BOTH codes (the shape the
  Python validators at exploration_actions.py:233-249 accept) and rejecting everything else
  (missing key, extra keys, non-integer, out-of-range).
- [x] 2.2 Audit `web/webclient-app/src/protocol/**` for equivalent enumeration tables (static pass
  found none); if any exist, widen identically and update Vitest fixtures; run `pnpm run build`
  ONLY if app sources actually changed (dist is a build artifact).

## 3. Tests (with the behavior)

- [x] 3.1 EvenniaTest regression at the composition layer: room with a bound companion → render
  the FULL `exploration` and `context_actions` panels through production presenters+validators;
  assert both available, the possess affordance present, no presenter error event. Lands in an
  existing exploration/context presentation test module; if a NEW module file is created, update
  `.github/evennia-shards.json` in the same change.
- [x] 3.2 Totality pin: the `_ACTION_PAYLOAD_VALIDATORS` key set ⊇ `ACTION_CODE_ALLOWLIST`; and a
  structured-rejection test for an out-of-vocabulary code through the same lookup. Include the
  suggestion-card path (`_validate_suggestion_params` → affordance-params lookup): a possession
  suggestion card must validate or reject structurally, never raise.
- [x] 3.3 Node gate: extend `web/static/webclient/js/tests/protocol.test.js` with accept/reject
  vectors for both possession codes in both enumerations. The ten-code inline fixture is a JS
  contract pin (label it as such; add an "update on vocabulary change" review marker) and its
  vectors must drive a real possess/release affordance entry through
  `validateContextActionsPanel`/`...AffordanceParams`, not just the exported arrays.
- [x] 3.4 Panel-derivation pin: `exploration` accepted-action set equals the shared allowlist.

## 4. Verification (focused only; no CI shard commands)

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  web.webclient` (focused labels for the touched modules).
- [x] 4.2 `node --test web/static/webclient/js/tests/protocol.test.js`; if Vue sources changed:
  `pnpm test`.
- [x] 4.3 `uv run --locked python -m tools.spec_traceability check` green with annotations on the
  tests covering the MODIFIED requirements' new clauses (literal IDs from
  `tools.spec_traceability list` after sync).
