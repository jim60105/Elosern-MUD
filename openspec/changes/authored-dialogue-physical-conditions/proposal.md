# Proposal

## Why

The approved authored-dialogue design requires actor identity, inventory, present companion, time, skills and exposure conditions. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Actor identity, inventory, present companion, time, skills and exposure conditions.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-dialogue-conditions`: Actor identity, inventory, present companion, time, skills and exposure conditions.

### Modified Capabilities
- None.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

No duplicate generated predicate evaluator, new game effects or source-specific social hierarchy. Both static YAML and generated JSON use the same conditions and canonical/package-permitted reference catalog.

## Batch:

depends-on: authored-dialogue-runtime
depends-on: authored-dialogue-possession
depends-on: authored-dialogue-social-identity

Code conflicts: Owns new condition evaluator. Progression slice extends same files after this. Shared browser fixture and dialogue.py are serialized; equipment/progression sources stay read-only.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. Dependencies refer to completed implementation; package-role companion references use captured package_id+role_id and current authoritative binding.
