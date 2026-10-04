# Design: face-crop-small-avatar-thumbnails

## Context

See proposal.md — Why. The diagnosis in one line: `faceObjectPosition` maps the rect center to a CSS `object-position` pair, which under `object-fit: cover` only re-centers the visible window; at 22–52px frames the window still spans most of a full-body portrait, so the marked face is barely visible. The server-side and payload contracts (normalized pixel-square rects, verbatim storage, per-surface stage rules) are settled and untouched; this is purely a client presentation mapping question.

Current consumers of `faceObjectPosition` in `web/webclient-app/components/face-rect.js`: CharacterSwitcher (pill + row thumbs), PartyDrawer (`.av-img`), GalleryPanel, GalleryDetailRail, ParticipantFrame, ReferenceArtwork (cover mode). Existing tests: `tests/data/face_rect.test.js` (helper), `tests/core/character_switcher.test.js` (pill + row thumb object-position), `tests/data/party_drawer.test.js` (avatar object-position), `tests/components/stage_transform.test.js` (ReferenceArtwork cover placement stays face-rect-driven).

## Goals / Non-Goals

**Goals:**
- One shared, pure, well-tested zoom mapping in `face-rect.js`; the three small-avatar bindings change from the raw `objectPosition` style to that mapping.
- Identical validation and fallback semantics as `faceObjectPosition`: same rejection set, same centered-crop result, no throw, no change to placeholder rendering.
- Every other framed-portrait surface keeps its exact current output.

**Non-Goals:**
- No zoom on gallery cards, gallery detail rail, participant frame, ReferenceArtwork, party strip, dialogue host avatar, interact/dock avatars.
- No stage-awareness in the zoom mapping; no server, payload, or `docs/game` change; no new Storybook surface (coverage gate must simply stay green).

## Decisions

**D1: Enlarge-and-anchor style, not object-position centering.** The mapping emits four frame-relative percentages for a well-formed rect: `width: 100/w %`, `height: 100/h %`, `left: -x·(100/w) %`, `top: -y·(100/h) %` — i.e. the img box is the reciprocal-size enlargement of the frame and is anchored so the rect's own image region lands exactly on the frame's box. (Anchoring by `-x/w`/`-y/h` is exact; centering an enlarged box on the frame and leaning on `object-position: cx%` is NOT — under p%-aligns-p% the face center lands at `2·(cx−50)%` of the box away from the frame center, and for the repo's near-symmetric fixtures the error is invisible, so the arithmetic here must be pinned with an asymmetric fixture, see D4.) Because server-validated rects are pixel-square, on a square frame the enlarged box's aspect `h/w` equals the image aspect `W/H` whenever `w·W ≈ h·H` holds, so `object-fit: cover` performs no interior crop and the anchor mapping is exact; interior crops only occur for legacy non-square rects, where the emitted centered `object-position: 50% 50%` keeps the crop box centered on the rect window's center. Percentages are frame-relative and fully assertable in jsdom, which has no layout engine. Rejected: `transform: scale()` + `translate` (origin math interacts badly with cover-fit's own cropping), and center-based `object-position` re-derivation (wrong, see above).
- Fallback shape: the exported signature is `faceCropStyle(rect, fallbackPosition = "50% 50%")`. For a rejected rect it returns `{ objectPosition: fallbackPosition }` and nothing else. The three call sites pass `faceCropStyle(rect, faceObjectPosition(rect))`, so a malformed rect produces exactly today's `{ objectPosition: "50% 50%" }`-shaped binding — one source of truth for the centering, byte-identical fallback. For a well-formed rect it returns `{ width, height, left, top, objectPosition: "50% 50%" }` (the object-position is inert for the exact pixel-square case and centers the crop box for the legacy non-square one).

**D2: Wrapper positioning mechanics live in CSS, the offsets in the helper.** The switcher wrappers (`character-switcher__thumb-wrapper`, `character-switcher__row-thumb-wrapper`) and the drawer's `.compbig .av` already clip with `overflow: hidden`; each gains `position: relative` and the small-avatar img classes keep their existing `width/height: 100%` class rule while gaining `position: absolute`. Inline styles outrank class rules, so a well-formed rect's bound `width/height/left/top` override the class size, and a rejected rect — whose bound style carries only `object-position` — still fills the frame through the class rule at exactly today's rendered box (auto `left/top` place an absolutely-positioned img at its static position, i.e. the frame's content origin, where 100%/100% fills it). `left`/`top` percentages resolve against the positioned ancestor = the frame box, and every named frame is square (22px, 24px, 52px, 42px), so the axis semantics are unambiguous. No JS-measured pixels anywhere.

**D3: Cap the enlargement.** Clamp each axis's enlargement factor to 8× (size ≤ `800%`), and derive the anchor offsets from the *clamped* factor (`left = -x × clampedFactor`), so a degenerate rect narrower than 1/8 of the image caps the box with the frame's window starting at the rect's near edge (the rect's marked region stays inside the frame, just smaller within it) instead of requesting a 10000%-wide img. The cap constant lives in `face-rect.js` beside the validation and is unit-tested.

**D4: Tests assert style attributes, not pixels — including an asymmetric fixture.** jsdom never lays out; the vitest suite already asserts `element.style.*`. `tests/data/face_rect.test.js` gains `faceCropStyle` unit cases: `{x:0.3,y:0.1,w:0.4,h:0.4}` → width 250%, height 250%, left -75%, top -25%; the asymmetric `{x:0.6,y:0.1,w:0.2,h:0.2}` → 500%/500%, left -300%, top -50% (this fixture is mandatory: every existing repo fixture is horizontally centered, so only an off-center rect distinguishes correct anchoring from the wrong center-based formula); the full rejection set → only the caller's fallback position; whole-image rect `{0,0,1,1}` → 100%/100% at 0/0; skinny `{0.49,0.49,0.02,0.02}` → 800%/800% at -392%/-392%. `tests/core/character_switcher.test.js`'s "offsets portrait crops by the payload face rect in both thumbnails" test is retargeted to assert width/height/left/top on pill and row thumb; `tests/data/party_drawer.test.js`'s avatar test likewise. `tests/components/stage_transform.test.js`'s ReferenceArtwork assertion (`object-position: 50% 50%;` only) must stay green unchanged — the regression guard that the non-small-avatar surfaces did not move. Placeholder/glyph tests in both component suites stay untouched.

**D5: Storybook fixtures already carry face_rect** (AppShell switcher rows, Overlays/PartyDrawer companion catalog, `stories/fixtures/core.js`, `stories/fixtures/party_panels.js`); no story changes planned beyond selector fallout, and `npm --prefix web/webclient-app run build-storybook` plus `... run showcase-coverage` stay green with no manifest change.

## Risks / Trade-offs

- [Rect aspect mismatch] A square frame with a pixel-square rect still cover-crops the enlarged box: if the source aspect leaves one axis overflowing, a sliver of the rect's side or top is cropped while the face fills the frame. Accepted — the contract is "substantially fills," and every gallery rect is pixel-square by server validation.
- [Enlarged img paint cost] ~2.5×-area rasterization for at most a handful of ≤52px avatars on screen. Negligible; browsers down-sample cover-fit images per frame.
- [Test churn on style shape] Existing tests assert exact `style.objectPosition` strings on these surfaces; retarget them in the same commit so `pnpm test` is green at the implementation HEAD.
- [Other-surface drift] Accidentally applying the zoom elsewhere is caught by leaving every other surface's binding untouched and keeping `stage_transform.test.js` and the gallery tests green byte-for-byte.

## Migration Plan

Purely additive helper + three template bindings + CSS one-liners; no data, payload, or protocol migration. Rollback = revert the implementation commit; the old object-position bindings return.
