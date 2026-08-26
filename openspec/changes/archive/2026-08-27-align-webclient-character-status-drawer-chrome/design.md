## Context

`CharacterStatusDrawer.vue` was built in H4 (`webclient-hud-04-reference-drawers`) to satisfy the
content-correctness rules in `webclient-contextual-hud` (registry-owned degrade reasons, the disguise
true/displayed comparison, the single-wallet-location rule, the absent intimate-state block) — every one
of those rules is about *which values render and when*, not their visual chrome. As a result the drawer's
template uses the simplest layout that satisfies those rules: `display:flex; flex-direction:column` rows
under a `border-top` divider (`CharacterStatusDrawer.vue:315-321`), with no section heading and no
grid/pill wrapper. Every sibling H2 island (`CharacterHead.vue`, `VitalsTrack.vue`, `ConditionChips.vue`)
went through a separate chrome pass that copied the design's exact token values (`--panel`, `--radius`,
`--line`, the five severity tint rules); the drawer never got that pass. `docs/design/elosern-redesign/index.html:1063-1087`
is the reference for what that pass looks like when applied to this exact set of rows (stat tiles in a
2-column grid, a wrapped pill row for conditions, a small-caps heading per section).

## Goals / Non-Goals

**Goals:**
- Every section in the drawer states what it is via a small-caps heading, using the same type scale
  `ConditionChips.vue`'s `.clab` already defines (`font-size:10px; letter-spacing:.14em; color:var(--paper-500)`),
  not a new one.
- Vitals, traits, and guild counters render as the design's 2-column `statgrid`/`statrow` card tiles,
  using the design's literal values (`grid-template-columns:1fr 1fr; gap:8px`; tile
  `background:var(--ink-820); border:1px solid var(--ink-700); border-radius:9px; padding:9px 12px`;
  label `font-size:13px; color:var(--paper-100)`; value `font-family:var(--f-mono); font-size:13px;
  color:var(--gold-400)`) — the same literal-value-copying approach `VitalsTrack.vue`/`CharacterHead.vue`
  already used successfully.
- The condition roster renders as the design's wrapped pill row (`pillrow`/`pill`:
  `display:flex;flex-wrap:wrap;gap:7px`; pill `font-size:12px;padding:5px 11px;border-radius:99px;
  border:1px solid var(--ink-600);background:var(--ink-780);color:var(--paper-300)`), colored per
  severity using `ConditionChips.vue`'s existing five `.chip--*` tint rules (reused verbatim, not
  reinvented), so the drawer's full roster (no 6-item cap, unlike the H2 island) uses the identical color
  language as the capped island version. The pill carries every piece of content the current flat row
  shows — the condition's label, its visible `SEVERITY_LABELS` word, its non-color glyph, and its
  timer/modifier text — folded into the label plus a trailing muted "stat" suffix; the design's own pill
  sample (which shows only a name and a duration) is a two-severity demo and is not read as license to
  drop the severity word our five-severity roster already displays today.
- No change to which values render, when a section degrades, or any existing `data-testid`.

**Non-Goals:**
- Any change to `EquipmentDoll.vue` — it already received its own H4 chrome pass (task 6.3) and matches
  the design's named-slot-box treatment.
- Any change to the disguise section's own content layout — the design renders it as plain text
  (`index.html:1087`) under its own `<h4>偽裝</h4>` heading, so only the heading (task 2.1) is added; the
  paragraph content is untouched.
- The wallet paragraph (`character-status-drawer__wallet`) and the persona-background section. Neither
  appears in the design's status-drawer markup at all (`index.html:1062-1103` has no 金錢/背景 block in
  this drawer — that content lives only in the design's separate bag/inventory drawer). The wallet stays
  exactly the bare `<p>` it is today, with no new wrapping `<section>` and no heading; the persona section
  keeps its existing plain-paragraph treatment. Neither is in the six-section list this change adds
  headings to (vitals, traits, conditions, guild, disguise — persona is listed in the spec delta only
  because it is one of this component's existing `.character-status-drawer__section`-wrapped blocks, not
  because the design shows one).
- Any change to the drawer's degrade-by-section content rules, the disguise true/displayed comparison, or
  the absent-intimate-state rule — all already correctly specified and implemented; this change only adds
  presentation scenarios alongside them.
- Introducing a numeric "effective vs. base" delta indicator (the design's `18 →25` arrow notation on
  attributes). Our `character.traits` rows carry only `current`/`max` (no separate base-vs-buffed pair in
  the payload contract), so inventing a delta arrow would fabricate a value the payload does not provide —
  explicitly against this project's no-invented-data rule. The value cell renders `current` (and `/ max`
  when present) exactly as today, just inside the new tile chrome.

## Decisions

**Add one shared "section heading" pattern used by all four sections, expressed as a scoped class in
`CharacterStatusDrawer.vue` itself (not a new component).** The heading is static markup
(`<p class="character-status-drawer__section-label">生命量</p>` etc.) styled with the same three
declarations `ConditionChips.vue`'s `.clab` uses. Alternatives considered:
- *Extract a shared `SectionLabel.vue` component* — rejected: three CSS declarations, reused by copying
  the same three lines `ConditionChips.vue` already has, is not enough logic to justify a new component
  and an extra import in every consuming file; `VitalsTrack.vue`/`CharacterHead.vue`/`ConditionChips.vue`
  already independently repeat their shared `.hud` chrome block rather than importing it from one place —
  this change follows that same established convention (a small scoped-style repeat, not premature DRY).

**Render the stat-tile grid and the pill row as new template structure inside the existing
`.character-status-drawer__section` wrapper, replacing the current flex-column row markup for vitals,
traits, and guild counters, and replacing the condition roster's flex-wrap row markup with the pill
markup — keeping every existing `data-testid` attribute on the same underlying value, just moved onto the
new element shapes.** E.g. `character-status-drawer__vital--hp` stays the per-row test hook, now on a
`statrow`-shaped `<div>` instead of a flex row; `character-status-drawer__condition--<code>` stays the
per-condition test hook, now on a `<span class="pill">` instead of a flex row. Alternatives considered:
- *Leave existing rows untouched and add the grid/pill purely via CSS (`display:contents` tricks, CSS
  Grid auto-placement over the existing flat DOM order)* — rejected: the design's tile needs its own
  border/background/radius per stat, which requires each stat to be its own grid item element, not a
  flattened set of spans; fighting the existing flex-row markup with grid overrides would produce more
  fragile CSS than writing the tile markup directly.

**Reuse `ConditionChips.vue`'s five `.chip--{beneficial,informational,warning,harmful,critical}` tint
values for the five pill color variants, rather than the design's two-variant (`buff`/`debuff`) sample.**
The design's static mock only had to demonstrate two conditions' worth of color; our system's condition
payload can carry any of five severities, and the H2 island already established the correct five-way
mapping — this change's pills use the exact same `background`/`border-color`/`color` triples per severity,
so the roster and the capped island agree on what each severity looks like everywhere it appears.

**Relax the global JSON-safety integer bound to the full JavaScript-safe range
(`-9,007,199,254,740,991..9,007,199,254,740,991`), in both the client's `protocol.js`
`checkGlobalSafety` and the server-side Python mirror.** Verification showed the deterministic
`world/rules/rulebook/combat_modifiers.yaml` already carries signed values (e.g. `defense: -15`,
`accuracy: -10`), and the client's `validateStatusCondition` runs `checkGlobalSafety` on every
`condition.modifiers` object — so the full condition roster (which the drawer now renders as pills)
would be rejected wholesale by the old non-negative bound. The relaxation is the single protocol-side
adjustment this change makes; no field contract, panel contract, or store slice changes.

## Risks / Trade-offs

- **The full (uncapped) condition roster could produce a very long wrapped pill row for a heavily-buffed
  character** → the design's own pill row already wraps (`flex-wrap:wrap`) with no stated cap, matching
  this drawer's existing "no 6-item cap, unlike H2's island" contract (`CharacterStatusDrawer.vue:159`
  comment); no new truncation is introduced, and the drawer body already scrolls
  (`character-status-drawer` is inside the reference-drawer's own scrollable body per the
  `webclient-contextual-hud` drawer requirement).
- **Moving `data-testid` attributes onto different element shapes (row → tile, row → pill) could silently
  break an existing browser test that also asserts on the row's tag name or a CSS class name rather than
  its testid** → task list includes grepping `web/tests/browser/` for every
  `character-status-drawer__{vital,trait,condition,guild}` selector before the template edit, to confirm
  each asserts only on testid/text content, not on structural CSS classes that this change removes.
- **The stat-tile grid could overflow the drawer's fixed width on narrow viewports** → the design's own
  `.statgrid` is a plain `1fr 1fr` grid with no minimum column width, so it already compresses gracefully;
  verified at both 1440×900 and 1280×720 (an equivalent bounding-box helper, `_anchors_overlap`, already
  exists independently in `test_browser_contextual_hud.py` — no dependency on any other open change).
- **A single vitals tile may not have room for its label, fill-bar track, the conditional `危險` marker,
  and the `current / maximum` numeral on one line** → today that row spans the drawer's full content
  width (`grid-template-columns: 3.5em 1fr auto auto`); halving that width inside a `1fr 1fr` tile is
  tightest for the HP tile when the low-HP marker is also present. The tile's internal layout SHALL stack
  the label+value line above the fill-bar track (two lines within the tile) rather than keep all four
  pieces on one line, so the track never has to compete for horizontal space with the numeral and marker;
  this is decided up front rather than left to be discovered at task 6.3's verification step.
