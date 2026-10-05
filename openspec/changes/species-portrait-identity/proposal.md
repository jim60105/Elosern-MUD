## Batch:

- depends-on: monster-species-registry (the species key IS the image identity), official-content-provenance (it owns the typed official content reference whose `monster` kind this change finally gives a producer; its proposal already declares the species registry as that prerequisite), official-artwork-catalog (mounted-catalog lookup by content reference), official-art-resolution-contracts (the presentation chain step that consumes an entity's official content reference)
- conflicts: `world/art/subjects.py`, `world/art/presenter.py`, and `world/rules/art_view.py` with the four artwork changes — this change adds species-identity resolution beside the machinery those changes own, so it MUST serialize after `official-content-provenance` and `official-art-resolution-contracts` land (it edits their landed code, not a parallel copy). `world/lore/monster_species.py` is read-only here (identity added as a helper read, no registry edit), so no conflict with the monster wave's lore-side changes. `.github/evennia-shards.json`: disjoint new entry; serialize landings.
- boundary: this change connects identity only — it resolves and presents the species-keyed official reference and guards the anti-tier-substitution rule. It ships no image bytes (the official package for `monster/<species-key>/` is an out-of-repo deliverable of `official-artwork-catalog`/`official-artwork-deployment` content), adds no portrait eligibility rule, and mutates nothing: an unmounted catalog behaves exactly like today's runtime/silhouette chain.

## Why

Design §7: species pictures ride the `monster/<species-key>/` identity from the external-art design, official images stay read-only, and each individual's personal image choice and geometry stay independent — and the design explicitly warns that the artwork proposals do not mean a species registry exists, and tier aliases must never satisfy that prerequisite. Today a monster's only image identity is its threat tier (`portrait:monster:<tier>` via `world/art/presenter.py`/`world/rules/art_view.py`), so six visually distinct approved species would all wear one tier silhouette, and `official-content-provenance` ships with monsters as an acknowledged producer-less reference. Now that `monster-species-registry` provides stable species keys, this change makes the species key the species' image identity end to end.

## What Changes

- A species-backed monster resolves its official content reference as `(monster, <species_key>)` derived solely from its persistent species provenance — never from its threat tier, display name, or variant key (variants share the species image; individuality comes from personal selection/geometry). The resolution is a pure read of stored identity plus the startup catalog snapshot.
- The standing anti-substitution guarantee stays enforced and becomes testable for real: no code path may present another species' official image by threat tier; a species whose official package is absent from the mounted catalog falls through to exactly today's runtime/silhouette chain with no diagnostic beyond the bounded vocabulary.
- The existing generic tier subject (`portrait:monster:<tier>`, validated against `MONSTER_TIER_REGISTRY`) keeps serving the built-in silhouette/gallery generic layer unchanged — species identity joins at the official-reference layer, matching the external-art design's separation of shared official art from generic silhouettes; tier-only individuals are unaffected everywhere.
- Individual independence is preserved and asserted: two individuals of one species share the official reference only (read-only default); personal selections, face-rect, and stage overrides stay per-entity through the existing `official-art-personalization` machinery, which this change neither edits nor duplicates.
- No auto-generation suppression change: the existing official-satisfied rule from `official-art-resolution-contracts` applies to the monster reference as soon as a producer exists, and one contract test pins that a monster with a mounted official species image presents it without installing any new state.

## Capabilities

### New Capabilities

- `species-portrait-identity`: the species-keyed official image identity — provenance-derived `(monster, species_key)` reference, tier-substitution prohibition with fall-through honesty, variant-shares-species-image rule, tier-only individuals unchanged, and per-individual independence from the shared reference.

### Modified Capabilities

- `art-subject-model`: records the layering fact — the generic monster subject remains tier-validated for the built-in silhouette/gallery layer, while species-backed individuals additionally resolve an official content reference keyed by species (the subject model itself gains no new kind), so no queue, store, or presenter path can smuggle a species key into the tier-validated subject vocabulary.
- (No delta on `official-content-provenance` itself: its "monster species references await the separate species catalog" requirement is an in-flight delta of that not-yet-archived capability, so this change cannot MODIFIED it and ships no file for it. Landing order carries the supersession — `official-content-provenance` lands and archives first, and this change's own `species-portrait-identity` requirements then hold exactly what that requirement anticipates: the registered species key is the content key, a species-backed monster's reference derives solely from stored species provenance (never tier, display name, or variant), a tier-only monster produces no reference, and the zero-producer and anti-substitution guarantees it states are carried forward unchanged.)

## Impact

- Code: `world/art/subjects.py` or its sibling (species reference producer from provenance), the monster arm of the official-reference resolution consumed by `world/art/presenter.py` / `world/art/gallery_match.py` chain step 3, `world/rules/art_view.py` classification docstring/annotation only if needed, new tests under `world/art/tests/`, `.github/evennia-shards.json` entry.
- No player-command surface change; docs for gameplay commands untouched. No image assets, no gallery/personalization edits, no database change, no generation or state mutation.
