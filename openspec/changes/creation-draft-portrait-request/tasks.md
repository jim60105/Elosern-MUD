# Tasks

## 1. Rule-owned admission

- [ ] 1.1 Extract pure shared checks into `world/rules/creation_identity.py` and `ensure_player_portrait_policy` in `character_creation.py`; add `creation_portrait.py` request/receipt ownership and exclude pending policies from startup autogen recovery. Land synthetic `world/rules/tests/test_creation_portrait.py` tests for identity checks, ownership/pending recheck, no canonical identity/draft/confirmation writes, restart without automatic replacement and transactional/cache rollback. The rules command in design must pass.
- [ ] 1.2 Add exact portrait payload validator/adapter and register the action; map safe reasons through `creation_messages.py`. Extend existing creation payload/adapter and fingerprint tests for missing/extra keys, all prompt cases, malformed age, forbidden synthetic sex/race and portrait success/rejection between save and activation. The focused adapter command in design must pass without changing activation authorization.

## 2. Common generation path

- [ ] 2.1 Add the typed pending-only `draft_values` branch to the existing service seam and factor the shared template composition in `subjects.py`. Extend request-seam/subject tests with conflicting shell attributes and active-character controls. Expected state is draft-value description with no shell identity read, no general age bypass, and unchanged ordinary request behavior. Preserve diagnostic-only connectivity: no new probe import/call or cached-verdict gate; a refusing fake client admits the valid request then produces an ordinary worker failure.
- [ ] 2.2 Atomically check in-flight/enqueue under the existing queue lock; carry draft replacement metadata and settle one current creation image/default without touching unrelated cards. Extend `world/art/tests/test_queue.py` and request-seam tests for two sessions, failure preserving old output, repeated failed retries, successful replacement and rollback before commit/unlink. Existing generation-token rejection and lock order must remain.
- [ ] 2.3 Update synchronization documentation, policy docstrings and service ownership notes in the same delivery. Verify the described exact payload, bounded receipt and pending-only age exception match focused passing tests; add no blueprint schema or migration.

## 3. Registry and echo integration

- [ ] 3.1 Extend the command-echo catalog, its coverage manifest and `test_action_catalog_coverage.py` for one admitted action-label echo with no prompt/identity content. The Node command in design and the focused Python catalog module must pass; drawer opening and gate-refused dispatch remain silent.
- [ ] 3.2 Run each focused command in design independently, register new modules with `uv run --locked python -m tools.shard_register fix`, then run `uv run --locked python -m tools.contract_gate` and `openspec validate creation-draft-portrait-request --strict`. Expected state is no warning/failure and real test-to-delta evidence.
