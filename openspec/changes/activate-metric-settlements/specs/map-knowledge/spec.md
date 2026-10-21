# Spec Delta

## ADDED Requirements

### Requirement: Coordinate cutover preserves observations without re-observation
Deterministic coordinate synchronization SHALL remap coordinate-backed known-node identity through the knowledge owner, preserving first/last seen ticks without recording arrival. Scene identity, service/NPC/quest references and home/inbound references SHALL resolve to the same logical room after cutover.

#### Scenario: Occupied discovered room survives
- **WHEN** actual startup replaces both settlements’ coordinates then restarts again
- **THEN** dbids, occupants, homes, references, knowledge timestamps and artwork association persist; place street attachments and NPC schedule/quest targets resolve correctly; no alias decoder, delete/recreate, or schema migration remains.

#### Scenario: Failure restores cutover
- **WHEN** a fault occurs after coordinate tags or identity records change
- **THEN** durable and cached coordinates/knowledge/references return to pre-cutover state, and ambiguous bindings refuse before changes.

