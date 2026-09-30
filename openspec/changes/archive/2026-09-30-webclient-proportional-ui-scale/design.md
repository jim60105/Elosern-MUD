## Context

AVG design section 2 requires proportional 2560x1440 behavior while preserving 1440x900 and 1280x720; report Cross-cutting and type/radius sprawl. Existing prose/band already use vh, so global zoom would double-scale them.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Scale desktop chrome with the 1080p reference without double-scaling prose or stage art.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Use S = clamp(1, min(viewportHeight / 1080, viewportWidth / 1920), 1.4) for desktop chrome (the width term, added during application, keeps a tall narrow window from outgrowing its width breakpoints). At 2560x1440 S=4/3; at the smaller acceptance sizes S=1. Define the unitless factor once from a ResizeObserver/window-resize owner, write one root CSS property, and remove the listener/observer on teardown. Do not read layout on every frame.

Scale the common type, spacing, radius, header-height, island-width, icon/control dimensions and fixed max-width tokens via calc(base * S). Audit fixed dimensions of the named surfaces and migrate them to the same tokens in one mechanical pass. Band height, prose vh size, standing-portrait vh geometry and full-bleed backdrop already respond to viewport dimensions: do NOT multiply them again. Reader prose preference remains a separate multiplier and does not change chrome. No CSS zoom/whole-root transform: these complicate hit-testing, SVG fit and accessibility zoom.

For the minimap only, scale its outward 208px square by S while keeping SVG user-unit geometry unchanged; this is a uniform display scale, never coordinate recomputation. The full-map fitted view measures its real available body normally. Scale drawer/creation art/form width caps once, not their percentages.

Consolidate ordinary rectangular radii to small/default/pill tokens while preserving circles, intentional square map cells, and geometric masks as geometry, not radius variants. Existing named display and prose type exceptions remain. This is a presentation-only mechanical conversion after the smaller surface changes, not a responsive redesign. At smaller acceptance sizes preserve readable text floors and internal scrolling rather than shrinking chrome below S=1.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.

## Implementation notes (applied)

- **One owner.** `lib/ui_scale.js` (height and width terms) exports the pure `computeUiScale(height)` and `installUiScale()`. `main.js` installs it before `app.mount()` and releases it through `app.onUnmount`; `.storybook/preview.js` installs the same owner so stories viewed above 1080px render at the live scale. `styles/tokens.css` declares `--ui-scale: 1` as the fallback for frames before the owner runs. The owner listens to window `resize` and writes only when the rounded factor changes.
- **One mechanical rule.** Every fixed CSS-pixel literal above 2px in the client's style sheets (components, `app-shell.css`, `tokens.css`, `AppClient.vue`) is written `calc(<n>px * var(--ui-scale))`, or `<n>px * var(--ui-scale)` inside an existing `calc()`/`min()`/`max()`/`clamp()`. 1–2px hairlines, borders and bar caps stay literal. Not touched: `@media` conditions, `@keyframes` bodies, the motion vocabulary (durations and travel distances), the focus ring, shadows and vignette tokens. The three viewport-derived tokens `--band-h`, `--message-text`, `--log-text` keep their vh term unmultiplied; only their px bounds carry the factor. `map-lattice.css` is excluded because its sizes apply inside the SVG in user units.
- **Why px bounds inside a vh clamp may scale.** Only px literals are multiplied, never a vh/vw term or a token derived from one, so nothing scales twice. For heights from 1080 to 1512, `px × S` equals `px × h / 1080`, so a scaled bound inside a vh clamp tracks the vh term exactly. Example: the portrait cap `min(62vh, 680px × S)` keeps the standing portrait proportional (669.6 → 892.8 at 1440). The band, page-text and log-text caps follow the same rule, so they keep tracking their vh term up to S = 1.4 instead of stopping at 1440.
- **Attribute-sized icons.** SVG icons whose only size was a `width`/`height` attribute (drawer header glyph and close, empty-state glyph, equipped check, reading-sample replay, skill search, vitals label icons, remembered-place marker) now take a scaled CSS box. The attribute stays as the intrinsic reference size.
- **Minimap.** The island's `latticeStyle` binds `calc(208px * var(--ui-scale, 1))`; the viewBox, pitch and label sizes in user units are unchanged, so the drawing only magnifies. The full-map overlay still measures its real body.
- **Radii.** The ladder is `--radius-sm` 5px, `--radius` 8px (was 7px) and `--radius-pill` 999px. Literal radii map as follows: 3–5px → sm, 6–18px → default, 99px and above → pill. Kept as geometry: 0, 50% circles, 1–2px caps, and derived inner radii such as `calc(var(--radius-sm) - 2px)`. This changes corners by at most a few pixels at S = 1; no box size changes.
- **Accepted drifts.** The command-line prompt and the log header already use chrome `--text-*` steps times `--prose-scale`, so they scale by S × prose scale. Browser zoom still enlarges everything, but above a 1080 CSS-px viewport height page zoom partly cancels S, because zooming reduces `innerHeight`; at 200% zoom on a 1440p screen S is 1 and text renders 1.5× larger than at 100%. A docked dev-tools panel changes `innerHeight` and therefore S.
- **Verification.** Vitest: `tests/ui_scale.test.js` covers the clamp boundaries, resize following and dispose. The source-text pins that encoded the old literals were updated or replaced with computed-style checks. Browser: `web/tests/browser/test_browser_proportional_ui_scale.py` renders the Storybook AppShell at 1920×1080 and 2560×1440 and checks that navigation, place card, minimap canvas and drawer header come out at 4/3 ±2px with the viewBox unchanged, and that page text, band and portrait also come out at 4/3 (scaled exactly once). It also checks that S = 1 at 1440×900, 1280×720 and on a narrow 1600×1440 window, that prose scale changes the page but not the chrome, and that resizing 1920 → 2560 → 1280 → 2560 still dispatches exactly one combat action from pointer clicks.
