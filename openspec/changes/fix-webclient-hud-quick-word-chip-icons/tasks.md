## 1. Glyph table

- [ ] 1.1 In `web/webclient-app/components/dock-icons.js`, add a new `get` entry to `GLYPHS` with the
      path `M6 11V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4M4 11h16v9H4z` (copied verbatim from
      `docs/design/elosern-redesign/index.html:870`).
- [ ] 1.2 Add a Vitest assertion that `glyphPath("get")` returns the new path, alongside the existing
      dock-icons coverage (or the new test file the sibling `fix-webclient-hud-dock-guidance-and-icons`
      change adds, if it has already landed).

## 2. Chip icons

- [ ] 2.1 In `web/webclient-app/components/QuickWordChips.vue`, import `glyphPath` from `./dock-icons.js`
      and render a leading 14px `aria-hidden="true"` `<svg><path :d="glyphPath(...)" stroke="currentColor"
      fill="none"/></svg>` inside each chip button, before the existing text label. Map verbs to keys:
      看→`look`, 拿→`get`, 說→`interact`, 交談→`character`, 等待→`wait`, 施法→`suggestions`.
- [ ] 2.2 Add `display: inline-flex; align-items: center; gap: 6px;` to `.qwc__chip` (it currently has
      neither `display: inline-flex` nor `align-items` — verify before assuming a flex layout already
      exists) — mirroring `DockTabBar.vue`'s `.dock-tab-bar__tab` icon+label convention. Keep the chip's
      overall padding/height otherwise unchanged.
- [ ] 2.3 Add a Vitest assertion that every rendered chip (exploration and combat sets) contains exactly
      one `aria-hidden` icon element alongside its text label.

## 3. Stories and verification

- [ ] 3.1 Update `web/webclient-app/stories/Core/QuickWordChips.stories.js`'s existing
      `ExplorationSet`/`CombatSet`/`CreationSet` stories (already offline-deterministic — no change
      needed to their args) and visually confirm each chip renders its icon correctly in Storybook.
- [ ] 3.2 Confirm `openspec validate fix-webclient-hud-quick-word-chip-icons --strict` passes against the
      delta spec in `specs/webclient-contextual-hud/spec.md`.
- [ ] 3.3 Run the focused test slice: `npm test -- quick_word` (or the component's existing test file
      name) plus the new/extended dock-icons assertion.
- [ ] 3.4 Re-check the live client (`podman compose`, `http://localhost:4001/webclient/`) with
      `agent-browser`: confirm each exploration chip (看/拿/說/交談/等待) and, in combat, each combat chip
      (說/施法) renders its icon, and that no chip's clickable behavior (inserting text, focusing the
      field) changed.
