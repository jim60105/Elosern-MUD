## Context

Report Message Window bullet 1; Command Panel bullets 1-4; Command Line; Motion bullet 1. Main spec fixes band size, one legend and focus ownership.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Unify the bottom-band material, focus hierarchy, exploration popover and motion.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Keep the fixed band box and 2:1 split. Add a pointer-inert feather above the seam, fine gold edge and central ornament, plus a subdued region divider. The feather is decoration and must not lower the usable art area or cover captions. Keep the lightest text ground no lighter than the ANSI proposal contrast reference.

Use a shared control-strip height for message controls and dock legend; all lists shrink and scroll above it. Strong keyboard focus belongs to the active row/control; the container uses a quiet corner/rule but still has a clearly visible focus indication when it is the focus target. Remove the command input's second frame while retaining the outer focus indicator and native caret/selection.

Make the verb popover fully opaque, with its one title. Suppress only the duplicate breadcrumb on this popover path, not general submenu breadcrumbs. Its underlying overview stays inert and visually recessed. Render existing overview footer actions as secondary buttons, not new actions.

Replace rotateY(72deg) with a token-timed opacity/short horizontal wipe for full motion; reduced is fade-only and off is immediate. Do not change dispatch gates or keyboard routing.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
