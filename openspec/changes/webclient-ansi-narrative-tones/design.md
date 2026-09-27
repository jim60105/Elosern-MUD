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

For each 6×6×6 cube entry, convert to HLS with `colorsys`. If S > 0.62, set S = 0.62, convert back, and round to integers. Then apply the contrast floor. Hue is preserved to within rounding (the test allows ±2° after rounding). The 0.62 cap is the ceiling of the authored table (gold-400 is 0.61). One number for the whole palette makes "no foreground entry is loud" a single testable rule.

Alternative considered: the review's 45% cap. The theme's own gold accent is 61%, so a 45% cap would forbid the theme's primary accent in narrative text.

### D3. The band's ink is the floor's reference

`INK` becomes `#141019`, the lighter end of the band's gradient, which is the worst case for contrast. The paper blend target stays `#ece7db`. Every current tone clears 3.0 against it without blending (D1 table).



## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
