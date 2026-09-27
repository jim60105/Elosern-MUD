## Context

tools/gen_ansi_palette.py is the existing generator; report Message Window ANSI observation. Palette constants are design choices, not claimed observed results.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Tone down ANSI foreground colors without changing server markup or background colors.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions


### D1. An authored table for the twelve chromatic ANSI entries

| Entry | Name | Tone | HSL S | Contrast on `#141019` |
|---|---|---|---|---|
| 001 | red | `#b8665f` | 0.39 | ≥ 4.4 |
| 002 | green | `#7fa37a` | 0.18 | ≥ 6.4 |
| 003 | yellow | `#c9ad78` | 0.43 | ≥ 8.4 |
| 004 | blue | `#7b92c2` | 0.37 | ≥ 5.8 |
| 005 | magenta | `#a987a9` | 0.17 | ≥ 5.8 |
| 006 | cyan | `#76a2aa` | 0.23 | ≥ 6.5 |
| 009 | bright red | `#dc7a72` | 0.60 | ≥ 6.1 |
| 010 | bright green | `#8fb98a` | 0.25 | ≥ 8.2 |
| 011 | bright yellow | `#e4c88e` (`--gold-400`) | 0.61 | ≥ 11 |
| 012 | bright blue | `#8aa3d8` | 0.50 | ≥ 7.2 |
| 013 | bright magenta | `#c496c4` | 0.28 | ≥ 7.3 |
| 014 | bright cyan | `#86b8c2` | 0.33 | ≥ 8.3 |

Normal entries are a step darker and duller than their bright pair, so `|R` vs `|r` stays distinguishable. The listed contrast figures are planning estimates, not newly exercised evidence. During application calculate them using the generator helper before relying on them; contrast flooring remains authoritative.

Alternative considered: desaturating the stock values by a formula. Stock `#00ff00` desaturated to a cap still reads as a neon green at full lightness. An authored table is short, reviewable, and the result is judged on the real reading surface; tests cover saturation, hue and contrast invariants rather than copying the authored table.

### D2. Cube entries: cap saturation, keep hue and lightness

For each 6×6×6 cube entry, convert to HLS with `colorsys`. If S > 0.62, set S = 0.62, convert back, and round inward: ceil channels below lightness, floor channels above lightness, and round a channel exactly at lightness. This avoids nearest-integer rounding increasing saturation beyond the strict cap. Then apply the contrast floor. Hue and lightness preservation are measured at the mapping stage, before that floor: hue within ±2° for chromatic entries and lightness within 1/255. Achromatic hue is undefined and is not compared. The final output must still satisfy saturation ≤0.62 and contrast ≥3.0. The paper blend may shift hue and lightness. The 0.62 cap is the ceiling of the authored table (gold-400 is 0.61).

Application-time numerical clarification (approved during implementation): a
216-entry probe using inward rounding and the new ink found no saturation,
contrast, or pre-floor hue violations. Maximum pre-floor hue error was
0.306123° (index 81); maximum post-floor hue shift was 9.230769° (index 53);
maximum final cube saturation was 0.618605 (index 26); minimum final cube
contrast was 3.005100 (index 29). The initial nearest-rounding probe's index 17
6° and index 53 8.78° were **post-floor**, not mapping errors. This is why both
the requirement and scenario explicitly name the hue-preservation stage.
The twelve authored tones were also evaluated against `#141019`: contrasts in
table order were 4.565587, 6.639522, 8.705749, 6.022688, 6.016206, 6.725923,
6.324299, 8.475286, 11.585227, 7.434581, 7.609632, and 8.631260. All clear the
floor unchanged; their saturation values round to the D1 values.

Alternative considered: the review's 45% cap. The theme's own gold accent is 61%, so a 45% cap would forbid the theme's primary accent in narrative text.

### D3. The band's ink is the floor's reference

`INK` becomes `#141019`, the band's opaque ink reference. The paper blend
target stays `#ece7db`. Every authored tone clears 3.0 against it without
blending (D1 table). This reference is not a worst-case guarantee for the
translucent upper gradient over arbitrary scene art; background composition
remains outside this foreground-only change.



## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.

## Application verification (2026-09-28)

The pure generator was executed with
`uv run --locked python tools/gen_ansi_palette.py`; it wrote
`web/static/webclient/css/ansi_palette.css`. Focused verification:

| Command | Observed result |
|---|---|
| `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_ansi_palette` (Bash env `MUD_TEST_SETTINGS=1`) | 8 tests passed, 0.011s |
| `pnpm exec vitest run web/webclient-app/tests/message_window.test.js web/webclient-app/tests/full_log_overlay.test.js web/webclient-app/tests/narrative_line_nodes.test.js` | 3 files, 41 tests passed |
| `node --test web/static/webclient/js/tests/narrative_markup.test.js` | 20 tests passed |
| `openspec validate webclient-ansi-narrative-tones --strict` | Change is valid |
| `uv run --locked python -m tools.spec_traceability check` | 1722 requirements covered, 6740 associations, 0 uncovered, 0 errors |

The traceability CLI has no capability filter; its static `check` is the
available local gate, not the CI-only evidence verification. `list
--json-output` supplied the existing canonical palette requirement identifier
used by the substantive numerical tests. No test modules or browser methods
were added/moved, so shard manifests are unchanged: the existing palette
module belongs to `web.webclient.tests` in `webclient-evidence`.

Storybook ran with `pnpm exec storybook dev -p 6011 --ci --no-open`.
`agent-browser --session ansi-tones open
'http://127.0.0.1:6011/iframe.html?id=core-messagewindow--narrative-tones&viewMode=story'`
loaded the real MessageWindow and FullLogOverlay, with generated CSS imported
by preview.js. `set viewport` and `screenshot` exercised 1280×720, 1440×900,
and 1920×1080. The band text measured 20px, 23.337px, and 28.0044px; the full
log measured 15.5px. Screenshots were inspected: normal/bright pairs remain
distinct, gold is the accent, the dark grayscale is visibly dimmer, and all
fixture text fits without page-level horizontal overflow. Clicking the log
button focuses the dialog; Escape removes it and returns focus to the opener.
The story now calls the overlay's existing `focusSelf` lifecycle, as the
application does, rather than leaving its focus trap uninitialized.

Computed foreground colors from the rendered full log yielded these ratios:

| Entry | Band reference `#141019` | Full log `#0b0d10` |
|---|---:|---:|
| Normal red 001 (minimum chromatic tone) | 4.5656 | 4.7289 |
| Bright red 009 | 6.3243 | 6.5506 |
| Gold 011 | 11.5852 | 11.9998 |
| Dark grayscale 232 | 3.1410 | 3.2534 |
| Middle grayscale 244 | 4.7564 | 4.9266 |
| Light grayscale 255 | 16.1910 | 16.7703 |

All twelve chromatic entries exceed 4.5:1 on these references, including the
normal-sized full-log text. The 3:1 contract for the complete cube/ramp is
**not** WCAG AA for all normal-sized text. A deliberate white-backdrop probe
of the existing translucent band sampled RGB(32,33,38) at screenshot
coordinate (1000,65): red was 3.9052 and grayscale 232 was 2.6867 there.
At (1000,138) the opaque `#141019` sample restored 4.5656 and 3.1410.
Backdrop-independent legibility would require a separate band-compositing
decision; this change neither changes backgrounds nor claims that guarantee.

Browser `eval` on the actual `.blink` span reported `blink-animation` at
`data-motion=full`; both `reduced` and `off` reported `animationName=none`,
`textDecorationLine=underline`, `textDecorationStyle=dotted`.
`agent-browser --session ansi-tones set media dark reduced-motion`, with the
root attribute removed, also reported that same static indicator and a true
OS media query. Existing committed browser tests
`test_os_reduced_motion_resolves_to_reduced` and `test_motion_off_is_instant`
retain computed-style regression coverage; the redundant CSS-source-string
test was removed, and the standard cube level is covered numerically.
Those managed browser tests were not run here; this local browser proof used
Storybook and agent-browser, without building or booting the game server.

The existing `core-messagewindow--oversize-map` story was also opened and
visually inspected. All 17 rendered box-drawing rows measured x=54.90625 and
width=211.640625 at 1920×1080, using the existing monospace map renderer;
the page had no horizontal overflow. No renderer/font/map behavior changed.
