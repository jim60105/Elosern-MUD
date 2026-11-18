# Tasks

## 1. Reset and cancellation

- [x] 1.1 Add rules-owned `reset_creation_draft`/`clear_draft_portrait` using the request slice's serialized unit before any transaction/read/write. Add service-owned exact-id job/card/error cleanup with the active token, private already-locked primitives and commit-qualified post-unlock confined unlinks. Extend `test_creation_portrait.py` for ready/pending/failed/unsaved and repeated reset, ownership rejection, unrelated controls and injected removal failure. The focused rules command in design must pass with no premature file deletion.
- [x] 1.2 Route the reset adapter through the new owner, preserving confirmed-reset payload/result and transient proposal clearing. Add barrier-controlled separate-connection threaded tests for worker settlement contending with reset in both orders, including late failure; canceled output never reappears, no write transaction waits for queue serialization, callbacks run after lock release, and rollback restores caches and persisted state.
- [ ] 1.3 Update synchronization documentation with exact reset receipt/card/job ownership and late-token behavior; verify against the same focused tests, without a mid-game global prune or compatibility path.

## 2. Activation disposition

- [ ] 2.1 Wrap `activate_draft` and direct `activate_player_character` entry points with the serialized rules unit before their outer transactions, reusing the same-character nested unit. Migrate start-arrival callback to `on_publication_commit` and keep callbacks deferred until queue release. Integrate preset-only cleanup after preflight and before finalization; include portrait state in rollback snapshots. Extend activation tests with barrier-controlled worker contention, outer-commit failure, post-cleanup failure, prior art survival and successful preset normal-source resolution. The focused activation command in design must pass.
- [ ] 2.2 Keep custom card/in-flight work on the same subject, remove only staging receipt, and reuse the existing autogen guard. Test ready/pending/no-art/skip paths and late success after activation; count enqueues to prove no duplicate, while unchanged ordinary creation still auto-generates.
- [ ] 2.3 Add synthetic overlay/rule regressions for sex/race/subrace/apparent-age edits, concept fill and custom save retaining portraits without invalidation, warning or automatic generation. Update finalizer/developer documentation to distinguish activation-added state from previously committed draft art; the focused Vitest command in design must pass.

## 3. Delivery acceptance

- [ ] 3.1 Run focused commands in design plus `world.art.tests.test_queue` and `web.webclient.actions.tests.test_creation_actions.test_adapter` with the same standalone Evennia command prefix. Register new test modules/methods with `uv run --locked python -m tools.shard_register fix`. Run `uv run --locked python -m tools.contract_gate` and `openspec validate creation-draft-portrait-cleanup --strict`; expect no warning/failure.
