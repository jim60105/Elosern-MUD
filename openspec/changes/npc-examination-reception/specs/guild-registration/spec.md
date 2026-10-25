# Spec Delta

## MODIFIED Requirements

### Requirement: Guild service components are capability adapters, not state writers
The project SHALL define `GuildStaff`, `Merchant`, and `GuildExamReception` Component subclasses attachable
to ComponentHolder NPCs. Components SHALL carry stable service/branch identifiers and persistent
service data only. Their command-facing methods SHALL delegate every registration, quest, trade,
examination, wallet, merit, inventory, and rank mutation to deterministic-core APIs.

#### Scenario: Service NPC exposes its capabilities
- **WHEN** an NPC has `GuildStaff` and `GuildExamReception` attached
- **THEN** local command discovery identifies it as both a guild service and examination service without
  inspecting the NPC's key or typeclass

#### Scenario: Components do not implement business writes
- **WHEN** the component modules are inspected
- **THEN** they contain no direct assignment to player rank, merit, wallet, inventory, quest log, reward
  claims, or active combat state
