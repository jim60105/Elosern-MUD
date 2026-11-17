# Tasks

## 1. Reset and cancellation

- [ ] 1.1 Add rules-owned `reset_creation_draft`/`clear_draft_portrait` and service-owned exact-id job/card/error cleanup with commit-deferred confined unlinks. Extend `test_creation_portrait.py` for ready/pending/failed/unsaved and repeated reset, ownership rejection, unrelated controls and injected removal failure. The focused rules command in design must pass with no premature file deletion.
- [ ] 1.2 Route the reset adapter through the new owner, preserving confirmed-reset payload/result and transient proposal clearing. Extend adapter and queue tests for settle-before-reset, reset-before-settle and late failure settlement; canceled output must never reappear and rollback must restore caches and persisted state.
- [ ] 1.3 Update synchronization documentation with exact reset receipt/card/job ownership and late-token behavior; verify against the same focused tests, without a mid-game global prune or compatibility path.

## 2. Activation disposition

- [ ] 2.1 Integrate preset-only cleanup after preflight and before finalization inside `activate_player_character`; include creation portrait state in rollback snapshots. Extend portrait-finalization/activation-rollback tests for post-cleanup failure, prior committed art survival and successful preset normal-source resolution. The focused activation command in design must pass.
- [ ] 2.2 Keep custom card/in-flight work on the same subject, remove only staging receipt, and reuse the existing autogen guard. Test ready/pending/no-art/skip paths and late success after activation; count enqueues to prove no duplicate, while unchanged ordinary creation still auto-generates.
- [ ] 2.3 Add synthetic overlay/rule regressions for sex/race/subrace/apparent-age edits, concept fill and custom save retaining portraits without invalidation, warning or automatic generation. Update finalizer/developer documentation to distinguish activation-added state from previously committed draft art; the focused Vitest command in design must pass.

## 3. Delivery acceptance

- [ ] 3.1 Run focused commands in design plus `world.art.tests.test_queue` and `web.webclient.actions.tests.test_creation_actions.test_adapter` with the same standalone Evennia command prefix. Register new test modules/methods with `uv run --locked python -m tools.shard_register fix`. Run `uv run --locked python -m tools.contract_gate` and `openspec validate creation-draft-portrait-cleanup --strict`; expect no warning/failure.
