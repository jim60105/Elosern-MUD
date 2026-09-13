## 1. Component family

- [x] 1.1 Build `GalleryPanel`: subject rail, five server-counted filters,
  committed-order grid/list cards, default crown, pending/failed states and
  shared face-position thumbnail anchoring.
- [x] 1.2 Build `GalleryDetailRail`: selected portrait, default/binding facts,
  explicit warning condition lines or unavailable copy, default/edit/face actions,
  and inline delete confirmation; no invented resolved-current-image state.
- [x] 1.3 Build `GalleryGenerateDrawer`: five capability-gated data fields,
  equipment summary, puppet-only character shortcut, raw Unicode prompt/counter,
  request/revision-correlated completion and rejection recovery via the full log.
- [x] 1.4 Build `GalleryBindingDrawer`: checkbox-only nonempty slot mask,
  committed current equipment, explicit warning lines and card-selection jumps;
  no item picker, stored-mask inference or client rule matching.
- [x] 1.5 Build `GalleryFaceRectModal`: original image, normalized pointer
  move/resize with bounds and cancellation, keyboard numeric controls, exact
  aspect-preserving square-frame preview, save/cancel and opener restoration.
- [x] 1.6 Apply Traditional Chinese static chrome and closed catalog copy,
  verbatim server labels/chips/equipment/warnings, UTC timestamps, and independent
  capability gates including single-card monster replacement.

## 2. App wiring

- [x] 2.1 Register the existing gallery overlay controller, add the
  availability-gated portrait-area opener, and mount the family through
  `OverlayHost` with shared connection/mutation/in-flight gates and dispatcher.
  Invalidate stale editors on subject/card/unavailable/transport transitions.
- [x] 2.2 Wire deletion confirmation; cancellation sends nothing and confirmation
  sends one shared-path action without optimistic removal.

## 3. Verification

- [x] 3.1 Add component behavior tests covering all five components: facts and
  filters, Unicode input, capabilities, warning rendering, confirmation, focus,
  request/revision correlation, empty-gallery publications and non-square geometry.
- [x] 3.2 Add application integration tests using the real store and protocol:
  availability, shared action payloads, global lock, rejection narrative exactly
  once, retained drafts, full-log access and transport teardown.

## 4. Storybook and storyboard

- [x] 4.1 Add deterministic stories under `Data/GalleryPanel`,
  `Data/GalleryDetailRail`, `Overlays/GalleryGenerateDrawer`,
  `Overlays/GalleryBindingDrawer`, `Overlays/GalleryFaceRectModal`, covering
  populated, empty, monster, pending/failed, unavailable and rejected states.
- [x] 4.2 Add all five titles to the frozen component manifest before live app
  wiring; pass the production and Storybook builds and showcase-coverage gate.
- [x] 4.3 Add the interactive `Data/GalleryPanel/Storyboard` and English
  `docs/design/elosern-redesign2/gallery-storyboard.md` frame guide. View all four
  reference images and exercise browse, generation/rejection, binding, real pointer
  face editing, confirmation and monster/focus flows in Chromium.

## Evidence

- Final complete Vitest gate: 92 files / 978 tests passed, including all 19
  focused gallery tests and the three added lifecycle/focus regressions.
- Vite production build, Storybook static build and showcase coverage passed;
  the frozen manifest has 56 registered/required component titles.
- The legacy Node contract gate caught an undefined body-font token; the gallery
  now uses the existing `--f-sans` token rather than inventing a parallel token.
  The complete Node gate then passed all 453 tests.
- Chromium: draft retained after rejection; successful matching publication closes
  generation; binding is initially disabled until a slot is chosen; non-square
  image drag updates normalized coordinates; crop save sends only identity and
  rectangle; delete cancellation preserves 8 cards and confirmed publication
  reduces to 7; monster exposes no input fields; Escape restores the clicked CTA.
- Repeated visual verification in a dedicated headed Wayland Chromium window;
  default selection changes only after publication, and face-editor cancellation
  returns to the gallery. Specification traceability: 1512 requirements covered,
  zero uncovered and zero errors. OpenSpec reports 13/13 tasks complete.
- No Python code, player commands, main specs, archive or branch merge changed.
- Final synchronous Rubber Duck review found no blockers. No null-rectangle
  fallback was added because completed cards are protocol-validated; no second
  shared-drawer teardown restore was added because the host and editor coordinator
  already own restoration. Added late-result-after-cancel and detached-opener
  focus regressions in response to the review's concrete test suggestions.
