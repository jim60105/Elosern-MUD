# Proposal

## Why

The approved authored-dialogue design requires owner guild, quest lifecycle and host relationship qualification. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Owner guild, quest lifecycle and host relationship qualification.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `authored-dialogue-conditions`: extend the capability introduced by an earlier dependency with this slice's named requirements.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

No alternate generated progression evaluator, new lifecycle/rank arithmetic or model-owned effects. Owner qualification applies equally to canonical and authorized package-scoped references.

## Batch:

depends-on: authored-dialogue-physical-conditions

Code conflicts: Sequentially extends physical-condition files and capability. Quest/guild/affinity domain writers stay unchanged; no new lifecycle or rank arithmetic.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. Dependencies refer to completed implementation; generated package definitions resolve through the same validated catalog and quest record readers.
