# Design: Pick combat targets on the stage figures

See `proposal.md` for the motivation and `specs/` for the contract. Builds on
`webclient-combat-command-card-centred` (the narrow dead-centre card; its design D3 holds the measured geometry).

## Context

- **The real TargetSpec forms** (`world/skills/registry/vocab.py` `TargetSpec`; `webclient-combat-menu` "Combat
  target selection sends one shape per TargetSpec"; `web/static/webclient/js/elosern/combat_menu.js`
  `targetItemsFor`):
  - `none` → one `none-confirm` item (施展), payload without target fields.
  - `self` → one `self-confirm` item (對自己施展), payload without target fields; the server binds the puppet.
  - `single` → one `target-<id>` item per server candidate (`skill.targets`, in participant order), payload
    `target_ids: [id]`; candidates may be in a non-active state (the item's description names it).
  - `area` → one `area-<id>` toggle item per candidate (`toggle-target`, Space or Enter toggles), one
    `shorthand-<key>` item per approved shorthand the descriptor carries (`all-enemies`, `all-allies`, `all`;
    `world/rules/targeting.py` `AREA_SHORTHANDS`; choosing one clears the explicit selection), then `area-confirm`,
    which submits `areaPayload` (explicit IDs in presenter order, or the shorthand). There is **no** area-centre or
    radius form: AoE in this game is "a set of participants", so no anchor-movement presentation is specified.
  - A disabled skill's frame is one `skill-disabled` item.
- Participants carry `team` `party` | `foes` and `state` `active` | `fled` | `knocked_out` | `defeated`
  (`world/rules/combat_view.py`); identities are ObjectDB ids.
- **The stage draws**: the controlled figure plus up to four companions (`companionFigures`, `displayedLineup`,
  `COMPANION_LINEUP_MAX = 5`) and up to three *active* foes (`activeFoes`, `FOE_LINEUP_MAX = 3`; during playback the
  round's pre-round foes). A candidate may therefore have no figure: foes four and five, any non-active foe, a party
  participant the line-up does not draw.
- **Existing machinery**: `AppClient.vue` `focusedCombatTarget` already resolves the focused item's single identity
  and `FoeLineup` marks `data-target` on the plate; `onRouterEvent` handles `toggle-target`, `choose-shorthand`,
  confirm and `target-*` submit; `focusPress` (`stores/elosern/interaction.js`) already claims keys before the
  frozen router (digits, the presence rail) using only `router.focusItemByKey` / `router.confirm`; `StageActor`'s
  `dimmed` prop is the dialogue listener dim (`data-speaking="false"`, `filter: brightness(var(--actor-dim))`, eased
  on `--motion-base` at `full`, instant below).

## Goals / Non-Goals

**Goals:** pick every real target form on the stage with keyboard and pointer; reuse the dialogue dim; keep items,
payloads, the router source, the UMD model and the protocol unchanged; accessible without colour or motion.

**Non-Goals:** confirming friendly fire (`webclient-combat-cross-side-confirm`); drawing more than three foes;
changing which participants the server lists as candidates; the SkillBook (exploration) casting flow.

## Decisions

### D1. One pure model of the step: `stores/elosern/stage_targets.js`

`stageTargetModel({ menu, skill, participants, drawnParty, drawnFoes, focusKey, selected, shorthand })` returns
`null` outside a step, else
`{ form, skillKey, label, positions[], focusKey, lit[], selectable[], selectedIds[], offStage[], announce }`, where each
position is `{ key, kind: "member"|"group"|"confirm"|"self", identities[], side, digit, offStage }`. It is a step only
when the current descriptor source is `combat.target`/`combat.skill`, the menu's items are target items of an
enabled `single`/`self`/`area` skill (never `scaleChoice`, `none-confirm` or `skill-disabled`), and playback is not
locked.

- **Stage order**: `drawnParty` is the displayed party figure identities rear → controlled (the reverse of the
  `companionFigures` slot order) and `drawnFoes` the drawn foe identities rear → front (the reverse of the line-up's
  slot order); both come from the same pure helpers the components draw with, so the store needs no DOM
  measurement. Members = drawn candidates in that order, then undrawn candidates in server order (`offStage`). AREA
  then appends group positions in the descriptor's shorthand order and the confirm position.
- **Lit sets**: member → `[id]`; group → the candidates of that side (`all-enemies` → `team === "foes"`,
  `all-allies` → `team === "party"`, `all` → every candidate); confirm → the explicit selection, else the chosen
  shorthand's set, else empty; self → the controlled figure's identity.
- **Labels**: side 敵方/我方 from `team`; groups 全體敵人/全體我方/全體 (client display labels for the three approved
  keys; the payload keeps the key); 場外 for an off-stage member; the exact announcement templates of the spec
  (with the session token appended when display names repeat) are built here so Vitest
  pins them.
- Identity joins use `String(identity)` exactly as `lineupSlotByIdentity` does.

### D2. Arrow keys: a claim in `focusPress`, nothing else

When `view.stageTarget` is non-null and the key is an arrow, `focusPress` moves to the next/previous position key
(wrapping; no-op for a single position; from a focused item that is no position, such as a back row, Right/Down
go to the first position and Left/Up to the last) with `router.focusItemByKey(key)` and returns `true`. Enter, Space, digits,
Escape and `/` continue to the existing paths, so the router's own geometry, item order and confirm path are
untouched and the digits still address items in server order (each marker shows its digit, D4). Rejected: reordering
the frame's items to stage order in the frame resolver — it would change digit mapping, the "server candidate order"
contract and the AREA grid geometry.

### D3. The card collapses to a target prompt

`ActionDock` (card mode) takes `stageTarget`; when non-null it renders the prompt instead of the visible row region:
all in `--text-sm` (16px, 22px·S lines): line 1 the action label (with the scale label from `scaleLabelFor` when the
skill has a chosen 威力), ` ‧ 選擇目標` and a right-aligned `Esc 返回`; line 2 the focused position summary; both
single lines with an ellipsis; then (AREA) one chip per group position and the confirm chip, 28px·S tall with 4px·S
gaps, wrapping onto at most two rows (全體敵人, 全體我方, 全體 and 施展（n） need ≈ 290px at S = 1, more than the
214px inner width). The chips are `<button tabindex="-1">` whose `mousedown` is prevented and whose click handler
returns DOM focus to `#action-dock`, because `bridge.js` leaves Enter on a focused button to the button. The DockMenu row region stays mounted with the `hidden` attribute
(so router state and focus bookkeeping are unchanged) and DOM focus moves to `#action-dock` when it was inside the
row region. The card's anchor rule from the previous change keeps `left`/`width`/`top`; in the step the dock's
height is `auto` with `max-height: 136px·S` (12 + 22 + 22 + 28 + 4 + 28 + 12 = 128 at S = 1). Clearance: markers are
24px·S tall with their bottom 4px·S above the figure box. The only marker inside the card's columns at the measured
configurations is the rearmost of three foes (box centre 856.1 vs card right edge ≤ 865.5 at 1451; marker 948.8–975.2
vs card right edge ≤ 954.4 at 1600), whose marker top is 237 − 4 − 24 = 209 / 269.9 − 4.4 − 26.5 = 239; the prompt
ends by 58 + 136 = 194 / 70.6 + 150 = 220.6, at least 8px·S above it. With two foes the rear marker centre (947.1 /
1065.8) and every party marker (controlled box centre ≤ 466.6 / 531.0) lie outside the card's columns.

A `<p role="status" aria-live="polite" class="sr-only">` inside the card carries `stageTarget.announce`; it changes
only with the focus or the selection.

### D4. Figures: dim, lit, markers, hit areas — inside the existing line-ups

`FoeLineup` and `CompanionLineup` take `targeting` (`null` or `{ lit, selectable, selected, focused, digits }` keyed by
`String(identity)`). When non-null:

- each StageActor's `dimmed` is `!lit.has(id)` (CompanionLineup ignores `speakingIdentity`/`dimmed` for the step;
  FoeLineup's `:dimmed="false"` becomes this expression) — the dialogue dim, no parallel treatment;
- each selectable slot renders `<span class="stage-target__marker" data-testid="stage-target-marker"
  :data-state="focus|selectable" :data-selected>` (▼ filled + digit when focused, ▽ outline + digit otherwise, ✓
  when selected) positioned `bottom: calc(100% + 4px·S)` of the slot, clamped below the top band with
  `max(…)` on its top, and a `<span class="stage-target__hit" data-testid="stage-target-hit">` covering the slot
  box; both are the only `pointer-events: auto` elements and carry `aria-hidden` like the rest of the line-up
  (keyboard and the live region are the accessible path);
- a lit focused slot gets `data-target-focus="true"`: at `full` a `filter: drop-shadow(...)` ring animated by
  `elosern-target-pulse` (1.2s, `infinite alternate`, `--ease-standard`); under `[data-motion-level="reduced"]`,
  `[data-motion-level="off"]` and `@media (prefers-reduced-motion: reduce)` the ring is static and brighter and the
  marker gains an underline bar. No figure's box, z or position changes.

`FoeLineup`'s existing `data-target` plate cue keeps following `focusedCombatTarget` (now extended to groups by
`lit`). `ParticipantFrame` takes `targetCues` and sets `data-target-cue` (`focus`/`selectable`) plus an arrow glyph on
rows of off-stage positions.

### D5. Pointer

The store gains `stageTargetPointer(key, action)` (`"hover"` → `focusItemByKey(key)`; `"activate"` →
`focusItemByKey(key)` then `router.confirm({ source: "pointer" })`), the same façade members the digit path uses.
Hit areas call it on `pointerenter`/`click`; prompt chips on `click`. Repeated `click` relies on the router's existing
in-flight lock.

### D6. Motion and reconnect

Dim changes use StageActor's existing eased filter at `full` (instant below). Markers appear without an entrance.
On mount/reconnect/panel replacement nothing animates except the steady pulse loop at `full`. Playback lock clears
the model (D1), so beats play on an undimmed stage.

### D7. Storybook

`Core/AppShell` (with the previous change's `combatKeys` arg): `TargetSingleFoe`, `TargetSingleAlly`,
`TargetSelf`, `TargetAreaExplicit` (two selected, focus on confirm), `TargetAreaAllFoes`, `TargetAreaAllAllies`,
`TargetOffStageFoe` (five foes, focus on the fifth), `TargetReducedMotion` (motion `reduced`). `Core/FoeLineup` and
`Core/CompanionLineup`: a `Targeting` story each. Fixtures: a SINGLE skill with ally+foe candidates, a SELF skill,
an AREA skill with both explicit candidates and the three shorthands (extend `stories/fixtures/skills.js`). No new
component; `component-manifest.json` unchanged.

## Risks / Trade-offs

- [Stage order computed from helpers, not boxes] → the browser method `test_targets_are_picked_on_the_stage`
  asserts the model's member order equals the markers' on-screen left-to-right order.
- [Arrow claim could swallow keys outside the step] → claimed only while `view.stageTarget` is non-null; Vitest
  pins arrows reaching the router in every other combat frame.
- [Hit areas over overlapping figures] → the slot z order already paints the front foe above the rear; its hit area
  wins where they overlap; the rear foe stays reachable by its marker and by keys.
- [Existing browser tests click card target rows] → listed in tasks and migrated to the stage hit areas or to keys.

## Migration Plan

Pre-release client; no data or protocol migration. Rollback is reverting the change's commits.

## Open Questions

- Whether foes four and five should stand on the stage at all is out of scope; they are off-stage positions cued on
  the participant frame.
