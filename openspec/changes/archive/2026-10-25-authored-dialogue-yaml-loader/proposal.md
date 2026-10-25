# Proposal

## Why

Per-NPC dialogue authoring requires one discoverable file per existing stable profile key. Safe all-or-nothing loading must be separate from the already broad runtime/protocol cutover to keep each implementation slice within one GPT-Luna workday.

## What Changes

- Add sorted safe YAML discovery at `world/lore/dialogue/content/<NpcProfile.key>.yaml`, with no manual file registration or duplicate owner field.
- Parse primitives through the shared immutable scene/topic validator and reject the complete candidate snapshot on any schema, identity or reference error.
- Publish a read-only snapshot once at initialization; runtime owns migration of existing Python dialogue data and deletion of obsolete modules.
- Record the dialogue-specific exception to architecture D9; unrelated lore stays Python.

## Capabilities

### New Capabilities
- `authored-dialogue-sources`: Discover, validate and publish immutable static dialogue definitions by stable NPC profile identity.

### Modified Capabilities
- None.

## Impact

Targets `world/lore/dialogue/loader.py`, shared codec integration and focused loader tests. No content prose, runtime/session cutover, hot reload, generated filesystem storage or gameplay mutation. Three bounded implementation units include their tests/docs.

## Batch

depends-on: authored-dialogue-contracts

Runtime depends on this completed API. Contracts owns the pure codec; loader owns filesystem handling/snapshot construction. Content slices own disjoint YAML files only after runtime migration. Generated package content never enters this snapshot. Shared contract v2 in `../authored-dialogue-contracts/design.md` fixes all schemas and identity rules. Planning only; no implementation or checks were run.
