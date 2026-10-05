## Batch:

- depends-on: official-artwork-catalog, official-content-provenance, official-art-resolution-contracts
- conflicts: `world/art/gallery.py` card-source/read-model vocabulary, the gallery panel wire validators, and `webclient-gallery-management-actions` adapters with `official-art-resolution-contracts` (already landed per depends-on; this change extends what that change's payload vocabulary established — one integration owner for gallery.py, serialize after it). `ReferenceArtwork.vue` personal-override props with `builtin-silhouette-stage-fallback` (serialize after it if that change lands first; disjoint regions otherwise). Shared presenters/protocols mean gallery.py, protocol.js, and management-adapter tasks from this change and the silhouette change MUST be integrated serially, not merged in parallel.

## Why

With official images resolved and distinguishable, players need to choose them: an explicit personal official-image selection is an art preference on the runtime entity — never an edit of the shared mounted source — and face-rect/stage adjustments for an official image are personal overrides keyed by its stable root-relative identity. Gallery surfaces must show official entries as selectable-but-read-only. The source design is §7–§8.

## What Changes

- Personal official selection: an explicit selection replaces the personal gallery-default choice (equipment-bound runtime cards keep their existing precedence); a later explicit runtime-default selection clears the personal official selection and vice versa, making the selected default unambiguous. A stale/unresolvable official selection is ignored for image resolution while the preference is retained (fall through the remaining chain); updating the directory never switches a player-selected generated image to an official default; the selected root-relative identity resolves its updated bytes after restart, and if the identity disappears the normal fallback chain applies without deleting the preference or any image.
- Personal geometry: face-rect/stage adjustments for an official image are stored as personal overrides keyed by the stable root-relative image identity, validated by the existing geometry rules against the current image dimensions; if an artwork update makes a stored override invalid, rendering uses valid directory metadata or fitted default geometry, the preference is retained, and one bounded diagnostic is emitted — no other character's display changes.
- Gallery read models list official entries for the subject's content reference as `official`-sourced, selectable, previewable rows that are NOT `GalleryRecord.cards` seed cards; backend mutation APIs (delete/replace/regenerate-overwrite via the existing management adapters) reject official entries with named rejections and no file or shared-preference changes; the frontend hides/disables inappropriate operations while the backend stays authoritative.
- Manual generation keeps writing runtime cards only — it never writes into the mounted official directory and never replaces an official asset file; replacing the official directory never deletes runtime cards, clears selections, or imports copies into every character's gallery (a maintenance update/restart preserves generated cards and personal selections).
- Wire/validator/frontend: gallery panel rows, the art/roster payload origin (from `official-art-resolution-contracts`), the dual-side validators, and the gallery management-action adapters carry the official-source fields and rejection codes together with their consumers.

## Capabilities

### New Capabilities

- `official-art-personalization`: personal official-image selection and its mutual-clearing with runtime defaults, stale-selection retention/fall-through, geometry overrides keyed by stable image identity with update-tolerant degradation, and backend-authoritative read-only guarantees for official entries.

### Modified Capabilities

- `art-gallery-resolution`: the exact ordered chain is amended so step 4 carries the personal official selection ahead of the gallery-default card, and step 5's classic-asset step applies "when no personal official selection resolves" (design §7's order); the runtime-precedence purity clause is qualified to apply to catalog defaults, not explicit selections.
- `art-gallery-model`: the `GalleryRecord` gains personal official-art preference fields (the selected official image identity and per-identity geometry overrides) written ONLY through `world/art/gallery.py`'s API under the existing sole-writer and lock discipline — never as cards, never touching the mounted source.
- `webclient-gallery-panel`: card-row projection gains official-source entries (selectable/previewable, no binding/default semantics that runtime cards own) with the mirrored exact validators updated.
- `webclient-gallery-management-actions`: the action surface gains personal official selection/override adapters routed through the deterministic art writer and rejects every official-entry mutation attempt with a stable code; every existing adapter's guarantees are unchanged.

## Impact

- Code: `world/art/gallery.py` (official-entry read-model projection plus preference-field writers — still the sole writer of records), `world/art/gallery_match.py`/`presenter.py` (selection-aware step 1), management adapters (`web/` ui_action layer) + `web/static/webclient/js/elosern/protocol.js` + Python validators, `GalleryPanel.vue`/`GalleryDetailRail.vue` affordances.
- Two preset-born characters sharing official bytes can choose different images/geometry independently (acceptance criterion 4); official mutation attempts change nothing on disk (acceptance criterion 6). No database schema change (preferences are stored attributes).
