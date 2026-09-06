# Proposal: webclient-lore-codex-panel

## Why

The knowledge codex has a complete backend — the eight-category registry mapping, the append-only
discovered store, the deterministic listing, the per-category card renderer, and the `lore` command —
but no OOB read model, so the web client cannot show it at all.

The component named `LoreDrawer.vue` is a misnomer: it renders guild quest prose out of the
`services` payload, and its own header comment admits "the 8-category codex has no OOB read model in
this payload, so the drawer never fabricates codex cards (a deliberate skip)". This change lands the
missing read model so the codex drawer can be built.

## What Changes

- New host-independent `lore_codex` presentation panel (schema version 1) carrying the holder's
  discovered entries grouped by the eight `CODE_CATEGORIES` in mapping order, each group with its
  category key, its player-facing label, its discovered count, and its entries.
- Each entry carries its key, its display title, and its rendered card — the exact declared card
  fields for its category, in declared order, from `lore_card`. The whole codex ships in one payload:
  the eight registries hold a few dozen short entries in total, far under the envelope limit, and the
  registries are immutable module-level data that generation never extends. No on-demand fetch and no
  new OOB action are needed.
- Non-disclosure is absolute: undiscovered entries do not appear, category counts count only
  discovered entries, and a category with nothing discovered ships as an empty group rather than
  disclosing how many entries it could hold. This mirrors the rule `commands/lore.py` enforces by
  returning one fixed not-found line for unknown categories, unknown keys, and undiscovered entries
  alike.
- A `LoreRecordError` from the reader degrades the WHOLE panel to the registry-owned common
  unavailable form, and never resets or rewrites the stored record.
- Explicit row, entry, and per-field bounds with the shared envelope guard failing closed, so
  registry growth surfaces as a loud test failure rather than a truncated payload.
- Registry registration plus a push on the reveal seam.
- Client-side validator mirroring the exact Python bounds, covered by the dual-direction parity test.

## Capabilities

### New Capabilities

- `webclient-lore-codex-panel`: the `lore_codex` read model — its shape and bounds, host
  independence, discovered-only disclosure, card rendering through the canonical renderer,
  all-or-nothing degradation, push timing, and read-only presenter isolation.

### Modified Capabilities

(None — panel registration rides the existing `webclient-oob-protocol` registration contract without
changing it.)

## Impact

- New presenter and validator module `web/webclient/presentation/lore_codex.py`; registration in the
  presentation registry.
- Client mirror in `web/static/webclient/js/elosern/protocol.js` and the
  `webclient-vue-application` protocol mirror table.
- New focused test module; `.github/evennia-shards.json` updated in the same change.
- No client component consumes it yet — `webclient-lore-codex-drawer` does.
