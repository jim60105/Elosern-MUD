## Context

StageActor shown() currently synthesizes a name placeholder and wraps ReferenceArtwork; report Stage/Portraits bullets 1, 2 and 4, Vitals bullet 4, Motion bullet 3.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Ground standing portraits and honest no-art silhouettes without changing the art pipeline.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Use a stage-only variant of ReferenceArtwork: alpha images retain their full contour, an ink ground ellipse and restrained drop shadow seat them on the band, and captions remain available to assistive technology rather than visually floating below the actor. Drawer artwork is unchanged. Do not infer alpha from filename or attempt a client cutout; the art-default proposal supplies transparent defaults. Do not apply the report's tighter ellipse to all portraits: it clips already-correct alpha hair and equipment.

The stage uses bottom-aligned contain fit, replacing its former face-rectangle
crop. Reconcile the existing contextual-HUD actor requirement accordingly and
scope the art-panel cover-fit requirement to the default drawer variant.
Opaque inputs retain their supplied rectangular background: this is an explicit
trade-off, verified in the opaque story, rather than a guessed client cutout or
a universal mask that erases alpha contours.

For missing, pending, failed and load-failed art, use one local inline SVG standing silhouette sized to the actor box, feet at the band. Show the name/initial and authoritative state once in the chest region. Only pending art shimmers, only at full motion; missing art must not promise generation. Offline gameplay, speaking dim and beat gestures stay intact.

Keep existing portrait-anchor/foe ratios. Resolve the reported 1280x720 vitals collision by reserving the island's horizontal footprint for the player's readable silhouette label, not by moving data under an island. Ground shadows are decoration, inert and outside the accessibility tree.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
