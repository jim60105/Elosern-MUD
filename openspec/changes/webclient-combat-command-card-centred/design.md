# Design: Centre the combat command menu over the stage

See `proposal.md` for the motivation and `specs/` for the observable contract. This document records how the
existing pieces are rearranged and why.

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
- The dialogue card geometry (HudFrame `[data-anchor="choices"]`): top `header + inset`, bottom
  `--stage-caption-top + 8px·S`, `width: min(560px·S, 40%)`, centred. Measured in Storybook at 1600x900 it spans
  x≈490–1110; the foe line-up spans x≈900–1290, so the dialogue width would cover foes.
- The open stage span between the figures is already computed for the scene caption in `styles/app-shell.css`:
  left `actor-left-inset + actor-h·2/3 + 16px·S`; right `max(actor-right box + 16px·S, foe reach + 16px·S)` using
  `--foe-lineup-span` / `--foe-front-scale`, which AppClient writes on `.elosern-root` and holds while a leaving
  foe fades.
- Worked geometry (S = 1 at 1451x790, S = 1.4 at 2560x1440, from the tokens):

  | Viewport | Foes | Player box right | Leftmost foe box left | Open span (with 16px·S gutters) | Card (W = min(400·S, span)) |
  |---|---|---|---|---|---|
  | 1451x790 | 1 | 461.5 | 944.5 | 477.5–928.5 (451) | 400 wide, 525.5–925.5, centre = stage centre |
  | 1451x790 | 2 | 461.5 | 843.6 | 477.5–827.6 (350) | 350 wide, centre 652.5 |
  | 1451x790 | 3 | 461.5 | 780.4 | 477.5–764.4 (287) | 287 wide, centre 621 |
  | 2560x1440 | 1 | 770.8 | 1724.8 | 793.2–1702.4 (909) | 560 wide, 1000–1560, centre = stage centre |
  | 2560x1440 | 3 | 770.8 | 1425.7 | 793.2–1403.3 (610) | 560 wide, 843–1403, centre 1123 |

  The `choices` anchor span is 414px tall at 1451x790 (58 → 472) and 813px at 2560x1440.
- The companion line-up (`components/CompanionLineup.vue`) shifts a multi-figure group right toward the centre
  (`translateX(max(0, reach − actor-left-inset + 16px·S))`); at 1451x790 a five-figure party moves the controlled
  figure ~194px right, which would leave almost no open span. Dialogue already uses a `compact` layout that clamps
  the overlap so the group clears the dialogue card.

## Goals / Non-Goals

**Goals:**

- One place for "what do I do next": combat commands appear where the dialogue list and room cards appear, in the
  same card frame.
- Immediate combat state stays readable: foes, their plates/gauges, the focused-target cue, the player's figure and
  party, the vitals dock, the participant frame, the scene caption and the combat log.
- Zero behaviour change to the combat menu model, router, payloads, protocol and telnet.

**Non-Goals:**

- Re-skinning the combat rows as ChoiceCard rows (digit badges, ChoiceCard's own key handling). The combat card
  keeps DockMenu's row forms and the router; only the shell (frame, crest, corners) is shared.
- The exploration dock, the SkillBook casting dock (`SkillUseDock`), dialogue, telnet.
- Changing the scene caption rule (it keeps its own copy of the open-span expression; see D3).

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
- Alternatives rejected: (a) CSS-only repositioning of `band-command` — its containing block is the band, so it
  cannot be centred on the stage box with the dialogue anchor's tokens; (b) rendering a second ActionDock in the
  `choices` slot under `v-if` — remounts the dock on every combat entry/exit, breaks the persistent-node contract
  and loses the exploration pane's state; (c) re-implementing the combat menu inside `ChoiceCard` — duplicates the
  router's key handling, breaks the `dock-menu` listbox contract and the grid geometry of target/scale frames.

### D2. The band collapses in combat like it does in dialogue, but with `display:none`

In combat `band-command` is empty (its content teleported), so HudFrame sets `.stage-band` to one column and
`[data-anchor="band-command"]` to `display:none`; the message region spans the band from the commit's frame. The
message page keeps its `--message-measure` reading column (centred), so pagination does not change and the combat
log sits centred under the card. No slide is needed because nothing visible leaves the band. On leaving combat the
region returns in the commit's frame and the existing `data-flip="combat-exploration"` flip-out plays on the dock
that has just moved back. HudFrame's flip watcher stops setting `data-flip` for `*-combat` changes (nothing in the
region to flip); the `elosern-panel-flip-in` rule for `-combat` is removed.

### D3. Card geometry: dialogue's vertical span, centred, clamped into the open span

HudFrame declares two stage-level custom properties on `.elosern-stage` (so `--foe-*` from `.elosern-root`
inherit; in stories without `.elosern-root` they fall back to "no foes"):

```css
--stage-open-left: calc(var(--actor-left-inset) + var(--actor-h) * 2 / 3 + 16px * var(--ui-scale));
--stage-open-right: max(
  calc(var(--actor-right-inset) + var(--actor-h) * 2 / 3 + 16px * var(--ui-scale)),
  calc(max(var(--actor-right-inset), var(--foe-face-clear) - var(--actor-h) * var(--foe-front-scale, 1) / 3)
       + var(--actor-h) * 2 / 3 * var(--foe-lineup-span, 0) + 16px * var(--ui-scale)));
```

and in combat the `choices` anchor keeps its dialogue `top`/`bottom` but takes

```css
--combat-card-w: min(400px * var(--ui-scale), 100% - var(--stage-open-left) - var(--stage-open-right));
width: var(--combat-card-w);
left: clamp(var(--stage-open-left), 50% - var(--combat-card-w) / 2, 100% - var(--stage-open-right) - var(--combat-card-w));
```

The expressions are the scene caption's (app-shell.css), so the card and the caption share one notion of the open
stage; a comment in both places says to keep them in step. The `left` transition glides with the line-up
(`transition: left …, width … calc(var(--motion-actor) * var(--motion-travel))`, like the caption's `right`).

- Width cap 400px·S: a command list plus a stacked detail reads comfortably at that measure and leaves stage art
  visible on both sides; the dialogue's 560px would cover the front foe at 1451x790.
- Height: the dock in card mode is `height: min(100%, 420px·S)`, centred vertically by the anchor's flex column, so
  no frame resizes or moves the card (the band principle "the dock has a fixed height" carried into the card).
- Alternatives rejected: a dead-centre card of dialogue width (covers the foe line-up and the target cue); an
  upper-centre card (covers back-row foe heads at 3 foes, 1451x790, whose tops stand ≈y 237); a card centred on the
  open span rather than the stage (off-centre even with one foe, contrary to the request).

### D4. The party line-up compacts in combat so it never enters the open span

In combat AppClient passes `compact` to CompanionLineup as in dialogue, and the compact edge becomes the open span's
left bound: CompanionLineup's compact clamp reads `--companion-compact-edge` (default: today's
`max(30vw, 50vw - 280px * S)`), and HudFrame sets it in combat to `var(--stage-open-left)`. With that edge the
clamp keeps `reach ≤ actor-left-inset − 16px·S`, so the compact translate is never positive: the controlled figure
stays at its standard box and companions compress leftward behind it. Rejected: deriving the card's left bound from
the live group width (at 1451x790 a five-figure party would leave ~90px between party and foes).

Trade-off recorded for the user: in combat with two or more companions the rear companions show less of
themselves than before (as they already do in dialogue). The modified companion requirement states it.

### D5. ActionDock gains a `card` presentation; the pane host stacks

`ActionDock` takes `card: Boolean` (AppClient passes `store.view.mode === 'combat'`). In card mode the root carries
`action-dock--card choice-card choice-card--still`, renders a decorative `<span class="choice-card__corners"
aria-hidden="true">`, drops its own `::after` focus mark (that pseudo-element is the ChoiceCard crest), brightens the
frame with `.choice-card:focus-visible`'s declarations while `:has(:focus-visible)`, and sizes itself
`width: 100%; height: min(100%, 420px·S); max-width: none; margin: 0`. Reusing the global `choice-card` classes
shares the frame without copying its gradient/border literals; `choice-card--still` disables ChoiceCard's mount
animation because the card's entrance is keyed on the live mode change instead (D6).

The stacked master-detail lives in `styles/app-shell.css` next to the existing `.dock-pane-host--bounded` rules
(unprefixed, so Storybook and the live client agree): `.action-dock--card .dock-pane-host--bounded` becomes a
column; the row region takes `flex: 1 1 auto` with a three-row minimum and scrolls; the detail
(`.dock-detail` / `.skill-detail-pane`) takes `flex: 0 1 auto; max-height: 50%; align-self: stretch` and scrolls.
The `.elosern-root .skill-detail-pane*` typography duplicates (app-shell.css) move into `SkillDetailPane.vue` so
Storybook renders what players see. The band-scoped `.elosern-root [data-anchor="band-command"] .dock-detail` /
`.skill-detail-pane` rules stay for the exploration SkillUseDock.

### D6. Motion: entrance keyed on the live mode change; reconnect at rest

`.elosern-stage[data-mode-change$="-combat"] [data-anchor="choices"] > .action-dock--card` runs
`elosern-combat-card-in var(--motion-reveal) var(--ease-enter) var(--motion-flash) backwards` (opacity 0 and
`translateY(var(--motion-shift-sm) × var(--motion-travel))` → rest). `data-mode-change` is never set on mount or
reconnect, so those render at rest; reduced resolves to a 150ms fade with no delay and no rise, off to 0ms. The node
is inserted into the anchor at the commit, so the animation starts once per entry. The `backwards` fill only holds
paint: the rows are focusable and clickable from the commit's frame. The foe line-up entrance (after half the
flash) is unchanged, so the card and the foes arrive together as the flash releases.

### D7. Focus re-home across the move

Moving a focused node blurs it. AppShell's mode watcher, after `await nextTick()`, calls `restoreFocusHome()` when
the mode entered combat and focus is lost (`focusIsLost`). Leaving combat for exploration is already covered by
`focusExplorationEntry` (lost focus → exit compass), and combat → dialogue by the dialogue branch. Focus in the
command field, a drawer or an overlay is not lost and is left alone.

### D8. Storybook

- `Core/AppShell` renders the real AppClient, so the existing CombatHud family shows the card. A `combatKeys` arg
  replays router keys through `store.focusPress` after the snapshot commits; new stories: `CombatTargetStep`,
  `CombatSkillDetail`, `CombatDisabledCommand`, `CombatMasterScale` (a skill carrying `freeform_scales`, as in
  `stories/fixtures/skills.js`) and `CombatFullParty` (four companions, three foes).
- `Action/ActionDock`: the combat stories render `card: true` inside a 400×414 frame with the stacked pane host;
  add `CombatTargets` and `CombatMasterScale` (with `SkillDetailPane` as the row region's sibling);
  `CombatPlayback` shows the cue inside the card.
- `Action/DockMenu`: `TargetFrame`/`FixedGridFrame` render inside a card-width host so they no longer depict the
  band width.
- No component is added; `component-manifest.json` stays frozen.

## Risks / Trade-offs

- [Teleport + focus in jsdom/Chromium differ] → Vitest asserts the node move and the re-home call; one live browser
  method asserts real focus after entering and leaving combat.
- [The `.elosern-root` duplicates diverge from Storybook] → D5 folds the SkillDetailPane duplicates into the
  component; the card geometry lives only in HudFrame; geometry is verified by a live-client browser test, not
  Storybook alone.
- [At 1451x790 with three foes the card is 287px wide] → rows wrap long labels; the scale frame's N columns
  compress (`A fixed-column dock pane stays inside the command region` keeps rows inside the pane); the browser test
  exercises the master scale step and the area target grid at that width.
- [Beat lunges (24px·travel) briefly cross the 16px gutter under the card] → decorative and momentary; the card
  paints above the stage actors as the dialogue card does.
- [A reload straight into combat must find the Teleport target] → `defer` + an id on the same component's anchor;
  covered by `test_reload_in_combat_plays_nothing` and a Vitest mount in combat.
- [Message window widens in combat] → its page keeps the measured column; the beat pages measure the same width,
  so pagination is unchanged (the region width is not the page width).

## Migration Plan

Pre-release client; no data or protocol migration. Rollback is reverting the change's commits.

## Open Questions

None that change the specs. Whether the card should later grow a caption (e.g. "戰鬥") at the root is deferrable:
the breadcrumb already names the frame below the root.
