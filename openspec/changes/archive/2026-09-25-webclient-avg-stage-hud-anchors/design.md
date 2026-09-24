## Context

See proposal.md (Why). The current state was checked in code. C1, C2, C3, C4a, and C4b are assumed archived first.

- `components/HudFrame.vue` renders `hud-left` and `hud-right` (testids `anchor-hud-left` / `anchor-hud-right`, slots `hud-left` / `hud-right`), plus an `objectives` slot outside any anchor.
  - C4a bounds both anchors above the band.
  - C4b places `place` above `hud-left`.
  - The creation rule hides `hud-left`, and `.local-map` is hidden in combat and creation.
- `AppShell.vue` maps `panel-left` to `#hud-left`, `panel-right` to `#hud-right`, and `objectives` to `#objectives`. `HIDDEN_BY_MODE.creation` names `[data-anchor='hud-left']`.
- `AppClient.vue`:
  - `#panel-left` holds `StatusPanel` (C3: `v-show` by the vitals rule) and `PartyStrip` (C3: renders nothing for an empty party).
  - `#panel-right` holds `LocalMap`, `ParticipantFrame` (combat `context_actions`), and `TitleBallotMenu` (while ballot candidates exist).
  - `#objectives` holds `ObjectiveTracker` when `use-scene.js` `showObjectiveTracker` holds: `objectivesAvailable && rows.length > 0 && mode !== "creation"`.
- `ObjectiveTracker.vue` is a scoped `.obj` card with `position: absolute; bottom: calc(var(--band-h) + 12px); right: 16px; width: 238px` (C4a). It renders:
  - the `目標` header with `N 追蹤`
  - one row per `objectives.rows` entry: stage box, `objective_line`, `.pr` slot, `deadline_line`

  `QuestLog.vue` already renders each tracked quest's objective and deadline (`quest-log__quest-deadline`).
- `PartyStrip.vue` (after C3) renders `同伴 N / 4`, one `.comp` cell per slot, and `emptyCount` dashed `+ 邀請` cells. Each `.comp` cell holds:
  - an avatar
  - a name
  - an HP hairline
  - a state row with the combat token, HP numerals, and bond

  Each cell already carries `aria-label="<name> HP a/b 羈絆 <stage>"`.
- C1 made the minimap a fixed 218px card (`align-self: flex-end`) that measures nothing, so the anchor rename touches only comments in `LocalMap.vue`.

## Goals / Non-Goals

**Goals:**
- Name the top islands' anchors by their content (`vitals`, `map`), completing the §5.1 anchor set: place, vitals, map, band-message, band-command, actor-left, actor-right, plus the command-line row.
- The objective tracker as one line under the minimap, in exploration only.
- Compact party avatars under the vitals.
- Decide where `ParticipantFrame` and `TitleBallotMenu` live.

**Non-Goals:**
- Anchor geometry: `vitals` and `map` keep exactly the C4a / C4b boxes.
- The vitals visibility rule (C3) and the minimap card (C1): unchanged.
- The party drawer's rows (`PartyDrawer`): unchanged.

## Decisions

### D1. Rename, do not re-derive
`hud-left` becomes `vitals` and `hud-right` becomes `map` in HudFrame, AppShell, AppClient, `app-shell.css`, and every test selector. The geometry rules move unchanged: `vitals` keeps C4b's top offset under the place card, and `map` keeps `top: calc(var(--header-h) + 16px); right: 16px; width: calc(var(--right-column) - 28px)` with C4a's band-bounded `max-height`.
- The whole `map` anchor is `display: none` in creation. Its content (minimap, objective line, participant frame, ballot) is never meaningful there. Today only `.local-map` is hidden in creation.
- `HIDDEN_BY_MODE.creation` becomes `"[data-anchor='band-message'], [data-anchor='place'], [data-anchor='vitals'], [data-anchor='map'], [data-anchor='command-line']"`. `.local-map` is dropped because it is inside `map`. `HIDDEN_BY_MODE.combat` keeps `.local-map`.
- At widths up to 1350px the `--right-column` token becomes 246px (was 244px), so the `map` anchor (`right-column - 28px`) is exactly as wide as the 218px minimap card. At 244px the anchor was 216px, and the card's left border was clipped by the anchor's `overflow-x: hidden`. The only other consumers are the two scene-art captions positioned from the right column; they move 2px.

### D2. The objective line
`ObjectiveTracker.vue` keeps its props (`rows`) and its root testid `objective-tracker`. Its template becomes one row:

```
<div class="obj hud" data-testid="objective-tracker" role="region" aria-label="目標">
  <span class="obj__label">目標</span>
  <span class="bx" :class="{ done }" data-testid="objective-tracker__box--<id>">✓?</span>
  <span class="txt" data-testid="objective-tracker__text--<id>" :title="line">…</span>
  <span class="pr" data-testid="objective-tracker__progress--<id> | __reward--<id>">…</span>
  <span v-if="rest > 0" class="n" data-testid="objective-tracker__more">+{{ rest }}</span>
</div>
```

- Height is fixed by `height: 32px` with `white-space: nowrap`, and `.txt` truncates with an ellipsis.
- It is `position: static` inside the `map` anchor's flex column, so the column's `gap` spaces it from the minimap card.
- It is right-aligned with a content-fitted width: `align-self: flex-end; max-width: 100%`. The line's right edge lines up with the minimap card above it. A short objective stays compact; a long one grows leftward to the anchor's width and then truncates. `align-self` is required because `app-shell.css`'s `.elosern-root` override sets the anchor's `align-items: stretch`, which outranks `HudFrame.vue`'s own `flex-end`. `.local-map` follows the same pattern.
- It carries its own island chrome (panel fill, blur, `--line` border, `--radius`, `--shadow`), like the place card, so the standalone story does not depend on another component's global rule.
- The deleted pieces are the `N 追蹤` count (testid `objective-tracker__count`), the per-row `.row` loop, and the deadline line (`objective-tracker__deadline--<id>`). The quest drawer presents every tracked row and its deadline, one navigation action away (top bar 任務).

Why the first row: the committed `objectives.rows` order is the presenter's tracked order, and the tracker already renders it "in payload order". The first row is therefore the server's own primary objective. Showing it avoids inventing a priority rule.

*Alternative:* cycle rows over time. Rejected: that is motion (C11), and it would hide the progress tag half the time.

Exploration only: `HudFrame.vue` gets `.elosern-stage:not([data-elosern-mode="exploration"]) [data-anchor="map"] .obj { display: none; }`. It uses the stage's single mode attribute, as the matrix requires. `showObjectiveTracker` keeps its data conditions, so the component is still unmounted for empty or unavailable rows and in creation. The line has no tab stop, so no focus rescue is needed.

### D3. Compact party cells
`PartyStrip.vue`:
- keeps the root island (`party-strip`, `role="region"`, the whole-island activation), the header `同伴 N / 4`, and one `.comp` cell per slot with its existing `role="button"`, `tabindex="0"`, `aria-label`, and activation
- adds `:title` equal to that `aria-label`
- keeps the avatar (`party-strip__avatar`, portrait or initial glyph)
- moves the HP hairline (`party-strip__hp-bar`) directly under the avatar
- turns the combat token (`party-strip__token`) into a corner badge on the avatar
- deletes `party-strip__name`, the `.st` state row (numerals, bond), `emptyCount`, and the `party-strip__empty-slot` cells

Cells sit in one four-track row, `display: grid; grid-template-columns: repeat(4, minmax(0, 40px)); gap: 6px`. Each track is at most 40px, and the `minmax(0, …)` tracks shrink together when room is short. The `vitals` anchor is narrowest at 1280x720: 184px, or 160px of content inside the island's 12px side padding. There each track is about 35px, so a full party of four always fits in one row. The avatar is square (`aspect-ratio: 1`) and fills its track.

Why: the design (§5.2) asks for compact avatars, and the island now shares the column with the place card and the vitals. The name, numerals, and bond stay in every cell's accessible name and tooltip. They are also visible text in the party drawer (`PartyDrawer`'s compbig rows), one activation away. Invite padding duplicated the drawer's 空位 row, and C3 already made the drawer reachable at every party size.

### D4. ParticipantFrame and TitleBallotMenu stay in `map`
- **ParticipantFrame.** In combat the minimap is hidden, so the `map` anchor is free. The participant frame is a display-only list of tokens, names, and HP numerals. Putting it on `actor-right` would make a data list look like a standing portrait, and it would collide with C13, which animates foe portraits on `actor-right`. The frame stays an island in `map`, and `actor-right` stays empty.
- **TitleBallotMenu.** It is a transient prompt tied to no mode. It stays last in `map`, below the objective line, where it was (`#panel-right`) and where the anchor's `overflow-y: auto` bounds a long candidate list.

### D5. Spec strategy and archive order
Each MODIFIED block is written on the latest series text for that requirement. Every scenario title is kept (the objective requirement's "Active objectives list in payload order" keeps its title; its body now pins the first row plus `+1`). New scenarios are added for the exploration-only line, the map-anchor order, the truncating line, and the frame's anchor.

| Requirement | Written on top of |
|---|---|
| stage, visibility | C4b `webclient-avg-place-card-top-bar` |
| reference surfaces | C4a `webclient-avg-stage-shell` |
| island stack, party quickbar | C3 `webclient-retire-redundant-hud` |
| minimap convention | C1 `webclient-minimap-and-log-quick-fixes` |
| `webclient-local-map` minimap | C2 `webclient-full-map-fit-view` (two words change) |
| objective tracker, participant frame | main spec (no series change touches them) |

**Archive order: C1 → C2 → C3 → C4a (`webclient-avg-stage-shell`) → C4b (`webclient-avg-place-card-top-bar`) → C4c (this change).** If any earlier block changes before archive, this change's block for that requirement must be re-synced, keeping only this change's edits.

### D6. Short viewports compact the vitals stack
At 1280x720 the `vitals` anchor had 300px. The populated stack (vitals, eight conditions with the overflow disclosed, a party of four) measured 431px, and it was already 332px without the party. The earlier browser test only checked that the islands did not intersect each other, never that they fit their anchor. The island-stack requirement asks for a fit, so under `@media (max-height: 820px)` (1440x900 has 490px and needs nothing):
- `--place-h` becomes 56px (the card's content is 47px tall).
- A new `--stage-inset-y` token (16px default, 10px here) is the vertical gutter above the place card and the `map` anchor and below both island stacks. It replaces the `16px` / `44px` / `32px` literals in the anchor offsets of `HudFrame.vue` and `app-shell.css`.
- The `vitals` anchor gap becomes 8px.
- `VitalsTrack.vue`: each gauge becomes one row (label, 7px bar, numerals), with tighter padding.
- `ConditionChips.vue`: chips shrink to 26px; the island, label, and disclosure get tighter spacing, and the disclosure caps at 64px.
- `PartyStrip.vue`: tighter padding.

Measured result at 1280x720: 313px of content in a 323px anchor. Every value and marker stays visible. Only spacing, the chip size, and the vitals row arrangement change. *Alternative:* let the anchor scroll the disclosed overflow. Rejected, because the party island would then depend on scrolling.

## Risks / Trade-offs

- [The objective line shows only the first tracked quest] → The `+N` count states that more exist, and the quest drawer lists them. This is the design's one-line decision.
- [Compact cells hide the party's HP numerals from sighted users on the stage] → The hairline still shows the ratio. Numerals are in the tooltip and accessible name, and visible in the party drawer. In combat the participant frame shows each joined companion's numerals, because companions are participants.
- [Tests and stories pin `objective-tracker__count`, `__deadline--*`, `party-strip__empty-slot`, `party-strip__name`] → Task 1.2 greps them all, and sections 3 and 4 rewrite or delete each hit.
- [Many browser tests name `hud-left` / `hud-right`] → Task 5.1 greps `anchor-hud-\|data-anchor=\"hud-\|data-anchor=\\\\\"hud-\|hud-left\|hud-right` across `web/tests/browser` and re-points every hit.

## Migration Plan

None. The client is unreleased.
