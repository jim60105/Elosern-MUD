# Tasks — retarget-browser-acceptance-viewports

Depends on `retarget-desktop-viewport-contract` landing (the amended requirement texts supply
every expected value; design D2). TDD order: retarget the shared base first, then the tuple
modules, then the per-journey absolute assertions, then the requirement-text deltas were already
authored to match.

## 1. Shared base

- [ ] 1.1 `web/tests/browser/browser_base.py`: `DEFAULT_VIEWPORT = (1451, 790)` (was
      `(1440, 900)`). Every journey that does not pass an explicit viewport now opens at the
      reference; verify the shell-journey module passes on the dependency change's build.
- [ ] 1.2 If `browser_base.py` (or a shared helper) names the iteration tuple, change it once:
      `((1451, 790), (1741, 948), (2560, 1440))`. Otherwise proceed module by module (task 2).

## 2. Viewport tuples

- [ ] 2.1 `grep -rln "1920, 1080" web/tests/browser/` — in every module, replace the
      `((1920, 1080), (1440, 900), (1280, 720))` iteration with
      `((1451, 790), (1741, 948), (2560, 1440))`, and any two-size pair with
      `((1451, 790), (2560, 1440))`. Keep per-module skips/xfails as they are; do not add
      journeys.
- [ ] 2.2 Re-point size-driven assertions to the dependency change's amended values (from the
      delta spec texts, not renders): bottom band 220px at 1451x790 (401px at 2560x1440), top
      band 48px, stage box >= 513.5px at reference, island canvas 240px at reference /
      336px (±1) at 2560x1440 / 288px (±1) at 1741x948, message page text 18px (±0.5) at the
      reference with default prose scale (16px at `A−`, 20px at `A+`), every visible text
      >= 16px at the reference including drawn-map labels. Modules that scaled off the old
      tuple's 4/3 at 2560x1440 (e.g. proportional-scale and island-magnification journeys)
      re-pin to the 1.4 cap.
- [ ] 2.3 Any module whose fixture observations cite the old fitted-label numbers (island
      scale 0.933, labels 11.2px, pitch 59) re-pins to the amended map scenarios: scale 1,
      labels 16px, pitch 60 at the reference; viewport-count-sensitive remembered-list and
      constant-size scenarios use the single reference viewport under test.

## 3. Suite runs

- [ ] 3.1 Run the managed localhost Playwright suites green at the new tuple (the repo's
      browser-suite invocation), including the shell journey, overlay journey, mode-gating,
      reconnect, dialogue stage journey (now at 1451x790), minimap-in-island, and complete-log
      journeys. Red journeys are fixed against the spec text (D2); if the dependency's geometry
      is at fault, fix it there and note the cross-change fix in this change's PR description.

## 4. Gates

- [ ] 4.1 `openspec validate retarget-browser-acceptance-viewports --strict` green.
- [ ] 4.2 Partition and completeness gates: the two changes' delta requirement sets are disjoint
      (compare the `### Requirement:` lists under both `openspec/changes/*/specs/`); after both
      deltas are applied, `grep -rE "1440x900|1280x720|1920x1080" openspec/specs/` names no
      requirement (simulate by checking no main-spec requirement amended here still carries the
      old literals and no requirement left unamended carries them — the retarget change's
      sweep covers its own capabilities).
- [ ] 4.3 `uv run --locked python -m tools.spec_traceability check` green (amended requirements
      keep their covering test IDs; the browser modules' `covers_requirement` annotations are
      unchanged by a tuple edit).
- [ ] 4.4 Confirm non-touches: `.github/evennia-shards.json` unchanged (no new test modules),
      `web/webclient-app/` untouched, `docs/game/` untouched.
