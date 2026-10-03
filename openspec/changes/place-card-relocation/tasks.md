# place-card-relocation — Tasks

## 1. HudFrame anchor restructure

- [x] 1.1 Remove the `[data-anchor="place"]` div and its `#place` slot from `HudFrame.vue` template. Remove the `place` anchor CSS block (`.elosern-stage [data-anchor="place"] { … }`). Update the script comments that reference the `place` anchor.
- [x] 1.2 Simplify the `[data-anchor="vitals"]` CSS: change `top` from `calc(var(--header-h) + var(--stage-inset-y) + var(--place-h) + 12px * var(--ui-scale))` to `calc(var(--header-h) + var(--stage-inset-y))`. Update `max-height` to remove the `var(--place-h)` term.
- [x] 1.3 Remove the creation-mode hide rule for `[data-anchor="place"]` from HudFrame's mode-gated visibility block (the `map` anchor is already hidden in creation, which covers the relocated PlaceCard).
- [x] 1.4 Remove `place` from the HudFrame header comments (anchor list, layer descriptions). Update any comment that says "below the place card" to "directly below the top band".
- [x] 1.5 Update `HudFrame.stories.js`: the `renderFrame` story passes a `place: () => sample("place ‧ 地點卡")` slot — delete that slot key and fold the place-card sample into the `map:` slot (stacked above the minimap sample so the story shows the island grouping). Update the header/story description, which names the `place` anchor ("the place card (`place`, top-left, fixed `--place-h`)") and `--place-h`: describe the place card as an island of the top-right `map` anchor with no fixed height token.

## 2. AppShell slot reassignment

- [x] 2.1 In `AppShell.vue`, move the `<PlaceCard>` from `<template #place>` to `<template #map>`, rendering it as the first element before the minimap slot content. Ensure `locationLabel`, `timeLabel`, and `motionLevel` props are unchanged.
- [x] 2.2 In `AppShell.vue`, remove `[data-anchor='place']` from `HIDDEN_BY_MODE.creation` (the entry keeps `band-message`, `vitals`, `map`, and `command-line`): the anchor is gone, and the relocated card hides with the `map` anchor. The dialogue-mode rescue selector logic is unchanged.

## 3. PlaceCard visual adjustments

- [x] 3.1 In `PlaceCard.vue`, change the location heading font from `var(--text-xl)` to `var(--text-lg)`. The heading should still use `var(--f-serif)` with `letter-spacing: 0.12em`.
- [x] 3.2 Shorten the gold rule from `calc(64px * var(--ui-scale))` to `calc(40px * var(--ui-scale))`.
- [x] 3.3 Remove the fixed-height `height: 100%` on `.place-card` and let it auto-size within the map anchor's flex column. The card should size to its content (heading + rule + time) rather than filling a fixed anchor height. Adjust `align-content: center` to `align-content: start` since the card is no longer in a fixed-height anchor.
- [x] 3.4 Update the PlaceCard component header comment to reference its new position: "the place card in the `map` anchor at the top of the right-hand island column".
- [x] 3.5 Update `PlaceCard.stories.js`: both story wrappers size the card at the old `place` anchor (`width:298px;height:var(--place-h)`) and the file header comment says the same. Size them like the `map` anchor island (`width: calc(230px * var(--ui-scale))`, auto height) and drop the `--place-h` reference from the comment.

## 4. Design tokens

- [x] 4.1 Delete the `--place-h` token from `tokens.css` (the `:root` block near `--header-h`) AND from `app-shell.css`, which re-declares it inside the `@media (max-height: 820px)` block (`--place-h: calc(56px * var(--ui-scale));`) — that media block keeps its `--stage-inset-y` line. After tasks 1.2/5.1 nothing references the token.

## 5. Mirror CSS in app-shell.css

- [x] 5.1 In `app-shell.css`, update the mirrored `[data-anchor="vitals"]` rule (its `top` and `max-height` reference `--place-h`) exactly as HudFrame's rule changes in 1.2, and remove the place-anchor offset comment (the file's comment says "keep the two in step" with HudFrame's anchor CSS).

## 6. Tests and stories

- [x] 6.1 Update `place_card.test.js`'s wiring pin: it asserts HudFrame's creation-mode hide line for `[data-anchor="place"]`, `AppShell.vue`'s `creation: "[data-anchor='place']…` string, and that `tokens.css` contains `--place-h: calc(68px * var(--ui-scale));`. Re-point it at the post-change truth (no `place` anchor in HudFrame or AppShell; no `--place-h` token; the map anchor hides in creation).
- [x] 6.2 Update `app.test.js` / `hud_frame.test.js` if they assert the existence of the `place` anchor div or test the slot assignment.
- [x] 6.3 Update the browser-test assertions that measure `[data-anchor="place"]`: `web/tests/browser/test_browser_layout.py` (mode-visibility selector list), `test_browser_proportional_ui_scale.py` (the `place: box(...)` entry — replace with the place card inside the `map` anchor), and `test_browser_shell_surfaces.py` (the `place: rect(...)` blocker probe — measure the place card element or drop the entry, keeping the band/commandLine blockers). These are managed-suite files: edit them here, execution is CI-owned; do not run the managed browser suite locally.
- [x] 6.4 Run the focused Vitest tests (`pnpm test` scoped to the touched test files) and the Node gate (`node --test web/static/webclient/js/tests/*.test.js`, fast per AGENTS.md) to verify no regressions. No full-suite runs.

## 7. Spec delta sync

- [x] 7.1 Verify `openspec validate place-card-relocation --strict` passes after implementation.
- [x] 7.2 Run `uv run --locked python -m tools.contract_gate` (seconds; traceability + lints + shard manifests — not a test run; required before handoff).
- [x] 7.3 Run the Storybook gates: `pnpm run build-storybook` (offline showcase builds with the relocated card) and `pnpm run showcase-coverage` (component-coverage check against the frozen required-set manifest — PlaceCard stays covered, nothing added/removed).
