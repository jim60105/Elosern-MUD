# Design: Centre a narrow combat command card over the stage

See `proposal.md` for the motivation and `specs/` for the observable contract. This document records how the
existing pieces are rearranged, the measured geometry the card's size comes from, and why.

## Context

- The stage (`components/HudFrame.vue`) is a `position:absolute; overflow:clip` box with named anchors. The bottom
  band `.stage-band` is itself `position:absolute`, so it is the containing block of `band-message` and
  `band-command`; CSS alone cannot place the band's command region over the stage centre.
- `components/AppShell.vue` puts AppClient's `#action-dock` slot into HudFrame's `band-command` slot. AppClient's
  slot renders `ActionDock` (`#action-dock`, the documented focus home in exploration/combat/creation) holding
  `.dock-pane-host` with `DockMenu` (row region + generic detail aside) and `SkillDetailPane`, plus the breadcrumb,
  the playback cue and the legend owned by `ActionDock`.
- Keyboard routing is document-level (`bridge.js` → `store.focusPress`); where the dock element sits in the DOM
  does not affect routing. Pointer clicks are handled by the row buttons themselves.
- Browser tests rely on one persistent `#action-dock` node across mode changes
  (`test_browser_contextual_hud_dock.py`: `__tracked` survives exploration → combat), on `dock-menu`,
  `combat-detail`, `dock-crumb`, `action-dock-description`, `action-dock-playback(-skip)` hooks, and on
  `focus_action_dock` focusing `#action-dock` in combat.
- The companion line-up (`components/CompanionLineup.vue`, `companion-lineup.js`) keeps every figure at full
  size and shifts a multi-figure group right: `translateX(max(0, reach − actor-left-inset + 16px·S))`, with
  `reach = (n − 1) × EXPOSURE[n] × figure width` and `EXPOSURE = [0, 0, 0.42, 0.3, 0.24, 0.22]` (n = figures,
  player included, at most five). The user ruled out compressing it in combat.
- The foe line-up (`components/FoeLineup.vue`, `foe-lineup.js`) stands at most three foes (a fourth and fifth
  are listed only in the participant frame), growing leftward toward the centre; every foe's name plate and gauge
  sit on one shared line above the scene caption.

### Measured geometry (built Storybook, `core-appshell--combat-*` and `--populated-full-party`)

Figure width `fw = actor-h × 2/3`; C = stage centre; g = 16px·S. Boxes are the figure slot boxes (the art's 2:3
box, which includes transparent margin).

| | 1451x790 (S = 1) | 1600x900 (S = 1.1027) |
|---|---|---|
| C | 725.5 | 800 |
| `fw`, `actor-left-inset` | 326.5, 134.9 | 372.0, 142.8 |
| controlled figure right edge, party of 1 / 2 / 3 / 4 / 5 figures | 461.5 / 479.7 / 538.4 / 577.7 / 629.9 | 514.8 / 545.8 / 612.8 / 657.5 / 717.0 |
| leftmost foe box left, 1 / 2 / 3+ foes | 920.5 / 819.7 / 756.5 | 1035.5 / 920.7 / 848.6 |
| rearmost foe name plate left, 1 / 2 / 3+ foes | 1012.0 / 891.0 / 812.2 | 1139.7 / 1001.9 / 912.1 |
| foe head (box top), rearmost, 1 / 2 / 3+ foes | 80.2 / 170.8 / 237.0 | 91.4 / 194.6 / 269.9 |
| foe name-plate line (top) / gauge bottom | 459.9 / 501.0 | 528.6 / 573.3 |
| `choices` anchor top / bottom (dialogue) | 58 / 472 | 70.6 / 541.3 |

(Party sizes 3 and 5 and foe counts 1–3 and 5 were measured; party sizes 2 and 4 are computed from the same
formula, which reproduces the measured rows to 0.1px.)

## Goals / Non-Goals

**Goals:**

- One place for "what do I do next": combat commands appear where the dialogue list and room cards appear, in the
  same card frame, at the stage's dead centre.
- Immediate combat state stays readable: foe plates, gauges and the focused-target cue, the player's figure and
  party, the vitals dock, the participant frame, the scene caption and the combat log.
- Zero behaviour change to the combat menu model, router, payloads, protocol and telnet.

**Non-Goals:**

- Picking targets on the stage figures (`webclient-combat-stage-target-picking`).
- Re-skinning the combat rows as ChoiceCard rows (digit badges, ChoiceCard's own key handling).
- Compressing the companion line-up, or re-staging the foe line-up.
- The exploration dock, the SkillBook casting dock (`SkillUseDock`), dialogue, telnet.

## Decisions

### D1. Move the same `#action-dock` node with a Teleport owned by HudFrame

HudFrame wraps its `band-command` slot in `<Teleport :to="#<choices-id>" defer :disabled="mode !== 'combat'">`,
where `<choices-id>` comes from `useId()` and is set as the `id` of the `choices` anchor element. While disabled the
slot renders in place (exploration, dialogue, creation); in combat Vue moves the existing DOM nodes into the
`choices` anchor and back without unmounting the components.

- Keeps exactly one `#action-dock`, the same node and component instance (the `__tracked` test, DockMenu/ExitCompass
  state, `compassRef`), all test ids, and the focus-home lookup `document.getElementById("action-dock")`.
- A `useId` selector instead of a static selector keeps several stages on one Storybook docs page from teleporting
  into the first stage; `defer` lets the target (rendered by the same component) resolve after mount, so a reload
  directly into combat works.
- Alternatives rejected: (a) CSS-only repositioning of `band-command` — its containing block is the band; (b) a
  second ActionDock in the `choices` slot under `v-if` — remounts the dock and breaks the persistent-node contract;
  (c) re-implementing the combat menu inside `ChoiceCard` — duplicates the router's key handling.

### D2. The band collapses in combat like it does in dialogue, but with `display:none`

In combat `band-command` is empty (its content teleported), so HudFrame sets `.stage-band` to one column and
`[data-anchor="band-command"]` to `display:none`; the message region spans the band from the commit's frame. The
message page keeps its `--message-measure` reading column (centred), so pagination does not change. On leaving
combat the region returns in the commit's frame and the existing `data-flip="combat-exploration"` flip-out plays on
the dock that has just moved back. HudFrame's flip watcher stops setting `data-flip` for `*-combat` changes; the
`elosern-panel-flip-in` rule for `-combat` is removed.

### D3. Card geometry: dead centre, width from the party-side gap, height above the plate line

**Gap computation.** For a card of width W centred on C, the free half-width on the party side is
`C − P − g` and on the foe side `F − g − C`, where P is the controlled figure's right edge and F the leftmost foe
box's left edge. The dead-centre width that clears both is `W = 2 × min(C − P − g, F − g − C)`:

| | foes: 1 | 2 | 3+ |
|---|---|---|---|
| 1451x790, 4-figure party (C − P − g = 131.8) | min(131.8, 179.0) → **263.6** | min(131.8, 78.2) → 156.4 | min(131.8, 15.0) → 30.0 |
| 1600x900, 4-figure party (C − P − g = 124.9) | min(124.9, 217.9) → **249.8** | min(124.9, 103.1) → 206.2 | min(124.9, 31.0) → 62.0 |

The foe line-up's rearmost foe stands within 31px (1451) / 49px (1600) of the centre with three foes, so no usable
dead-centre card clears every foe box. The foe-side gap therefore cannot set the width. The card instead:

1. takes its **width from the party side only**, which is guaranteed for a given party size:
   `--combat-card-w: clamp(240px·S, 2 × (50% − var(--stage-party-edge) − 16px·S), 280px·S)`;
2. keeps the **foe plates, gauges and the focused-target cue clear vertically**: its bottom edge stands
   8px·S above the foe name-plate line, which every foe shares, so whatever the foe count it never meets a plate,
   gauge or cue (the current cue is the plate's border; the arrow markers of the stage target step only show while
   the card is collapsed, see `webclient-combat-stage-target-picking`);
3. **may stand over foe art** — this deviates from the user's "only empty floor" wording and needs the user's
   sign-off before apply (see Open Questions): with one foe it clears the foe's box at both viewports; with two foes
   (rear box 819.7–1074.4, centre 947.1 / 920.7–1210.8, centre 1065.8) a 280/308.8 card covers the left 45.8px /
   33.7px of the rear box, well short of its centre; with three or more foes (rear box 756.5–955.6, centre 856.1 /
   848.6–1075.5, centre 962.1) it covers 109px / 105.8px, passing the rear box's centre by 9.4px at 1451 and stopping
   7.7px short of it at 1600. Only slot boxes were measured; the art's alpha bounds were not, so how much of the rear
   foe's body or face is hidden depends on the artwork. With three foes the foe-side dead-centre gap is 30px / 62px,
   so no usable card avoids the rear foe's box; the overlap is forced, not a tuning choice.

Fallback when even the minimum cannot fit (five-figure party): the card keeps the minimum width and dead
centre and stands over the right part of the controlled figure's box (below).

`--stage-party-edge` = `var(--actor-left-inset) + fw + max(0px, fw × var(--party-reach, 0) − var(--actor-left-inset)
+ 16px·S)`, the CSS form of CompanionLineup's own translate; AppClient writes `--party-reach` =
`(n − 1) × EXPOSURE[n]` (from `companion-lineup.js`, 0 for a solo player) on `.elosern-root`, next to the existing
`--foe-lineup-span`. A comment in both CompanionLineup and HudFrame says the two copies must stay in step.

Resulting widths (±1px):

| Party figures | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 1451x790 (min 240, max 280) | 280 | 280 | 280 | 263.6 | 240 (overlaps the controlled box by 24.4) |
| 1600x900 (min 264.6, max 308.8) | 308.8 | 308.8 | 308.8 | 264.6 (clamped up; left edge 667.7, 10.2px clear of the box) | 264.6 (overlaps the controlled box by 49.3) |

With five figures the controlled figure stands right of where even the minimum card can clear; the overlap is the
right 24.4px / 49.3px of its 2:3 box, whose centre (466.6 / 531.0) stays 138.9px / 136.7px left of the card. The art's
alpha bounds were not measured, so the overlap is stated against the box only.

**Minimum width 240px·S — why.** Inner width = card width − 2 × 12px·S card padding − 2 × 1px frame border =
214px at S = 1. Budgets at S = 1: a skill row = selection glyph 18 + icon 20 + two 6px gaps + a label of four
characters at `--text-md` 18px (72; the longest current combat skill labels — 基本攻擊, 微光治癒, 疾風突進 — are four)
+ a cost `MP 12` at `--text-sm` ≈ 48 + 2 × 8 row padding = 186, leaving room for a fifth character (204); longer
labels wrap inside the row. The 威力 scale step's five chips (1/4, 1/2, 1, 2, 4) at a 38px minimum with 4px gaps =
206. The AREA token grid's two columns at 102px with an 8px gap = 212. 224px·S (inner 198) would overflow the scale
row and the token grid, so 240px·S is the smallest width at which every frame keeps its columns on one line.
**Maximum 280px·S** keeps the card's right edge left of the single foe's box at both viewports (865.5 < 920.5 −
16; 954.4 < 1035.5 − 17.6).

**Height and placement.** In combat the `choices` anchor keeps its dialogue `top` (header + inset) and the card is
top-anchored in it (not vertically centred), with
`height: min(400px·S, 100% − (anchor bottom → plate line clearance))`, written as the distance from the stage top to
`band top − var(--foe-plate-rise) − 8px·S`. `--foe-plate-rise` (new token in `tokens.css`) is the height of the
plate's top edge above the band, the expression `.foe-lineup__name` already positions itself by
(`command-line-h + 12px·S + (scene-caption-h − 8px·S)/2 + 13px·S + --foe-plate-h`) with `--foe-plate-h` the plate's
own fixed height (`--text-sm × 1.3` + its 2px padding × 2 + 2px border); FoeLineup's rule is rewritten to read the
same tokens so the card and the plates cannot drift apart. Measured: 1451x790 → card 58–451.9 (393.9 tall);
1600x900 → 70.6–511.7 (cap 441.1).

- The `left` is `calc(50% − var(--combat-card-w) / 2)`; `width`/`left` glide on
  `calc(var(--motion-actor) × var(--motion-travel))` when a companion joins or leaves (rare, but it keeps the card
  in step with the line-up's own glide).
- Alternatives rejected: shifting the card toward the open span (the old clamp; the user wants dead centre);
  compressing the party (ruled out by the user); a card above the foes' heads (the rear foe's head top is y 237 /
  270, leaving 163px / 199px, too short for the seven-row root); re-staging the foe line-up so the rear foe clears
  a 280px card (its exposure would fall from 46% to ~17%, hiding the rear foes).

### D4. Combat keeps the uncompressed companion line-up

AppClient keeps passing `compact` only in dialogue. No change to `CompanionLineup.vue` or its requirement; the card
reads the line-up's geometry through `--party-reach` (D3).

### D5. ActionDock gains a `card` presentation with a narrow layout

`ActionDock` takes `card: Boolean` (AppClient passes `store.view.mode === 'combat'`). In card mode:

- The root carries `action-dock--card choice-card choice-card--still`, renders a decorative
  `<span class="choice-card__corners" aria-hidden="true">`, drops its own `::after` focus mark (that pseudo-element
  is the ChoiceCard crest), brightens the frame with `.choice-card:focus-visible`'s declarations while
  `:has(:focus-visible)`, and sizes itself `width: 100%; height: 100%; max-width: none; margin: 0; padding:
  12px·S`. `choice-card--still` disables ChoiceCard's own mount animation (D6 owns the entrance).
- **Layout (top to bottom):** the one-line breadcrumb; the row region (`flex: 1 1 auto`, scrolls, three-row
  minimum); the detail strip; the playback cue overlays the row region and strip; the legend at the foot.
- **Breadcrumb:** one line, `white-space: nowrap`; the back chevron and the current frame name never shrink; earlier
  crumbs share the rest with `text-overflow: ellipsis` (`DockBreadcrumb` already renders crumbs as separate
  spans; only card-scoped CSS changes).
- **Rows:** the root, category, group, skill and SINGLE/SELF/NONE target frames already have `gridCols: 1`; the card
  CSS removes their band-width minimums so they fill the card's inner width and wrap long labels; the skill row puts
  the cost at the row's end in `--text-sm`. The AREA token grid keeps two columns (`minmax(0, 1fr)` each) and the
  scale step one column per chip (`minmax(0, 1fr)`); the Forfeit pair keeps two columns. Grid geometry for the
  router is unchanged.
- **Detail strip:** `DockMenu`'s generic detail and `SkillDetailPane` take a `variant` prop (`"pane"` default,
  `"strip"` in the card). The strip is a direct child of the pane host below the row region, fixed at three lines
  of `--text-sm` (`height: calc(3lh + padding)`), `overflow: hidden`. Line 1: cost and target requirement (and
  element) joined by ` ‧ `; lines 2–3: the description, or for a disabled entry the server-authored reason in its
  place, `-webkit-line-clamp: 2`. The strip's full text stays in the DOM, the strip carries `title` with the full
  text, and the focused row's `aria-describedby` already points at the detail (unchanged hook
  `action-dock-description`).
- **Legend:** unchanged text; card CSS lets it wrap at the ` ‧ ` separators (`flex-wrap` over its segments) to at
  most two lines.

The card pane-host rules live in `styles/app-shell.css` next to `.dock-pane-host--bounded`, unprefixed, so
Storybook and the live client agree. The `.elosern-root .skill-detail-pane*` typography duplicates move into
`SkillDetailPane.vue`. The band-scoped `[data-anchor="band-command"]` detail rules stay for the exploration
SkillUseDock.

### D6. Motion: entrance keyed on the live mode change; reconnect at rest

`.elosern-stage[data-mode-change$="-combat"] [data-anchor="choices"] > .action-dock--card` runs
`elosern-combat-card-in var(--motion-reveal) var(--ease-enter) var(--motion-flash) backwards` (opacity 0 and
`translateY(var(--motion-shift-sm) × var(--motion-travel))` → rest). `data-mode-change` is never set on mount or
reconnect, so those render at rest; reduced resolves to a 150ms fade with no delay and no rise, off to 0ms. The
`backwards` fill only holds paint: the rows are focusable and clickable from the commit's frame.

### D7. Focus re-home across the move

Moving a focused node blurs it. AppShell's mode watcher, after `await nextTick()`, calls `restoreFocusHome()` when
the mode entered combat and focus is lost (`focusIsLost`). Leaving combat for exploration is already covered by
`focusExplorationEntry`, and combat → dialogue by the dialogue branch. Focus in the command field, a drawer or an
overlay is not lost and is left alone.

### D8. Storybook

- `Core/AppShell` renders the real AppClient, so the CombatHud family shows the card. A `combatKeys` arg replays
  router keys through `store.focusPress` after the snapshot commits. New stories: `CombatTargetStep`,
  `CombatSkillDetail`, `CombatDisabledCommand`, `CombatMasterScale` (a skill with `freeform_scales`, as in
  `stories/fixtures/skills.js`), `CombatFourFigureParty` (three companions, three foes) and `CombatFullParty`
  (four companions, three foes); `CombatOneFoe` and `CombatFiveFoes` already exist.
- `Action/ActionDock`: combat stories render `card: true` in a host of 240×394 and 280×394; add `CombatTargets`,
  `CombatMasterScale` and `CombatDisabledDetail` (strip with a reason).
- `Action/SkillDetailPane`: a `Strip` story. `Action/DockMenu`: `TargetFrame`/`FixedGridFrame` in a 240px host.
- No component is added; `component-manifest.json` stays frozen.

## Risks / Trade-offs

- [Card over rear foe art with 2–3 foes] → plates, gauges and the target cue stay clear by construction; the stage
  target step (next change) collapses the card while the player picks a target. Recorded as the open question.
- [Five-figure party] → the card overlaps the right 24.4 / 49.3px of the controlled figure's box; the box centre stays ≥ 136px clear.
- [`--party-reach` duplicates `companion-lineup.js`'s table in CSS] → AppClient computes it from the JS table
  (no second table); only the translate formula is mirrored, with comments; a Vitest case pins both.
- [Teleport + focus in jsdom/Chromium differ] → Vitest asserts the node move and the re-home call; one live browser
  method asserts real focus after entering and leaving combat.
- [Truncated detail] → the strip clips description lines; the full text stays the row's accessible description and
  the strip's `title`, and the SkillBook drawer shows the full skill.
- [A reload straight into combat must find the Teleport target] → `defer` + an id on the same component's anchor;
  covered by `test_reload_in_combat_plays_nothing` and a Vitest mount in combat.

## Migration Plan

Pre-release client; no data or protocol migration. Rollback is reverting the change's commits.

## Open Questions

- **Needs the user's sign-off before apply (blocking for task 1.1):** with two or more foes the dead-centre card
  stands over part of the rear foe's box while the player chooses a command (three foes: 109px at 1451x790, past the
  box's centre by 9.4px; 105.8px at 1600x900), and with a five-figure party over the right 24.4 / 49.3px of the
  controlled figure's box. This deviates from "overlay only empty floor between figures"; physically no usable
  dead-centre width avoids it (the foe-side gap is 30px / 62px with three foes). Plates, gauges and cues stay clear,
  and the card collapses during target choice once `webclient-combat-stage-target-picking` lands. Alternatives: accept;
  re-stage the foe line-up (a separate change); or relax dead centre for three foes.
