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
- **The stage draws** (after `webclient-combat-formation` and `webclient-combat-defeated-foes`): the controlled
  figure, up to four companions, and every foe that has not fled (up to 15), all at the formation engine's boxes,
  with fallen figures in their defeated/down treatment and one plate per non-controlled figure with a marker slot
  above it. Only a fled participant can be a candidate without a figure. There is no participant frame.
- **Existing machinery**: `AppClient.vue` `focusedCombatTarget` already resolves the focused item's single identity
  and `FoeLineup` marks `data-target` on the plate; `onRouterEvent` handles `toggle-target`, `choose-shorthand`,
  confirm and `target-*` submit; `focusPress` (`stores/elosern/interaction.js`) already claims keys before the
  frozen router (digits, the presence rail) using only `router.focusItemByKey` / `router.confirm`; `StageActor`'s
  `dimmed` prop is the dialogue listener dim (`data-speaking="false"`, `filter: brightness(var(--actor-dim))`, eased
  on `--motion-base` at `full`, instant below).

## Goals / Non-Goals

**Goals:** pick every real target form on the stage with keyboard and pointer; reuse the dialogue dim; keep items,
payloads, the router source, the UMD model and the protocol unchanged; accessible without colour or motion.

**Non-Goals:** confirming friendly fire (`webclient-combat-cross-side-confirm`); the formation itself;
changing which participants the server lists as candidates; the SkillBook (exploration) casting flow.

## Decisions

### D1. One pure model of the step: `stores/elosern/stage_targets.js`

`stageTargetModel({ menu, skill, participants, formationOrder, focusKey, selected, shorthand })` returns `null` outside
a step, else `{ form, skillKey, label, positions[], focusKey, lit[], selectable[], selectedIds[], offStage[], announce }`,
where each position is `{ key, kind: "member"|"group"|"confirm"|"self", identities[], side, digit, offStage }`. It is
a step only when the current descriptor source is `combat.target`/`combat.skill`, the menu's items are target items of
an enabled `single`/`self`/`area` skill (never `scaleChoice`, `none-confirm` or `skill-disabled`), and playback is not
locked.

- **Stage order**: `formationOrder` is the drawn identities sorted by their formation box's horizontal centre, from
  left to right (the front rank first on a tie), published by AppClient from the same `formation` object the stage
  draws. Members = drawn candidates in that order, then undrawn candidates (only a fled participant) in server order
  (`offStage`). AREA then appends group positions in the descriptor's shorthand order and the confirm position.
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
height is `auto` with `max-height: 136px·S` (12 + 22 + 22 + 28 + 4 + 28 + 12 = 128 at S = 1). Clearance needs no
derivation any more: every marker slot and plate stands outside the formation's dead-centre gap, and the card fills
only that gap.

A `<p role="status" aria-live="polite" class="sr-only">` inside the card carries `stageTarget.announce`; it changes
only with the focus or the selection.

### D4. Figures: dim, lit, markers, hit areas

`FoeLineup` and `CompanionLineup` take `targeting` (`null` or `{ lit, selectable, selected, focused, digits }` keyed by
`String(identity)`). When it is non-null:

- each StageActor's `dimmed` is `!lit.has(id)`, the dialogue dim with no parallel treatment; a fallen figure keeps its
  fallen treatment whether lit or not, and the focus ring still applies to it;
- each selectable slot renders a hit area `<span class="stage-target__hit" data-testid="stage-target-hit">` covering
  its figure box, the only `pointer-events: auto` element in the portrait anchors (`aria-hidden`; the keyboard and
  the live region are the accessible path);
- the arrow markers render in the `plates` layer at each figure's formation marker slot, directly above its plate:
  `<span class="stage-target__marker" data-testid="stage-target-marker" :data-state="focus|selectable"
  :data-selected>`, ▼ filled with the digit when focused, ▽ outlined with the digit otherwise, ✓ when selected;
  markers take a pointer like the hit area;
- a lit focused figure gets `data-target-focus="true"`: at `full` a `filter: drop-shadow(...)` ring animated by
  `elosern-target-pulse` (1.2s, `infinite alternate`); under reduced, off and `prefers-reduced-motion` the ring is
  static and brighter and the marker gains an underline bar;
- plates are never dimmed: they carry the hit points the choice depends on. No figure's box, z or position changes.

AppClient bumps the plates' `plateTooltipClose` counter (`webclient-combat-figure-plates` D3) when a step starts.
Hovering a glyph during the step opens its tooltip only; the glyph is not a hit area.

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

None.
