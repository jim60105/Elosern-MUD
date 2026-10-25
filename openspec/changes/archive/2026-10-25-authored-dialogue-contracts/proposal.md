# Proposal

## Why

The approved authored-dialogue design requires immutable reusable scenes and complete typed topic declarations. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Immutable reusable scenes, exact primitive schema, source-neutral validation and collision-free generated topic/scene identity.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-scene-model`: Immutable reusable scenes and complete typed topic declarations.

### Modified Capabilities
- None.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

No filesystem-generated content, profile requirement for generated roles, new effect verbs, compatibility migrations or gameplay/lore invention. The approved dialogue-specific YAML exception amends architecture D9; unrelated lore remains Python.

## Batch:


depends-on: none

Code conflicts: Runtime cutover touches shape.py and its imports; serialize after this. No production consumers change here.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. Loader owns safe filesystem parsing; generated-packages owns production prompt/schema and existing atomic DB package cutover. This change owns the pure common declarations/parser/validator/identity codec.
