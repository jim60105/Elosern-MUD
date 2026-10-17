# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration.

## 1. Lineage tab (3h)

- [ ] 1.1 Implement `PartyLineageTab.vue` (grouped list with diamonds and owned/total, detail graph by depth with labelled edges, non-colour states, node → 技能) and route the 技能系譜 tool to it; verify Vitest for grouping, root naming, one/two/seven-node graphs, merge node drawn once, edge labels, ready marking and node selection.

## 2. Deletion and stories (1.5h)

- [ ] 2.1 Delete `LineagePanel.vue`, its story, manifest title, tests and duplicate `.elosern-root` rules; add lineage stories (multi-node, single-node, ready) at both sizes; run `pnpm run build-storybook` and `pnpm run showcase-coverage`.

## 3. Integration (1.5h)

- [ ] 3.1 Update `web/webclient-app/AGENTS.md`, annotate canonical IDs for the renamed/modified and added requirements, run the touched Vitest files, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-party-lineage-tab --strict`.
