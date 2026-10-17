# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Follower set under possession (3.5h)

- [ ] 1.1 Derive followers from `resolve_commander(traverser)` and effective membership in `follow_companions`, move the owner body quietly, record its arrival once and re-observe quest arrival for the commander; verify in `world/rules/tests/test_party_follow_possession.py` grid, wilderness entry, step and return traversals, a failed follow with one notice to the puppet session, a stale possession flag following nobody, a destination receive gate refusing the body (left behind with the notice), a body in a recycled wilderness room rejoining through the registration predicate, `move_hooks=False` for the body only, unchanged player traversal, and no action-options/dialogue/encounter side effects attributed to the body.

## 2. Settlement compensation (2h)

- [ ] 2.1 Snapshot and compensate every follower (owner body included) in `movement_settlement.py`; verify injected failures before and after the follow return the possessed traverser, the owner body and companions with caches, wilderness bookkeeping and the possession mirror unchanged, and that a later 歸位 leaves both figures in the shared destination room.

## 3. Integration (1.5h)

- [ ] 3.1 Update existing follow and possession-transition tests, add `possessed` to the follow event context and run `uv run --locked python -m tools.observability_lint check`; register the new module in one shard; annotate canonical IDs for the modified `party-system`, `movement-settlement-atomicity` and `companion-possession-transition` requirements; run `uv run --locked python -m tools.contract_gate` and `openspec validate party-follow-under-possession --strict`.
