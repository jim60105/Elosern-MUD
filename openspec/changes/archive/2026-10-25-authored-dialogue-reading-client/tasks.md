# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Pending completion state machine

Shared contract v2 preserves full generated IDs in admission/queue/request/response fields. Test long generated IDs, phase-retired memory and identical completion with no source-specific branch or truncation.

- [x] 1.1 Implement applyDialogueReading and finishDialogueDelivery with dedup, exact response binding, retry/discard distinctions and no browser persistence. Add tests/stores/dialogue_reading.test.js (new) with synthetic saved/stale/error responses and document bounded memory lifecycle.

## 2. Pure-chain and playback wiring

- [x] 2.1 Connect formal-only scene-finished events, predecessor-first ack queue and local public successor reveal; keep qualified choices authoritative. Add AppClient tests for pending status, no repeat effects, same-delivery refresh and stale-character replies.

## 3. Browser recovery and ownership

- [x] 3.1 Add focused retry-without-reread and reload-discard acceptance to test_browser_exploration_dialogue.py, register new methods and existing store wiring in relevant inventories. Verify focused Vitest/browser methods and contract_gate; update player-facing help only for observable saved/pending semantics.

## Implementation notes

- Focused Vitest (`web/webclient-app/tests/stores/dialogue_reading.test.js`,
  `app_client_dialogue_choices.test.js`, `use_authored_scene.test.js`,
  `use_dialogue_choices.test.js`, `dialogue_view_model.test.js`), the full
  `pnpm test` suite, the Node protocol gate and
  `uv run --locked python -m tools.contract_gate` pass in this worktree.
- The two managed browser methods
  (`test_dialogue_completion_retry_without_rereading`,
  `test_dialogue_completion_reload_discards_pending`) could not be executed
  locally: the local managed-browser harness login is broken for every browser
  test in this environment (pre-existing, not introduced here). They are
  registered in `.github/browser-shards.json` (shard 9) and remain CI-owned
  acceptance; no assertion was weakened. Run them with
  `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings
  test_settings.py --keepdb web.tests.browser.test_browser_exploration_dialogue`.
- The delta requirement annotations for the two new browser methods land at
  delta sync (authored-dialogue-locked-ui precedent): the traceability gate
  only recognizes synced requirement text.
