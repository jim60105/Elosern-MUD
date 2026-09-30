## Context

See proposal.md (Why) for the motivation. Current state that shapes the approach:

- `web/webclient-app/styles/fonts.css` holds about 6000 lines of `@font-face` rules extracted from the
  design draft's Google Fonts CSS. Iansui (108), Noto Sans TC, and Noto Serif TC slices live under
  `web/webclient-app/fonts/<family>/` and are referenced relatively (`url(../fonts/...)`). Vite
  content-hashes each slice into `web/static/webclient/app/dist/assets/` and rewrites the URLs to
  `/static/webclient/app/dist/assets/<name>-<hash>.woff2`. Assets smaller than Vite's default 4 KB
  `assetsInlineLimit` are base64-inlined into `index.css` instead (321 source slices produce 313
  emitted files today).
- `fonts.css` is imported by `web/webclient-app/main.js` and `.storybook/preview.js`.
  `tests/test_design_draft_contract.py` guards the design draft's own copy under `docs/design/`, not
  the app copy.
- `--f-mono` is used by 23 production selectors (CommandLine, HelpOverlay, ActionDock, DockMenu,
  MapOverlay, DialogueChoices, ParticipantFrame, PartyStrip, LocalMap, `map-lattice.css`,
  MessageWindow `.narrative-line.map-art`, FullLogOverlay). Only PartyStrip requests weight 700; no
  monospace selector requests italic, except that a box-drawing `err` line would inherit
  `.narrative-line.err { font-style: italic }`.
- `.narrative-line.map-art` is applied to any line containing U+2500–U+257F, including the CJK headings
  that commands emit (`── 稱號冊 ──`, `　　─ <basis>`), so monospace lines mix Hack-width glyphs with
  full-width CJK.
- Map geometry bounds assume each label code point advances at most one type step:
  `use-map-lattice-geometry.js` (`labelClearancePitch`, argued for full-width CJK with "ASCII is
  narrower"), `MapLattice.vue` `markerNameFont`, and `use-map-lattice-render.js`
  `MARKER_NAME_ASCENT = 11`.

Research measurements (Hack v3.003, taken during the proposal from the upstream TTFs with fontTools
4.66.1 and a Chromium probe page served over HTTP and inspected with agent-browser):

| Metric | Value |
| --- | --- |
| unitsPerEm | 2048 |
| Advance (every glyph, including box drawing) | 1233 = 0.602 em |
| hhea ascent / descent / lineGap | 1901 / −483 / 0 (`line-height: normal` ≈ 1.164 em) |
| cmap size | 1548 code points; no CJK, no U+2328 ⌨, no U+2715 ✕, no 「」 |
| Covers | ASCII, Latin-1, Latin Extended, Greek, Cyrillic, Armenian, Georgian, arrows ←↑→↓, box drawing U+2500–257F, blocks, geometric shapes ▲◆▽▼◈, math, powerline PUA |
| Probe: `M×10` at 11 px | 66.23 px (current local stack: 66.00 px) |
| Probe: line box at 11 px / 16 px | 13 px / 19 px (current local stack: 14 px / 21 px) |

Hack is derived from DejaVu Sans Mono and keeps its advance and vertical metrics, so a machine that
already rendered DejaVu Sans Mono sees nearly no geometry change. The measured 1–2 px line-box drop came
from the developer machine, where the current stack resolved to a different installed monospace family.

## Goals / Non-Goals

**Goals:**

- Hack draws every Latin, digit, punctuation, arrow, and box-drawing glyph in a monospace context on
  every machine, from the project origin.
- The shipped files are small, independently cacheable unicode-range slices, following the same
  pattern as Iansui.
- The slices can be regenerated from upstream with one command and produce the same bytes.
- Tests assert the rendered face (Hack web font), not just the computed `font-family` string.

**Non-Goals:**

- `<link rel="preload">` for Hack. Slice URLs are content-hashed by Vite and not known to the Django
  template. The same pattern is used for every other family, and `unicode-range` already restricts
  downloads to slices the page draws. `font-display: swap` behaves the same as for the other families.
- Italic and bold-italic faces. No monospace selector asks for italic; the rare inherited italic on an
  `err` map-art line is synthesized by the browser.
- A monospace CJK face. CJK in monospace contexts keeps using the bundled Noto Sans TC. The map
  geometry already budgets CJK at one em.
- Replacing HelpOverlay's deliberate routing of non-ASCII legends (⌨, arrows) to `--f-sans`
  (`HelpOverlay.vue:154–158`). It stays as it is. U+2328 ⌨ is not in Hack, so the reason for that
  routing still holds.
- Changing `--f-num` (numbers stay on the sans stack).

## Decisions

### D1. Source: the upstream v3.003 TTF release, pinned by SHA-256

The generator downloads `Hack-v3.003-ttf.tar.xz` from
`https://github.com/source-foundry/Hack/releases/download/v3.003/` and verifies its SHA-256
`d9ed5d0a07525c7e7bd587b4364e4bc41021dd668658d09864453d9bb374a78d` before using it. The generator slices
the TTFs itself. The release archive holds only the four TTFs and no license. The generator therefore
also fetches `https://raw.githubusercontent.com/source-foundry/Hack/v3.003/LICENSE.md` from the same tag
and checks its SHA-256 `1f61bb7c790c59b4b0ecdf304628b94e42ae4c8020094a8c3da73381ab212623`.

*Alternative:* ship the upstream `webfonts` tarball's `hack-regular.woff2` (106 KB) or
`hack-regular-subset.woff2` (23 KB, 386 code points, no box drawing). Rejected. The first breaks the
small-file requirement, and the second lacks the box-drawing and geometric glyphs the map art and
severity markers need.

### D2. Slice plan: five unicode-range slices × {Regular 400, Bold 700}

Each code point in Hack's cmap goes to the first slice, in table order, whose claim window contains it.
The claim windows overlap on purpose:

- arrows U+2190–2193 sit in both `latin` and `symbols`;
- `latin` takes a few punctuation code points out of the `latin-ext` window.

Browsers resolve overlapping `unicode-range` declarations by last-declared-wins, not first-claim. The
*declared* ranges therefore must never overlap. The generator emits them from the disjoint claimed sets,
collapsed into runs.

| Slice | Claim window (not the declared range) | Hinted size R / B (research) |
| --- | --- | --- |
| `latin` | U+0020-007E, U+00A0-00FF, U+2013-2014, U+2018-201F, U+2022, U+2026, U+2039-203A, U+20AC, U+2122, U+2190-2193, U+FFFD | 23.0 / 23.5 KB |
| `latin-ext` | U+0100-036F, U+1E00-1EFF, U+2000-218F | 26.0 / 28.3 KB |
| `greek-cyrillic` | U+0370-03FF, U+0400-058F, U+10A0-10FF, U+1F00-1FFF | 28.2 / 26.8 KB |
| `box` | U+2500-259F | 8.8 / 8.8 KB |
| `symbols` | U+2190-23FF, U+25A0-2BFF, U+2E00-2E7F, U+E000-F8FF | 33.2 / 33.2 KB |

- **Arrows in `latin`.** Keycaps show ←↑→↓ on first paint, so the hot path fetches only one file.
- **Fallback for missing glyphs.** A slice declares only code points it actually contains. Code points
  Hack lacks, such as ⌨ and ✕, therefore fall through to Noto Sans TC.
- **Size.** About 250 KB in total. The largest slice is 33 KB, under the 40 KB ceiling in the spec.
  No slice is under 4 KB, so Vite emits every slice as its own file and inlines none.

The slice-contract test checks two things. The declared ranges are pairwise disjoint per weight. Their
union equals Hack's cmap minus the control code points U+0000 and U+000D, so no glyph is silently
dropped.

*Alternative:* one file per weight (106 KB). Rejected because it breaks the small-file requirement.

*Alternative:* a Google-style split into ~100 tiny slices. Rejected. Hack has only 1548 code points, so
that many slices would add request overhead with no gain.

### D3. Keep Hack's TrueType hinting

Hack ships ttfautohint instructions tuned for code at 10–13 px. That is our monospace range
(`--text-xs`/`--text-sm`, 11 px map labels).

Stripping the hints makes each slice about 40% smaller (latin 14 KB, box 4.3 KB). The cost is worse
rendering on Windows' hinted rasterizer, and every slice already fits under the ceiling with hints kept.

The generator drops:

- the `TTFA` table (ttfautohint's parameter record, not used at runtime);
- glyph names.

It keeps name IDs 0–6, 13 and 14, which include copyright and license.

### D4. A generated `fonts-hack.css`, separate from `fonts.css`

The generator writes `web/webclient-app/styles/fonts-hack.css`. Its header names the generator, the
upstream version and the license. `main.js` and `.storybook/preview.js` import it right after
`fonts.css`, which stays a byte-faithful extraction of the design draft.

Each rule uses family `'Hack'`, `font-style: normal`, `font-display: swap`, and a relative
`url(../fonts/hack/hack-<weight>.<slice>.woff2) format('woff2')`, matching the existing rules.

A family defined by `@font-face` shadows an installed family with the same name. A player who has Hack
(or Hack Nerd Font) installed still gets the bundled slices, and the rendered-font check (D7) confirms
this.

### D5. The new stack: `--f-mono: "Hack", "Noto Sans TC", monospace;`

`ui-monospace`, `"DejaVu Sans Mono"` and `"JetBrains Mono"` are removed, so no machine font sits ahead
of the bundled faces. `monospace` stays as the generic tail. The computed family still reports
monospace intent, and only code points outside both Hack and the Noto Sans TC slices, such as emoji,
reach it.

### D6. A reproducible generator script with pinned inline dependencies

`tools/gen_hack_font_slices.py` carries PEP 723 inline metadata pinning `fonttools==4.66.1` and
`brotli==1.2.0`, and runs with `uv run --script tools/gen_hack_font_slices.py`. The pins stay out of
`pyproject.toml` and `uv.lock`, and the game runtime never imports fontTools. The script:

1. **Download.** Fetches the archive and the license (D1) into a temporary directory and verifies both
   checksums.
2. **Slice.** Cuts each slice with `fontTools.subset` (`layout_features=['*']`, hinting kept,
   `notdef_outline`). It sets `font.flavor = "woff2"` before saving; in the research run the subsetter
   option alone did not produce woff2.
3. **Pin timestamps.** Opens fonts with `TTFont(path, recalcTimestamp=False)` so `head.modified` keeps
   the upstream value. By default fontTools rewrites it to the current time on every save, and every
   regeneration would then change every file.
4. **Self-test.** Slices twice in memory and exits non-zero if the two byte streams differ.
5. **Write.** Writes the slices, `web/webclient-app/fonts/hack/LICENSE.md`, and `fonts-hack.css`, whose
   runs come from each slice's claimed set.
6. **Report.** Prints a size table and exits non-zero if any slice exceeds 40 KB.

The script follows the shape of `tools/gen_ansi_palette.py`. Its pure helpers (slice assignment, run
collapsing, CSS rendering) sit apart from the I/O entry point, and fontTools is imported only inside
that entry point. The helpers can therefore be unit-tested without network access or fontTools.

### D7. Test strategy: assert the rendered face, not the family string

- **Rendered face** (`web/tests/browser/test_vue_typography.py::test_keycaps_and_command_input_keep_monospace`,
  Storybook populated-HUD story).
  - **CDP sequence.** The method runs after `document.fonts.ready`, then `DOM.enable`, `CSS.enable`,
    `DOM.getDocument`, `DOM.querySelector` and `CSS.getPlatformFontsForNode`.
  - **Nodes checked.** Three nodes must report `familyName` Hack with `isCustomFont`:
    - the first `kbd`;
    - the command-line prompt (`.cmdfield__prompt`, `›` U+203A, in `latin`);
    - `#inputfield` after typing `look 42`. Blink walks the layout tree, so an input holding text
      reports fonts; an empty input reports none.
  - **CJK node.** A CJK node in a monospace surface must report Noto Sans TC as a custom font.
  - **Failure policy.** A missing CDP method fails the test instead of skipping it, because the suite
    runs only on Chromium. The existing `assertIn("monospace", …)` checks stay.
  - **Stale build.** `setUpClass` reuses `.storybook-out` whenever `index.json` exists. The implementer
    deletes `.storybook-out` before the first run after the CSS change. Otherwise the test runs against
    a build with no Hack faces and proves nothing.
- **Offline origin and on-demand slices** (`web/tests/browser/test_vue_foundation.py::test_vue_bundle_loads_from_origin_offline`).
  Unicode-range slices are fetched lazily after layout. An assertion right after mount is racy, and a
  negative assertion there is vacuous. The test therefore runs in this order:
  1. Make monospace ASCII text visible. Use the dock legend `<kbd>` (`ActionDock.vue:147`) if the live
     state renders it. Otherwise open the command line (`›` prompt).
  2. Wait for `document.fonts.ready` and for a loaded `FontFace` with family `Hack`.
  3. Positive assertion: an origin response matches `/assets/hack-regular.latin-*.woff2`.
  4. Negative assertion: no `hack-*.greek-cyrillic-*` and no `hack-*.latin-ext-*` response.

  The negative assertion holds because the fixture puts no Greek, Cyrillic or extended-Latin text in a
  monospace surface. The spec scenario is worded around that fixture.
- **Slice contract** (new `tests/test_hack_font_slices_contract.py`; Python, no browser). It reads
  `fonts-hack.css` and `fonts/hack/`, then checks:
  - every `url()` resolves to a file, and every file is referenced;
  - every file starts with `wOF2` and is at most 40960 bytes;
  - declared ranges are pairwise disjoint per weight;
  - their union equals Hack's cmap minus U+0000 and U+000D, read from a committed code-point manifest
    that the generator writes beside the slices;
  - U+2190–U+2193 appear only in `latin`;
  - no declared range enters the CJK blocks (U+2E80–U+9FFF, U+F900–U+FAFF, U+20000 and above);
  - weights 400 and 700 are both declared;
  - `LICENSE.md` exists;
  - `tokens.css` sets `--f-mono` to exactly the D5 stack.

  It is written in Python rather than vitest so it can carry `@covers_requirement` (D9, added at archive).
- **Generator helpers** (new `tests/test_hack_font_slices_tool.py`). Covers run collapsing, first-claim
  slice assignment and CSS rendering on synthetic cmaps. CI runs it through
  `unittest discover -s tests -t .`. It needs no network access and no fontTools.
- **Map re-verification.** No map assertion is loosened. The existing map browser tests serve as the
  geometry oracle and are re-run as focused single methods (see tasks). The only map-code edits are
  comments:
  - The "full-width CJK in the monospace token" wording becomes "CJK (Noto Sans TC, 1 em) and Hack
    ASCII (0.602 em)".
  - The comment in `map_lattice_renderer.test.js` about the "11px monospace line box" is re-read and
    corrected the same way.

  The one-em-per-code-point bound still holds, because 0.602 em ≤ 1 em. The SVG labels are placed by
  glyph count × type step and never measure text.
- **Shard registration.** New browser test methods, if any, go into `.github/browser-shards.json` in
  the same commit.

### D8. Visual verification protocol with agent-browser

The implementer captures before and after screenshots with agent-browser (throwaway headless Chromium)
at 1440×900 and 1280×720. The before set comes from an unmodified checkout, in the same environment
used for the after set.

Surfaces to capture:

- populated HUD dock keycaps;
- open command line with the mixed input `look north 看看 42`;
- help overlay keycap table, including the arrow rows;
- dialogue choice numbers (`font: …/1`);
- party strip badges (bold);
- island local map with a dense neighbourhood;
- full map overlay with edge-marker names;
- a message page with a box-grid map (`┌───┬───┐ / │ @ │ # │ / └───┴───┘`) and a `── 稱號冊 ──`
  heading;
- one cold-cache load (cache disabled) of the box-grid page, to judge the swap flash.

Each before/after pair is checked for:

- clipping;
- overlap;
- vertical strokes that join in box art;
- height changes in text-driven boxes.

Screenshots stay in the session scratchpad and are not committed.

### D9. Requirement traceability

`tools/spec_traceability.py` expects a `@covers_requirement` test for every main-spec requirement. The
new requirement's slug, computed with `normalize_requirement_name`, is
`webclient-vue-application::the-monospace-type-role-is-a-self-hosted-sliced-hack-face`. The checker
only indexes `openspec/specs/`, so a decorator naming the ID before the delta is synced fails with
`unknown-requirement-id`. The decorators therefore go into the same commit as the archive-time spec sync
(tasks group 7). Each test below carries that ID:

| Scenario | Test |
| --- | --- |
| Monospace text renders the bundled Hack face offline | `test_vue_typography.VueTypographyBrowserTest.test_keycaps_and_command_input_keep_monospace` |
| CJK text in a monospace surface uses the bundled sans face | same method (CJK node check) |
| Only the needed slices are downloaded | `test_vue_foundation.VueFoundationBrowserTest.test_vue_bundle_loads_from_origin_offline` |
| Every Hack slice is small | `tests/test_hack_font_slices_contract.py` |
| Map labels keep their layout under Hack | `test_browser_local_map_lattice` `test_densely_populated_lattice_scales_down_without_reintroducing_overlap` and `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas` |

## Risks / Trade-offs

- **[Line boxes get shorter on machines whose old monospace face was taller]**
  - The research probe measured −1 px at 11 px and −2 px at 16 px, on pure-Hack lines only. A line
    containing CJK keeps Noto Sans TC's ascent and descent.
  - Fixed-height surfaces and the island anchor clamp (eb3bbc24) are unaffected.
  - Mitigation: re-run the shell island test and the map geometry tests at both viewports, and show
    any surface that moved in the D8 screenshots before merge.
- **[The CI runner's old monospace face is unknown]**
  - The claim of "almost no change on DejaVu machines" is treated as a hope, not a premise.
  - Mitigation: take the D8 baseline and the focused runs in the environment that runs the shards.
- **[Fallback text flashes while a slice loads (`font-display: swap`)]**
  - Until a slice arrives, monospace Latin draws with Noto Sans TC, which is proportional, so box art
    can be briefly misaligned on a cold cache.
  - Slices come from the same origin, are cached immutably by hash, and are at most 33 KB.
  - Mitigation: judge the D8 cold-cache capture by eye. If the flash is objectionable, set
    `font-display: block` on the `box` slice only. Preload stays a Non-Goal.
- **[A UI glyph Hack lacks (⌨ U+2328, ✕ U+2715, 「」) now falls back differently]**
  - The declared ranges exclude these code points, so they resolve to Noto Sans TC where its slices
    cover them and to the `monospace` tail otherwise, as today.
  - HelpOverlay's `--f-sans` routing for ⌨ is kept. Arrows now draw in Hack, and the D8 help-overlay
    capture checks the table layout.
- **[The CDP rendered-font call is Chromium-only]**
  - The suite runs Chromium only, and a missing method fails the test.
  - `familyName` comes from the font data (name IDs 1, 4 and 6 are kept). The implementer confirms the
    reported string once and asserts it together with `isCustomFont`.
- **[The upstream download disappears or changes]**
  - Both checksums are pinned, and the slices and CSS are committed. A normal build never needs the
    network; only regeneration does.
- **[A future slice drops under Vite's 4 KB inline limit]**
  - The browser test matches the Latin slice by name, and that slice is far above the limit.
  - The contract test checks source files, so it does not depend on how Vite emits assets.
- **[Box art mixed with full-width CJK does not align column-for-column]**
  - This is the same as today: 0.602 em box glyphs sit next to 1 em CJK.
  - Emitted map-art lines are either pure box grids or headings that need no alignment. Out of scope.

## Migration Plan

The change ships as one atomic commit with no data migration. Rollback is a revert of that commit. The
dist is rebuilt by `pnpm run build` as part of the normal build.
