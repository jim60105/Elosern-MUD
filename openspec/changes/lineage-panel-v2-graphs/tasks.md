# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Graph read model (2.5h)

- [ ] 1.1 Rewrite `lineage_query.py` to connected graphs with edges, depth and ready (preserving the lineage-position helper); verify synthetic-registry tests for a two-root merge (one merge node, two edges, depth), owned singleton present, unowned isolated skill absent, ready marking, identity filtering, and byte-identical rebuilds with no writes.

## 2. Panel v2 (2h)

- [ ] 2.1 Bump `lineage.py` to v2 with graph/node/edge caps and deterministic truncation without dangling edges, built for the viewed member; add `lineage` to the `party.view_member` affected panels; update the JS mirror, parity contract and fixtures; verify presenter, truncation and mirror tests.

## 3. Command and transitional window (1.5h)

- [ ] 3.1 Extend `commands/lineage.py` to `lineage [<成員>]` with alias `系譜`; render graphs in `LineagePanel.vue` without the meter; verify command parity with the panel, Vitest LineagePanel, both command documents and `tests/test_command_docs.py`.

## 4. Integration (1h)

- [ ] 4.1 Annotate canonical IDs for the modified `skill-lineage-panel` and `game-command-docs` requirements, register any new test module in one shard, run `uv run --locked python -m tools.contract_gate` and `openspec validate lineage-panel-v2-graphs --strict`.
