# Proposal

## Why

The approved authored-dialogue design requires complete authored rewrite for altoria_eatery, altoria_tavern, altoria_lodging. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Complete authored rewrite for altoria_eatery, altoria_tavern, altoria_lodging.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-dialogue-content`: Complete authored rewrite for altoria_eatery, altoria_tavern, altoria_lodging.

### Modified Capabilities
- None.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

Do not implement another slice, retain obsolete authored compatibility paths, change native generated/freeform authority or invent gameplay/lore. Content writing waits for its mandatory private source prerequisite at apply time.

## Batch:

depends-on: authored-dialogue-unread-notices

Code conflicts: Same-domain siblings share world/lore/dialogue/altoria_lower.py and profile source modules; apply serially or coordinate disjoint host hunks. New content test/review files are exclusive. All content changes share manifest append entries and the authored-dialogue-content main spec at archive; supervisor serializes manifest integration/archive, never edits sibling-owned hosts.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v1. This change owns only the interfaces explicitly assigned in its design. All active proposals are planning context; dependencies refer to future completed implementation, not mere proposal existence.
