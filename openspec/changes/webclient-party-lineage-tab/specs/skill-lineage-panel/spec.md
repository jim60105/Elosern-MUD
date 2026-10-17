# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The WebClient renders the lineage window from the view alone`
- TO: `### Requirement: The party window lineage tab renders the graphs from the view alone`

## MODIFIED Requirements

### Requirement: The party window lineage tab renders the graphs from the view alone
The party window's 系譜 tab SHALL render the viewed member's `lineage` v2 graphs. Each graph's nodes SHALL render per-node level and an XP meter of `xp_into_level / 50` (e.g. 「23/50 → 下一階」, saturated nodes marked 見頂), locked nodes SHALL carry `prereq_text_zh`, ready nodes SHALL be marked 可解鎖, each graph SHALL show its `owned_count / total_count`, and the tab SHALL show `已完成 completed_count / total_count 樹`. Every rendered value SHALL come from the panel payload; the client SHALL compute no growth rules and render no chain meter.

#### Scenario: Expanded fire tree shows per-node meters
- **WHEN** a player opens the fire graph with `fire_arrow` at 23/50 into level 1
- **THEN** the node renders the meter 「23/50 → 下一階」 and the tab header counts only fully-`consumed` graphs

#### Scenario: The client invents nothing
- **WHEN** the payload omits a graph (truncated or unavailable)
- **THEN** the tab renders no placeholder graph and no invented progress
