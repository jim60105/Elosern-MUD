# Proposal

## Why

The approved authored-dialogue design requires typed social identity source without parsing persona prose. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Typed social identity source without parsing persona prose.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `social-identity`: Typed social identity source without parsing persona prose.

### Modified Capabilities
- None.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

No persona parsing, invented hierarchy, implicit model-authored identity writes or new freeform authority. Both scene sources read the same acting-body typed identity; generated-package publication retains deterministic construction ownership.

## Batch:

depends-on: authored-dialogue-contracts

Code conflicts: Shares profile shape/application and creation/import paths with later explicit content metadata only. Independent of runtime/player; physical conditions depend on this. Guild.py overlap with progression integration is serialized by dependency.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. Dependencies refer to completed implementation. This source API is independent of dialogue content storage.
