## Batch:

- depends-on: (none — this change needs no official artwork directory and is dependency-free)
- conflicts: `world/art/presenter.py` payload branch and the portrait origin wire vocabulary (`protocol.js` + Python validators) with `official-art-resolution-contracts`: this dependency-free change ESTABLISHES the closed origin vocabulary (`runtime | silhouette | placeholder`) and the decorative `fallback` field; `official-art-resolution-contracts` later EXTENDS the vocabulary with `official` on top of what this change ships — serialize in that order; if the order is ever reversed, the resolution change's vocabulary ships first and this change rebases onto it. `ReferenceArtwork.vue` stage props with `official-art-personalization` (disjoint regions; serialize second).

## Why

Where the stage currently draws a crude stretched human SVG, the six committed built-in WebPs may be published (user-confirmed) and should instead render as dark, attribute-selected silhouettes using each image's own alpha mask, in the current stage position — while the portrait's true missing/pending/failed state stays truthful. The source design is §9. This change is independent of the official artwork mount.

## What Changes

- Keep the six committed originals and their closed `/art/defaults/<key>.<ext>` identities unchanged (no new files, no format conversion); reuse `fallback_key_for` (declaration → sex/apparent-age band → stable subject-key hash) as the single selection rule — no duplicated selection in JavaScript.
- Change the fallback payload semantics: the backend provides the resolved fallback key/media identity separately from the (absent) portrait — as a decorative `fallback` field retained even beside a resolved real image so a browser-side load failure can re-render it with no new request — and the payload never reports `DONE`, a generated label, or a completed generation for a silhouette; existing missing/pending/failed/unavailable states pass through unchanged. This change establishes the closed portrait origin discriminator vocabulary (`runtime | silhouette | placeholder`; `official-art-resolution-contracts` extends it with `official` when it lands).
- Replace the stage SVG in `ReferenceArtwork.vue` with a CSS alpha-mask rendering of the resolved built-in image: explicit mask-alpha semantics, existing dark silhouette fill styling, preserved aspect ratio, aligned to the stage floor; no RGB texture display, no stretching. Keep the actor name, targeting/focus behavior, accessible missing/pending/failed labels outside the decorative mask, and reduced-motion behavior.
- Preserve selection-rule behavior explicitly: apparent-age bands (≤12 child, ≥60 elder, between adult), adult-band fail-closed for unknown/invalid age, stable subject-key hash within the band's pool for sex outside the male/female pair, `monster_anon` for monsters without an override, and valid registry declarations as intentional authored overrides; entities with no named portrait subject may hash only their stable runtime entity identity.
- Keep every other portrait consumer honest: compact views may retain the existing text/glyph placeholder; no consumer may treat the fallback as a full-color completed portrait. If a real image fails in the browser after server resolution, show the already-provided silhouette reference plus the load-failure label with no state mutation and no remote request. If even the bundled resource fails, retain name + truthful text placeholder and a usable interaction surface.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `art-gallery-fallback`: the terminal seam's payload contract — resolved built-in identity/key/rectangle are carried as silhouette presentation data, never as a `done`/generated portrait; the selection rule, committed-vocabulary contract, and `/art/defaults/` serving are unchanged.
- `webclient-art-panel`: the portrait-catalog requirement gains the server-authored origin vocabulary, the decorative `fallback` field (including on placeholder rows for policy-less entities selected from validated attributes only), while the real-fields-stay-null placeholder rule, eligibility dispatch, and no-second-reference-beyond-the-fallback rule hold.
- `webclient-art-panel`: the ReferenceArtwork stage placeholder requirement — the inline standing SVG is replaced by the attribute-selected alpha-mask silhouette with preserved labels, geometry, and reduced-motion behavior.
- `webclient-contextual-hud`: the grounded-silhouette fallback requirement — the stage silhouette is now the server-selected built-in mask (or truthful text when the mask resource itself fails), still never claiming generation or inventing imagery.

## Impact

- Code: `world/art/presenter.py` (fallback payload branch), `web/webclient-app/components/ReferenceArtwork.vue` (stage mask), the art-panel wire vocabulary for the silhouette fields (dual-side validators), one focused browser acceptance file/class.
- No new image files, no route change, no database change; independent of the official artwork directory, gallery state, and generation services.
