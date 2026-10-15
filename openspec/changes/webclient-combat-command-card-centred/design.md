# Design: Centre a narrow combat command card over the stage

See `proposal.md` and `specs/`. Builds on `webclient-combat-formation` (both sides stand in a shared-scale formation
that keeps a dead-centre gap of `264px·S + 2 × 16px·S` clear) and its engine's design (measured inputs, reference
table).

## Context

- The stage (`components/HudFrame.vue`) is a `position:absolute; overflow:clip` box with named anchors. The bottom
  band `.stage-band` is the containing block of `band-message` and `band-command`, so CSS alone cannot place the
  band's command region over the stage centre.
- `components/AppShell.vue` puts AppClient's `#action-dock` slot into HudFrame's `band-command` slot. `ActionDock`
  holds `.dock-pane-host` with `DockMenu` and `SkillDetailPane`, the breadcrumb, the playback cue and the legend.
- Keyboard routing is document-level (`bridge.js` → `store.focusPress`); the DOM position of the dock does not affect
  routing.
- Browser tests rely on one persistent `#action-dock` node across mode changes and on the dock's test ids.
- The `choices` anchor (dialogue geometry) spans 58–472 at 1451x790 and 70.6–541.3 at 1600x900.

## Goals / Non-Goals

**Goals:** one place for "what do I do next" — the combat commands appear where the dialogue list and room cards
appear, at the stage's dead centre, in the same card frame; zero behaviour change to the menu model, router,
payloads, protocol and telnet.

**Non-Goals:** picking targets on the stage (`webclient-combat-stage-target-picking`); the formation itself.

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

### D3. Card geometry: fixed width in the formation's gap

- **Width:** `264px·S`, fixed (264 at 1451x790, 291.1 at 1600x900); `left: calc(50% - 132px·S)`.
- **Gap:** the formation engine reserves `[C − 132px·S − 16px·S, C + 132px·S + 16px·S]` for every party size (1–5
  figures) and foe count (up to 16 − party) at every viewport. Nothing in the formation (figure boxes, plates, target markers) can
  meet the card, so the card needs no clamp, no shift and no dependency on the line-ups.
- **Height:** top-anchored at the `choices` anchor's top; `height: min(400px·S, 100%)` of the anchor's span (400 at
  1451x790, 441.1 at 1600x900). No frame resizes it.
- **Why 264px·S.** The inner width is 264 − 2 × 12 padding − 2 × 1 frame = 238px at S = 1. Budgets at S = 1:
  - a skill row: glyph 18 + icon 20 + two 6px gaps + a 6-character label at `--text-md` (108) + the cost `MP 12`
    (≈ 48) + 2 × 8 padding = 222 ≤ 238, so labels of up to six characters stay on one line (the current longest are
    four);
  - the 威力 step's five chips: 5 × 38 + 4 × 4 = 206;
  - the AREA grid: 2 × 113 + 8 gap = 234;
  - the legend wraps at its separators onto at most two lines.

  A wider card would shrink the formation's zones and push the shared scale down: every 32px·S of card costs both
  sides 16px·S. 264 is the smallest width that keeps every frame's columns on one line with room for six-character
  labels.
- The old open-span clamp, the party-edge property and the plate-line bottom are gone; the companion line-up is not
  touched by this change.

### D4. (retired)

The earlier party-compaction decision no longer applies; the formation owns all figure placement.

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
  `stories/fixtures/skills.js`), and the formation corners from `webclient-combat-formation` now show the card.
- `Action/ActionDock`: combat stories render `card: true` in a 264×400 host; add `CombatTargets`,
  `CombatMasterScale` and `CombatDisabledDetail` (strip with a reason).
- `Action/SkillDetailPane`: a `Strip` story. `Action/DockMenu`: `TargetFrame`/`FixedGridFrame` in a 264px host.
- No component is added; `component-manifest.json` stays frozen.

## Risks / Trade-offs

- [Teleport + focus in jsdom/Chromium differ] → Vitest asserts the node move and the re-home call; one live browser
  method asserts real focus after entering and leaving combat.
- [Truncated detail] → the strip clips description lines; the full text stays the row's accessible description and
  the strip's `title`.
- [A reload straight into combat must find the Teleport target] → `defer` + an id on the same component's anchor.
- [Beat lunges] → `webclient-combat-formation` shrinks the step toward the centre to 12px·S, inside the 16px·S
  gutter, so no figure ever enters the card's columns.

## Migration Plan

Pre-release client; rollback is reverting the commits.

## Open Questions

None.
