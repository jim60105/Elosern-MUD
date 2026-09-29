## Context

HudDrawer owns createFocusTrap and Escape propagation; current reference-surface requirement says above persistent command line. Report Drawers bullets 1-2 and top-bar icon mismatch.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Unify reference drawer and overlay framing without moving their modal boundary.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Create one small presentational DrawerHeader used by OverlayHost and HudDrawer, with display title, optional subtitle, registry glyph and 36px close target. It emits close only; existing hosts retain their focus trap, Escape ownership, nesting, opener restore and open-surfaces registration. Migrate gallery's duplicate title/close into its host rather than stacking headers. Full-log adopts the header in its own later change. Settings/help/map keep their existing body components.

Use a fully opaque ink panel and dark scrim. Blur/saturation is optional progressive decoration: opacity must work without backdrop-filter. Keep the existing workspace: 12px below the navigation, 16px side insets, and one command-line row height plus 12px (`--workspace-bottom`) above the viewport bottom. Since the AVG stage shell moved the command line onto the band's top edge, that workspace covers the stage, the band and the command-line row (expanded or not) and leaves only the band's lowest control strip exposed; earlier wording that the workspace sits "above the command line" predates that move and is corrected in this change's delta. Reject the suggested viewport-bottom 16px inset: it would push the panel onto that control strip for no gain and break the shared inset token. The scrim covers and recesses the exposed band strip so its text is not mistaken for drawer content; focus remains trapped. Do not dim the panel as part of stage recession.

The drawer scrim keeps covering the whole viewport and closing the drawer on activation. The overlay gains a scrim of its own that starts below the top navigation and only absorbs pointer activation: the navigation must stay operable because activating another overlay or drawer trigger replaces the open overlay, and an accidental click beside a map or settings workspace should not dismiss it. The overlay keeps its low stacking tier so the gallery's teleported nested editors (modal-tier drawers with their own scrim) still stack above it.

Use the same icon key registry as navigation; fix lineage/title icons there instead of an unrelated fallback '?'. Header typography uses the scale: both hosts render the title in the serif heading face (`--f-serif`) the live drawers already use, so overlay titles move off the handwritten display face. Header markup lives in one `DrawerHeader` component with its own `drawer-header__*` classes; the retired `hud-drawer__head/__title/__subtitle/__icon/__close` and `overlay-host__header/__icon/__title/__subtitle/__close` classes are removed with every stylesheet and test that selected them (existing `data-testid` values stay). The help overlay gains its missing title, 說明. This change migrates host chrome only, not every drawer's content layout, preventing an oversized redesign.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
