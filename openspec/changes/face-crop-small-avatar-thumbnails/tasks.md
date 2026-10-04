# Tasks — face-crop-small-avatar-thumbnails

TDD: where a task changes behavior the suite pins, amend/extend the pinning test in the same
task and run it before and after. Unit-level pins are the Vitest suite
(`npm --prefix web/webclient-app test`). Requirement IDs cited are the amended/added
`webclient-art-panel` requirements of this change's delta spec.

## 1. The shared zoom mapping (design D1/D3)

- [ ] 1.1 Amend `web/webclient-app/tests/data/face_rect.test.js` with a `faceCropStyle`
      describe block first, pinning (design D1/D4: sizes `100/w`/`100/h`, anchors
      `left = -x·size_w`, `top = -y·size_h`): `{x: 0.3, y: 0.1, w: 0.4, h: 0.4}` →
      `width 250%, height 250%, left -75%, top -25%`; the asymmetric `{x: 0.6, y: 0.1,
      w: 0.2, h: 0.2}` → `500%/500%, left -300%, top -50%` (mandatory — every existing repo
      fixture is horizontally centered, and only an off-center rect separates this mapping
      from a wrong center-based one); whole-image rect `{x: 0, y: 0, w: 1, h: 1}` →
      `100%`/`100%` at `0%`/`0%`; the full rejection set (null, undefined, non-finite field,
      out-of-bounds field, `x + w > 1`, `y + h > 1`, non-positive `w`/`h`) → exactly
      `{ objectPosition: <caller's fallback> }` with no width/height/left/top keys; a skinny
      rect `{x: 0.49, y: 0.49, w: 0.02, h: 0.02}` clamps to `800%`/`800%` with anchors from
      the clamped factor (`-392%`/`-392%`). Verify the new block fails before the helper exists.
- [ ] 1.2 Implement `faceCropStyle(rect, fallbackPosition = "50% 50%")` in
      `web/webclient-app/components/face-rect.js`: reuse the existing well-formedness gate and
      `pct()` rounding (share them, don't duplicate them — one validation source of truth);
      per-axis enlargement `1/w` × `1/h` clamped to the module-level 800% cap with the
      `left`/`top` percent anchors derived from the clamped factors, plus a centered
      `objectPosition` for the legacy non-square interior-crop case (design D1); a rejected
      rect returns only `{ objectPosition: fallbackPosition }`; update the file header comment
      to name both mappings and the small-avatar surfaces. `faceObjectPosition` itself is
      unchanged.

## 2. The three small-avatar bindings (delta: small-avatar zoom-crop requirement)

- [ ] 2.1 Amend `web/webclient-app/tests/core/character_switcher.test.js`: retarget
      "offsets portrait crops by the payload face rect in both thumbnails" to assert the zoom
      shape on `img.character-switcher__thumb` and `img.character-switcher__row-thumb`
      (width `250%`, height `250%`, left `-75%`, top `-25%` from the sample rect
      `{x: 0.3, y: 0.1, w: 0.4, h: 0.4}`); keep the placeholder tests unchanged; add one case
      pinning a URL-bearing character whose `face_rect` is null falls back to
      `object-position: 50% 50%` with no width/height/left/top style on the pill thumb.
- [ ] 2.2 `web/webclient-app/components/CharacterSwitcher.vue`: bind both thumbs
      (`:style="faceCropStyle(..., faceObjectPosition(...))"`, design D1); give
      `__thumb-wrapper` / `__row-thumb-wrapper` `position: relative` and the two thumb img
      classes `position: absolute` (design D2); the `overflow: hidden` clipping and 22/24px
      circular boxes and the class-rule `width/height: 100%` fallback stay as-is.
- [ ] 2.3 Amend `web/webclient-app/tests/data/party_drawer.test.js`: retarget "offsets the
      companion avatar crop by the catalog face rect" to the zoom anchor shape on the row's
      `img` (`500%`/`500%` at `-300%`/`-50%` if the fixture's catalog rect is changed to the
      asymmetric `{x: 0.6, y: 0.1, w: 0.2, h: 0.2}`, or `250%`/`250%` at `-75%`/`-25%` on the
      existing `{x: 0.3, y: 0.1, w: 0.4, h: 0.4}`); add the null-`face_rect` centered-fallback
      case mirroring 2.1.
- [ ] 2.4 `web/webclient-app/components/PartyDrawer.vue`: bind `av-img` through the same
      `faceCropStyle(...)` mapping; give `.compbig .av` `position: relative` and `.av-img`
      `position: absolute` (design D2); `overflow: hidden`, the 42–52px box, and the
      `av-glyph` placeholder branch stay untouched.

## 3. Non-touch regression guards

- [ ] 3.1 Confirm byte-unchanged bindings for the recenters-only surfaces:
      `GalleryPanel.vue`, `GalleryDetailRail.vue`, `ParticipantFrame.vue`,
      `ReferenceArtwork.vue`, party strip / dialogue host / interact / dock avatars keep
      `faceObjectPosition`. `tests/components/stage_transform.test.js` (cover placement →
      `object-position: 50% 50%;`) and the gallery tests must pass with zero edits — that is
      the guard.
- [ ] 3.2 Confirm the placeholder contracts did not move: `tests/drawer_content_polish.test.js`,
      the switcher placeholder tests, and `tests/app_client_drawers.test.js` (null-URL roster
      portrait fixture) pass untouched.

## 4. Gates and sweep

- [ ] 4.1 `npm --prefix web/webclient-app test` (Vitest) green.
- [ ] 4.2 `npm --prefix web/webclient-app run build-storybook` and
      `npm --prefix web/webclient-app run showcase-coverage` green with no manifest/required-set
      change; the existing AppShell switcher and Overlays/PartyDrawer stories exercise the new
      crop through their committed `face_rect` fixtures — no new story required.
- [ ] 4.3 Traceability: `uv run --locked python -m tools.spec_traceability list` shows the two
      requirement IDs (amended recenters-only requirement + added small-avatar zoom-crop
      requirement) covered by the amended tests; `check` green. No new test module → no
      `.github/evennia-shards.json` change.
- [ ] 4.4 Confirm non-touches: `docs/game/**` unchanged (no command surface), no server/`world/**`
      edits, no payload/schema edits, legacy `web/static` text-client suite untouched.
- [ ] 4.5 `openspec validate face-crop-small-avatar-thumbnails --strict` green.
