## 1. Pin down the exact current DOM and existing test surface

- [x] 1.1 Grep `web/tests/browser/` and `web/webclient-app/tests/` for every
      `character-status-drawer__{vital,trait,condition,guild,section}` selector and confirm each asserts
      only on `data-testid`/text content, not on a structural class name (`.character-status-drawer__vital`,
      `.character-status-drawer__condition`, etc.) that this change's markup restructuring removes. List any
      that do, so task 4 updates them alongside the template change.
- [x] 1.2 Confirm (by reading `ConditionChips.vue:211-244`) the exact five `.chip--{beneficial,
      informational,warning,harmful,critical}` background/border-color/color triples to reuse verbatim for
      the new pill variants — no new colour value is invented.

## 2. Add the shared section-heading pattern

- [x] 2.1 Add a `character-status-drawer__section-label` element (a `<p>` or `<span>`, matching
      `ConditionChips.vue`'s `.clab` markup shape) as the first child of each of the drawer's six sections
      (vitals, traits, conditions, guild, disguise, persona — when persona renders), with the section's name
      (生命量/屬性/狀態/計數 · 公會/偽裝/背景) as its text, and give it the shared small-caps style
      (`font-size:10px; letter-spacing:.14em; color:var(--paper-500); text-transform:uppercase` — copied
      from `ConditionChips.vue`'s `.clab` rule, not imported).

## 3. Re-chrome vitals, traits, and guild counters as card tiles

- [x] 3.1 Wrap the vitals section's three rows in a `.character-status-drawer__statgrid` grid container
      (`display:grid; grid-template-columns:1fr 1fr; gap:8px`) and restyle each row as a
      `.character-status-drawer__statrow` tile (`background:var(--ink-820); border:1px solid
      var(--ink-700); border-radius:9px; padding:9px 12px`), keeping each row's existing
      `character-status-drawer__vital--<key>` testid on the tile element, the label styled per the
      design's `.statrow .k` rule, and the `current / maximum` value per `.statrow .v` (gold monospace).
      Per design.md's risk analysis, stack the tile's contents on two lines (label+value on the first
      line, the fill-bar track spanning the full tile width on the second line) rather than one
      `align-items:center` row — the halved tile width (vs. today's full-width row) does not reliably fit
      label + track + the conditional `危險` marker + numeral on a single line, especially for the HP tile.
- [x] 3.2 Apply the same `statgrid`/`statrow` treatment to the traits section's rows
      (`character-status-drawer__trait--<key>`), rendering exactly `row.label` and `traitValue(row)` inside
      each tile — no delta/effective-vs-base figure is added, since the payload carries none (design.md
      Non-Goals).
- [x] 3.3 Apply the same treatment to the two guild-counter rows (`character-status-drawer__guild-rank`,
      `character-status-drawer__guild-merit`), grouped in their own `statgrid` under the "計數 · 公會"
      heading from task 2.1.

## 4. Re-chrome the condition roster as pill badges

- [x] 4.1 Replace the condition roster's flex-row markup with a `.character-status-drawer__pillrow`
      container (`display:flex; flex-wrap:wrap; gap:7px`) of `.character-status-drawer__pill` elements —
      one per condition, keeping the existing `character-status-drawer__condition--<code>` testid on the
      pill — each rendering the condition's label plus a trailing muted suffix carrying its visible
      `SEVERITY_LABELS` word, its non-colour severity glyph, and its timer/modifier text. This is a
      relayout of the SAME content the current flat row shows (nothing dropped — the severity word stays
      visible, not just the `aria-hidden` glyph), styled per the design's `.pill` rule
      (`font-size:12px; padding:5px 11px; border-radius:99px; border:1px solid var(--ink-600);
      background:var(--ink-780); color:var(--paper-300)`).
- [x] 4.2 Apply the five severity tint variants from task 1.2 to the pill (`background`/`border-color`/
      `color` per `condition.severity`), matching `ConditionChips.vue`'s existing mapping exactly.
- [x] 4.3 Confirm the empty state (`character-status-drawer__conditions-empty`, "無狀態") still renders as
      plain text beneath the new "狀態" heading, not as an empty pill row.

## 5. Update any structural-selector tests found in task 1.1

- [x] 5.1 Update each test flagged in task 1.1 to select on the preserved `data-testid`/text content
      instead of the removed structural class, with no change to what the test actually asserts.

## 6. Verify

- [x] 6.1 Extend the existing `web/webclient-app/stories/Data/CharacterStatusDrawer.stories.js`
      (title `Data/CharacterStatusDrawer`, already frozen in `component-manifest.json` — do not create a
      new file or a new title) with a populated state (resources, traits, a multi-severity condition
      roster, guild rank) and a degraded state (`character.available: false`), so the new grid/pill chrome
      is visible in Storybook for both.
- [x] 6.2 Add a component test asserting the new section-heading elements are present for each section and
      that the condition pills carry the correct severity-based class/colour per `condition.severity`.
- [x] 6.3 Add a browser or Vitest bounding-box assertion (reusing the non-intersection pattern from
      `fix-webclient-local-map-node-crowding`) that no stat tile or pill overlaps or clips its own text at
      1440×900 and 1280×720, including a roster of 8+ conditions (more than the H2 island's 6-item cap) to
      exercise the pill row's wrap behavior.
- [x] 6.4 Re-run the full existing `character-status-drawer` test suite (component + browser) to confirm no
      regression beyond the intended visual change — same testids, same values, same degrade-by-section
      behavior.
- [x] 6.5 Re-screenshot the live client's `角色狀態` drawer at 1440×900 and visually confirm it now matches
      the design's card-tile/pill-badge/section-heading presentation.

## 8. Protocol integer-bound fix (found in implementation verification)

- [x] 8.1 Relax the global JSON-safety integer bound to the full JavaScript-safe range in
      `web/static/webclient/js/elosern/protocol.js` (`checkGlobalSafety`) and its Python mirror in
      `web/webclient/presentation/protocol.py` (`check_json_safety`), so the deterministic
      `combat_modifiers.yaml`'s signed modifier values (`defense: -15`, `accuracy: -10`) pass the
      client's `validateStatusCondition` and reach the drawer.
- [x] 8.2 Add regression tests in `web/static/webclient/js/tests/protocol.test.js` (negative safe
      integers pass, out-of-range fails, status panel with signed modifiers validates) and in
      `web/webclient/presentation/tests/test_protocol.py` (negative safe integers pass, below-range
      fails).
- [x] 8.3 Add a `webclient-oob-protocol` delta spec recording the modified global-bounds requirement
      and the negative-safe-integer scenario.

## 7. Close out

- [x] 7.1 `openspec validate align-webclient-character-status-drawer-chrome --strict`.
- [x] 7.2 Run the focused JS gates (`npm test`, Storybook build + component-coverage) and the smallest
      browser class covering `character-status-drawer` / `test_browser_art.py`'s HUD-drawer coverage.
