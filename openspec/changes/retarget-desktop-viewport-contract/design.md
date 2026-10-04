# Design — retarget-desktop-viewport-contract

## Context

The desktop contract — reference viewport, derived geometry, and the type ramp — was drawn
against 1920x1080 with a 12 CSS px chrome floor. The player's actual browser viewport is
1451x790 CSS px: below the old reference, so the reference never applies in normal play
(S = 1 permanently), and the 12px chrome steps are too small at real viewing distance. The
user decision set is locked: 1451x790 replaces 1920x1080 as the reference for everything the
scale-once contract derives; every visible glyph (chrome, drawn-map labels, message/log prose)
reaches at least 16 CSS px at the reference scale; 1280x720 and 1440x900 leave the contract as
required acceptance sizes while proportional scaling above the reference stays. This change is
the engine half (reference constants, tokens, derived spec geometry, prose contract). The
acceptance half — browser-verification matrix, per-feature acceptance requirements, Playwright
viewport tuples, `browser_base.DEFAULT_VIEWPORT` — is the companion change
`retarget-browser-acceptance-viewports`, which lands after this one.

## Goals / Non-Goals

**Goals:**
- One reference viewport, 1451x790 CSS px, from which every chrome dimension is derived.
- A 16 CSS px floor at the reference scale for every visible text, including the drawn map and
  the prose surfaces, with the prose steps re-stepped so the smallest is exactly the floor.
- The chrome-factor mechanism itself untouched: `S = clamp(1, min(h/refH, w/refW), cap)`,
  cap 1.4, below-reference floors unchanged.
- Every main-spec requirement the retarget touches amended here or in the companion change —
  no requirement keeps stale reference numbers after both changes archive.

**Non-Goals:**
- No acceptance viewport-matrix or browser-test edits (companion change).
- No mobile support; desktop-only stance unchanged.
- No mechanism changes: no new scale factor, no second multiplier, no persistence layout-version
  bump (the stored prose-scale numeric is normalized in place, D6).
- No `docs/game` change — no player-command surface moves.

## Decisions

### D1: Reference constants 1080→790, 1920→1451; cap 1.4 stays

`UI_SCALE_REFERENCE_HEIGHT = 790`, `UI_SCALE_REFERENCE_WIDTH = 1451`, `UI_SCALE_MAX = 1.4` in
`web/webclient-app/lib/ui_scale.js`. Consequences of the new reference aspect (~1.837, not 16:9):

| viewport | h/790 | w/1451 | S |
| --- | --- | --- | --- |
| 1451x790 (reference) | 1.0 | 1.0 | 1 |
| 1741x948 (both ratios 1.2) | 1.199 | 1.199 | 1.2, uncapped |
| 2560x1440 | 1.823 | 1.764 | 1.4, capped |
| 1280x720 (off-contract) | 0.911 | 0.882 | 1 (below-reference floor) |

At 2560x1440 the drawing no longer renders at four thirds — both raw ratios now exceed the cap,
so chrome renders at 1.4x reference. The frozen scenarios that pinned 4/3 at 2560x1440 (band
height, island canvas) are restated against 1.4x, and the uncapped-proportionality scenario
moves to 1741x948, a viewport whose height and width ratios are both exactly 1.2 (the old
1741x978 is height-ratio 1.238 > 1.2 and would not hold a 1.2 ratio within tolerance). The
comment block in `ui_scale.js` stops saying "16:9 desktop only" and says "narrower than the
reference's own aspect ratio," which is what the width term actually guards.

### D2: Band clamp keeps the vh term; px bounds become 190/400

`--band-h: clamp(190px * S, 27.85vh, 400px * S)`. The 27.85vh term is kept (the band is
viewport-relative prose-region geometry, unchanged in kind), re-pointed so it lands on the
reference: 27.85% of 790 = 220.0px, so the reference band is 220px (was 300px at 1080). The
lower bound 190px ≈ 260px scaled by the height ratio is not required to be exact — it only has
to stay below the reference landing value so the vh term owns the reference; the upper bound
stays 400px (560px at the cap) so the band still stops growing at large heights. At 2560x1440
the vh term gives 401.0px (inside the bounds), which is the amended frozen value.

### D3: Top band stays 48px; the stage-box invariant holds at 66.1%

`--header-h: calc(48px * S)` unchanged. 790 − 48 − 220 = 522px of stage box = 66.1% of 790,
above the unchanged ≥65% invariant (513.5px). No top-band height change is needed and none is
made; the portrait anchor keeps `min(62vh, 680px * S, stage box)`, whose third term owns at the
reference exactly as before.

### D4: Type ramp re-stepped +4 from the new floor

`--text-*` reference values: xs 12→16, sm 13→17, md 14→18, base 16→20, lg 18→22, xl 20→24,
2xl 24→28, 3xl 28→32, 4xl 32→36, initial 44→48; every token keeps its `calc(Npx * var(--ui-scale))`
shape. The ramp is design-led, not a uniform multiply: the bottom steps compress (12/13/14 →
16/17/18) so the floor is met with the least disruption to the densest chrome, and the top steps
keep their rhythm. `--text-xs` (16px) becomes the smallest rendered step anywhere, which is what
the island's chrome requirement and the place-card numerals' floor clause now reference.
Motion-token "12px" values are travel distances, not type sizes, and stay.

### D5: Message/log prose is a flat 16px reference size in the mono face

`--message-text` and `--log-text` lose their `vh` clamps and become `calc(16px * var(--ui-scale))`
— the prose size at the reference scale is the floor itself, scaled once by the chrome factor like
every other dimension. `MessageWindow.vue` and `FullLogOverlay.vue` swap `--f-serif` for
`--f-mono` (Jim Mono TC) on the page text and the log lines — the reading face is the bundled
monospace family, whose CJK is exactly two cells wide, which is what the 42-cell measure
(`--message-measure`, `42em` in the full log) was always counting in. The measure formula and the
full-log 42em / 1.75 leading keep their shape; only the base size under them changes.

### D6: Prose steps become 16/18/20; stored legacy multipliers normalize to A

The reader prose scale is re-stepped as `A−` = 16px (multiplier 1.0 — the floor, nothing renders
smaller), `A` = 18px (1.125), `A+` = 20px (1.25) at the reference scale. `SCALE_STEPS` in
`SettingsOverlay.vue` keeps its numeric-stored form; the persisted `fontScale` stays a number, and
`preferences.js` normalizes a stored value matching none of the three new steps to the default
`A` — no layout-version bump, because a stale presentation multiplier is exactly as harmless as a
stale presentation key and the clamp-on-load path already exists. The old 0.92 step is deleted
outright: with a 16px floor there is no below-floor step to store.

Relative (em) treatments inside the prose — the `sys` line (0.75em), the box-drawing art path
(0.6em / 0.8em) — would render below the floor once the base is 16px, so they are re-stepped to
absolute reference tokens (`--text-sm` for `sys`, `--text-xs` for the art path) rather than left
as fractions; the amended legibility requirement now states that rule directly. `ReadingSample.vue`'s
0.5em is `visibility: hidden` spacing furniture, exempt as non-visible text.

### D7: Minimap island 208→240px, label steps 12/10→16 units

`--minimap-size: calc(240px * var(--ui-scale))`. The square is re-derived so the fitted drawing
meets the 16px floor at scale 1: the reported wilderness payload's 222.91-unit side now fits the
240px square's inset box at scale 1, so its drawn labels render at exactly the declared 16-unit
step. The island's declared node-label type step moves 12→16 user units and edge-marker names to
the same 16-unit step; the full-map overlay's label steps are 16/16. The lattice pitch derivation
is untouched as a mechanism — its outcome for the frozen 3x3 fixture changes only because the
inset box is roomier: the grown pitch reaches its 60-unit cap (1.5x the declared 40-unit pitch)
instead of binding at 59. The full-map overlay's 1px/2px-per-unit fit and zoom bounds are
unchanged. The island's chrome (title, orientation marks, readout) follows the new `--text-xs`.

### D8: Acceptance-size clauses inside geometry requirements re-point to the reference

Several geometry requirements in this change's capabilities name (1920x1080, 1440x900, 1280x720)
inline. Because MODIFIED deltas replace whole requirements, this change restates those
enumerations as part of owning the geometry: they become 1451x790, with 2560x1440 (the cap) and
1741x948 (uncapped 1.2) as the larger-display pins. The companion change must not touch these
requirements; it owns only the pure acceptance requirements that carry no derived geometry.

## Risks / Trade-offs

- **The cap binds at 2560x1440.** Chrome on a 2560x1440 display renders 1.4x the new reference
  instead of 1.333x the old one — text there grows ~5%. Accepted: the mechanism and cap are
  unchanged, only the reference moved.
- **16px at dense chrome.** Widest labels (top-nav tool group, place card, combat frame rows)
  grow ~33%. Mitigated by the existing mode-gated/compact padding rules and verified by the
  amended fit scenarios at 1451x790; the acceptance change re-runs the journeys.
- **Prose re-stepping is not ratio-preserving** (old 20/22.5/25-style clamp → 16/18/20). Readers
  at A+ see slightly smaller prose than the old clamp could reach; that is the point of the floor
  retarget — the old clamp bottomed at 20px *at 1080 only* and rendered ~14.6px at 790.
- **Stale persisted prose multipliers** (0.92/1.12) load as A; a one-time visual reset for
  players who had chosen a step. Accepted over a layout-version bump.

## Migration plan

Land this change first (constants, tokens, components, derived spec geometry, unit tests). The
companion `retarget-browser-acceptance-viewports` then retargets `browser_base.DEFAULT_VIEWPORT`,
the Playwright viewport tuples, and the acceptance requirements; between the two, the browser
suites run the old tuples against the new geometry (they still pass — old viewports remain
valid, just no longer contractually required). Rollback is the reference constants alone: every
derived value is a function of them plus the token literals.

## Open Items

- None blocking. The stored-`fontScale` normalization is decided (D6); if a future change wants
  named steps in storage it can bump the layout version then.
