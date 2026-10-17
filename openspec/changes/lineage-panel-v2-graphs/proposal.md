# Proposal: lineage panel v2 connected skill graphs

## Why

Design §2, §5 and §6.5 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the lineage payload lists chains as reverse closures from each root, so a merge node appears in every root's chain and no client can draw the real graph; the 系譜 tab needs connected graphs (group label, roots, unique nodes, edges with minimum level, owned/total) for the viewed member, and the chain meter is removed. The text client needs `系譜 <成員>`.

## What Changes

- **BREAKING (pre-release)** `world/rules/lineage_query.py` rewrites chains into connected graphs (`LineageGraphView`, `LineageEdgeView`, node `depth` and `ready`); `lineage` panel v1 → v2 built for the viewed member; caps for graphs, nodes and edges; no meter. Single-node graphs are emitted only for owned skills (design §6.5 renders one-node graphs; emitting every isolated registry skill would bury the real trees — recorded interpretation).
- `lineage [<成員>]` gains the alias `系譜` and prints the graphs; both player command documents updated.
- `party.view_member` affected panels add `lineage`; JS mirror, parity, fixtures; the transitional `LineagePanel.vue` renders graphs as node lists with owned/total until the 系譜 tab replaces it.
- `world/rules/lineage_query.py` keeps the lineage-position helper added by `character-skill-growth-fields`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: lineage row identity uses graph roots and owned/total instead of the chain meter.
- `skill-lineage-panel`: read model, panel contract, command and window requirements move to graphs.
- `game-command-docs`: the lineage command entry documents the member argument and the `系譜` alias.

## Impact

- `world/rules/lineage_query.py`, `web/webclient/presentation/lineage.py`, `commands/lineage.py`, `party_actions.py`, JS mirror, fixtures, `web/webclient-app/components/LineagePanel.vue`, both command documents, `tests/test_command_docs.py` manifest.
- Tests: lineage query/presenter/command tests, Node mirror tests, Vitest LineagePanel.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **20 of 31**.

- depends-on: party-panel-v3-view-member
- depends-on: member-info-text-commands
- depends-on: item-holdings-panel

### Code and spec conflicts within the new batch

- `character-skill-growth-fields`: shared file `world/rules/lineage_query.py` (F; that first; its position helper is preserved).
- `party-unlock-notices` / `party-practice-booking`: none in code; `skill-lineage-panel` unlock requirement is a different requirement (S).
- `member-info-text-commands`: shared command docs and cmdset (F; that first, hence the declared prerequisite).
- `item-holdings-panel`: shared `party_actions.py` affected tuple (F; that first).
- `webclient-party-lineage-tab`: re-modifies the window requirement and removes `LineagePanel.vue` (S/F; ordered).

### Active change coordination

No active OpenSpec change.
