# Design: Party window 系譜 tab

## Context

See proposal.md. `LineagePanel.vue` renders v2 graphs as node lists (transitional since change 20); the prototype `tabs/LineageTab.vue` defines diamonds, layout by depth and edge labels.

## Goals / Non-Goals

**Goals:** truthful graph drawing from `depth`, `edges` and node states; deletion of `LineagePanel`.

**Non-Goals:** new layout data from the server beyond `depth`; growth rules in the client.

## Decisions

- **Layout**: rows by `depth`, columns by first appearance order within each depth; edges drawn as SVG lines with a `Lv N` label at the midpoint; SVG sized with `--ui-scale` tokens.
- **States**: capped = filled diamond + solid border + 見頂, owned = half-filled + solid border, locked = dashed border + prerequisite text; ready adds 可解鎖 text.
- **Node selection** sets the 技能 tab's selected skill and switches tab locally (no server call besides the tab's own selection dispatch).

## Risks / Trade-offs

- [Edge crossings in dense graphs] → Acceptable; payload order keeps layout deterministic and stories cover the seven-node ice graph.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: list grouping, root naming, diamond states with text, one/two/seven-node graphs, merge node once, edge labels, ready marking, node → 技能 switching, no invented graph when unavailable. Stories (multi-node, single-node, ready-to-unlock) at both sizes; Storybook build and showcase coverage; AGENTS.md. `tools.contract_gate`.
