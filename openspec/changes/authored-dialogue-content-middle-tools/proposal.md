# Proposal

## Why

The approved authored-dialogue design requires complete authored rewrite for altoria_general_store, altoria_forge, altoria_tailor. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Complete per-NPC YAML authored rewrite for altoria_general_store, altoria_forge, altoria_tailor.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-dialogue-content`: Complete authored rewrite for altoria_general_store, altoria_forge, altoria_tailor.

### Modified Capabilities
- None.

## Impact

Exact profile-key YAML ownership and APIs are enumerated in design.md. Files are automatically discovered without manual content registration; canonical profiles remain read-only. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

Do not implement another slice, retain obsolete authored compatibility paths, change native generated/freeform authority or invent gameplay/lore. Content writing waits for its mandatory private source prerequisite at apply time.

## Batch:

depends-on: authored-dialogue-unread-notices

The dependency chain includes authored-dialogue-contracts, authored-dialogue-yaml-loader and authored-dialogue-runtime; content uses their completed v2 schema/scanner implementation.

Code conflicts: Content slices exclusively own their per-NPC YAML files and unique test/review files; they do not edit shared region Python modules, profile definitions, loader code or a registration list. Profiles and place bindings are read-only canonical inputs. The integration owner serializes test-manifest entries in tools/test_data_freeze.json and .github/evennia-shards.json, runs the combined gate, and serializes archive into the shared authored-dialogue-content spec. No manual content registration is added.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. This change owns only the interfaces explicitly assigned in its design. All active proposals are planning context; dependencies refer to future completed implementation, not mere proposal existence.
