# Design: lineage panel v2 connected skill graphs

## Context

See proposal.md. `build_lineage_view(entity)` emits one chain per consumed root as the reverse-edge closure in topological order, with `meter`, `consumed`, and nodes derived through `_node_view`; identity eligibility filters nodes and roots; `lineage.py` truncates trailing chains then nodes; `commands/lineage.py` prints chains.

## Goals / Non-Goals

**Goals:** one graph per connected component, each node once, explicit edges, deterministic depth, member-scoped panel and command.

**Non-Goals:** graph layout coordinates beyond `depth` (the client places siblings), the 系譜 tab UI.

## Decisions

- **Components**: union-find over identity-eligible skills using prerequisite edges; a component qualifies when it has an edge, or when its single skill is owned. `root_keys` = nodes without prerequisites in registry order; `graph_id` = the first root key; `group_label_zh` = the shared element/style label of the roots (existing `CATEGORY_LABELS`/chain label helper), joined labels when roots differ.
- **Ordering**: graphs in registry order of their first root; nodes topologically with registry order as tie-break; `depth` = longest path from any root.
- **ready** = not owned and every prerequisite edge's minimum level met.
- **Truncation**: drop trailing graphs, then trailing nodes and every edge touching them, then further graphs, until within the byte bound; counts describe the full view.
- **Command**: `lineage [<成員>]` resolves with `resolve_member_token` (membership only) and prints `── 冰（2/6）根：寒霜之觸‧冰錐術` headers, node lines with `← 冰錐術 Lv.3` edges, 見頂/可解鎖 markers.

## Risks / Trade-offs

- [Single-node policy] → Owned singletons only; recorded as a planning interpretation for the user.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Synthetic registries: a two-root merge graph (merge node once, two edges, depth 2), a single owned skill (one-node graph) and an unowned isolated skill (absent), ready marking, identity filtering, truncation without dangling edges, counts after truncation; presenter for the viewed member and possession; command parity; mirror parity; Vitest transitional panel. Both command documents and `tests/test_command_docs.py`; `tools.contract_gate`.
