## Context

LocalMap/MapLattice already implement coordinate dot field, remembered-name disclosure, fixed 208px fitting and pure geometry. Main webclient-local-map pins 9-unit labels/10px chrome; report Minimap bullets 1-3.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Raise map chrome readability while preserving truthful geometry and simplify the current-location ornament.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Keep the 208px island canvas and deterministic topology/clearance algorithm. Raise header/readout to 12px shared type; retain the textual orientation convention because an icon alone would no longer state it accessibly. For node labels use an 11 CSS-pixel target on the ordinary three-by-three island fixture by increasing the label declaration and recomputing the pitch from real label footprints. The map's dense-payload fit can necessarily scale below that target; do not promise a universal font floor inside a fixed 208px SVG for arbitrary payloads. The full-map disclosure, focus labels and accessible names remain the complete reading path. Never hide remembered marker names wholesale or drop actionable nodes to hit a nominal size.

The report's 'hide all non-adjacent labels' and terrain-like contour texture are rejected: map names/remembered disclosure and the existing coordinate-dot/one-vignette contract are deliberate. Tune only existing ink/gold layers, add non-topological corner ornaments outside the drawing, and retain contrast band for coordinate decoration. Merge the teardrop current-location ornament into the existing current marker footprint instead of offsetting it over connector paths; reserve the complete drawn footprint in geometry. Current position remains one claim, not a second pin.

Update the main map requirement's declared label/chrome numeric examples and derived pitch scenarios together, never simply replacing a 9 with 11 in CSS. The geometry invariant, bounds, remembered-name disclosure, fitted view, zoom and travel descriptors remain unchanged. This slice is map-specific and precedes final proportional scaling.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
