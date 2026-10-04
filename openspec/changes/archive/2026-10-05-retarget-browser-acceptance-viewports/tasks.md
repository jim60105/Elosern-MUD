# Tasks — retarget-browser-acceptance-viewports

Depends on `retarget-desktop-viewport-contract` landing (the amended requirement texts supply
every expected value; design D2). TDD order: retarget the shared base first, then the tuple
modules, then the per-journey absolute assertions, then the requirement-text deltas were already
authored to match.

## 1. Shared base

- [x] 1.1 `web/tests/browser/browser_base.py`: `DEFAULT_VIEWPORT = (1451, 790)` (was
      `(1440, 900)`). Every journey that does not pass an explicit viewport now opens at the
      reference; verify the shell-journey module passes on the dependency change's build.
- [x] 1.2 If `browser_base.py` (or a shared helper) names the iteration tuple, change it once:
      `((1451, 790), (1741, 948), (2560, 1440))`. Otherwise proceed module by module (task 2).

## 2. Viewport tuples

- [x] 2.1 `grep -rln "1920, 1080" web/tests/browser/` — in every module, replace the
      `((1920, 1080), (1440, 900), (1280, 720))` iteration with
      `((1451, 790), (1741, 948), (2560, 1440))`, and any two-size pair with
      `((1451, 790), (2560, 1440))`. Keep per-module skips/xfails as they are; do not add
      journeys.
- [x] 2.2 Re-point size-driven assertions to the dependency change's amended values (from the
      delta spec texts, not renders): bottom band 220px at 1451x790 (401px at 2560x1440), top
      band 48px, stage box >= 513.5px at reference, island canvas 240px at reference /
      336px (±1) at 2560x1440 / 288px (±1) at 1741x948, message page text 18px (±0.5) at the
      reference with default prose scale (16px at `A−`, 20px at `A+`), every visible text
      >= 16px at the reference including drawn-map labels. Modules that scaled off the old
      tuple's 4/3 at 2560x1440 (e.g. proportional-scale and island-magnification journeys)
      re-pin to the 1.4 cap.
- [x] 2.3 Any module whose fixture observations cite the old fitted-label numbers (island
      scale 0.933, labels 11.2px, pitch 59) re-pins to the amended map scenarios: scale 1,
      labels 16px, pitch 60 at the reference; viewport-count-sensitive remembered-list and
      constant-size scenarios use the single reference viewport under test.

## 3. Suite runs

- [x] 3.1 Run the managed localhost Playwright suites green at the new tuple (the repo's
      browser-suite invocation), including the shell journey, overlay journey, mode-gating,
      reconnect, dialogue stage journey (now at 1451x790), minimap-in-island, and complete-log
      journeys. Red journeys are fixed against the spec text (D2); if the dependency's geometry
      is at fault, fix it there and note the cross-change fix in this change's PR description.
      Verified locally with focused per-module runs (AGENTS.md's budget: one class/file at a
      time; the full managed suite stays CI-owned): proportional-ui-scale, vue-typography,
      chrome-navigation, map-legibility, local-map-geometry, local-map-lattice,
      contextual-hud-dock/stage/anchors/drawers, shell-surfaces, shell-command-line,
      shell-dock, vue-foundation, layout, input-narrative — all green. The red journeys that
      surfaced are fixed: the two `webclient-app` floor carve-outs (4.4) and the assertions
      whose expected values still carried the retired reference (see the commit messages).
      One deviation is recorded rather than fixed here: with the full-log overlay open, a line
      appended to the response being read re-pages the message window from page 1 to page 2
      while the window's box (720x162 at 16px) and its page count (4) stay unchanged. The
      clause it touches, "Lines appended to the response being read SHALL NOT move the reader
      off the page on screen" (`webclient-input-narrative::the-message-window-s-reading-
      controls-advance-pages-and-a-new-action-flushes-unread-pages`), stays asserted by that
      requirement's own journeys (`test_message_window_pages_and_flushes`,
      `test_message_window_repages_on_resize`) and by webclient-shell
      `test_paging_marker_and_append_keep_page`, all green; the log-open state is a follow-up
      investigation (MessageWindow.repage's same-response anchor mapping).

## 4. Gates

- [x] 4.1 `openspec validate retarget-browser-acceptance-viewports --strict` green.
- [x] 4.2 Partition and completeness gates: the two changes' delta requirement sets are disjoint
      (compare the `### Requirement:` lists under both `openspec/changes/*/specs/`); after both
      deltas are applied, `grep -rE "1440x900|1280x720|1920x1080" openspec/specs/` names no
      requirement (simulate by checking no main-spec requirement amended here still carries the
      old literals and no requirement left unamended carries them — the retarget change's
      sweep covers its own capabilities).
- [x] 4.3 `uv run --locked python -m tools.spec_traceability check` green (amended requirements
      keep their covering test IDs; the browser modules' `covers_requirement` annotations are
      unchanged by a tuple edit).
- [x] 4.4 Confirm non-touches: `.github/evennia-shards.json` unchanged (no new test modules),
      `docs/game/` untouched, and `web/webclient-app/` untouched **except** the floor carve-outs
      the retargeted journeys exposed (`MessageWindow.vue` plate name, `tokens.css`
      `.ui-icon-btn`, `FoeLineup.vue` placeholder label — the last latent, changed at the source
      against `webclient-vue-application` "Chrome type is legible and numerals are stable";
      design.md's Non-Goal records the carve-out). `.github/browser-shards.json` necessarily
      changed with the renamed viewport-named test methods.
