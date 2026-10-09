# Scene Overview Redesign Design

**Date:** 2026-10-10
**Status:** Design approved in brainstorming; interaction prototype committed. Split into three OpenSpec changes (§10); implementation not started.
**Scope:** Replace the exploration command panel's chip rows (`SceneOverview.vue`: 出口 / 人物 / 物件 / footer) with three surfaces placed by meaning: an exit compass for movement, a presence rail on the stage for people and things, and room actions on the place card, all explained by one shared readout line.

The current scene overview packs every exploration decision into the 484×220 command panel as wrapping chip rows. Exits read as a list of arrows plus destination names. The arrow is the only spatial cue, and in the wilderness most chips repeat the same name (西部丘陵與谷地), so the player has to read every chip to find the one they want. People, objects, and room-level actions (查看房間, 等待／休息, 建議) sit in the same grid with the same visual weight. The panel scrolls, and the key hints (`數字鍵 1-9 · Enter 執行 · Esc 返回`) take a permanent line.

**Visual reference:** the interaction prototype is committed at [`docs/design/scene-overview-redesign/`](../../design/scene-overview-redesign/):

- `ScenePrototype.vue`: the whole exploration screen.
- `ExitCompassPrototype.vue`: the compass, with live pointer and keyboard behavior.
- `ChoiceCardPrototype.vue`: the centred card.
- `compass-model.js`: the pure angle, snap, portal-slot, and continuous-step rules from §3.
- `prototype-data.js`: a small mock world with wilderness, grid town, interior, and instance rooms.
- `ScenePrototype.stories.js`.

Storybook loads it under `Design/SceneOverviewRedesign` with the stories `Wilderness`, `TownGate`, `MarketSquare`, `GuildInterior`, and `PersonFocus`. Run `pnpm run serve-storybook` and open `?path=/story/design-sceneoverviewredesign--town-gate`.

The prototype is the source of truth for geometry, colors, and the feel of hover-aim, click, and hold. It is reference only: it reads no payload, sits outside the component-coverage manifest, and is not imported by the app. Where this document and the prototype disagree on behavior, this document wins.

## 1. Authority and Constraints

- `web/webclient-app/AGENTS.md` governs. Desktop 16:9 only, and changes ship through OpenSpec. The stage stays large, and the bottom band stays message window (2/3) plus command panel (1/3). Before restyling a class, grep `styles/app-shell.css` for its `.elosern-root` duplicates. Verify geometry in the live client, not only in Storybook.
- Server-authoritative honesty stays. The client renders only committed payload fields and never enables an action the server disabled. A disabled exit stays aimable so the player can read its server-authored reason. `explore.move` payloads (`{exit_ref, current_node}`) and every look/interact payload stay byte-identical to what `ExplorationMenu` builds today.
- Style comes from `styles/tokens.css`: ink grounds, paper text, gold for focus and emphasis, seal red for warnings and the current-position dot. Every size is written `calc(<n>px * var(--ui-scale))` or uses a token. No text is smaller than `--text-xs`.
- Motion respects the effective motion level. At `off`, every transition resolves in the commit frame, and the shake on a blocked move becomes a static seal-red flash of the readout.

## 2. Player Decisions and Placement

This section applies the game-ui-design workflow: map each exploration decision to the minimum information it needs, then place that information where it costs the least to check.

| Decision | Frequency | Information needed | Placement |
| --- | --- | --- | --- |
| Where to go | Highest | Bearing, destination name, passability | Exit compass in the command panel, cross-checked on the minimap |
| Whom to interact with | Medium | Who is present, what they afford | Presence rail on the stage floor, verbs on the centred card |
| What to inspect | Low | Object names | Presence rail, after a separator |
| Let time pass or re-read the room | Low | Current time and place | Buttons on the place card, beside the values they act on |
| What to do next (LLM suggestions) | Low | Suggestion count | 建議 N pill in the command panel |

This placement addresses three review findings from the current UI:

- Exit chips encode direction only as a glyph, so finding an exit means reading every chip. The compass encodes bearing as position.
- People, objects, and room actions share one visual weight. The new layout gives each group its own place and shape.
- Permanent key hints spend panel space. They move to the help overlay (?).

## 3. Exit Compass (`ExitCompass.vue`)

### 3.1 Angle model (`components/compass-model.js`, pure)

Each exploration exit resolves to exactly one of two kinds: **angled** or **portal**. The rules apply in this order:

1. **Map bearing.** The rule applies when all of these hold:
   - The committed `local_map.layer` is `grid` or `wilderness`.
   - The exit's `destination` is a node in the committed local map.
   - Both the current node and the destination carry coordinates, and the coordinates differ.

   The angle is `((atan2(dx, dy) in degrees) mod 360)` over the raw payload `x/y`, with +y north and angles clockwise from north. This is the same formula as `LocalMap.remoteDirection`, so the compass and the minimap always agree. It gives irregular city bearings such as 37° or 323°.
2. **Direction word.** Otherwise, if the exit label normalizes to a canonical direction (`ExplorationMenu`'s `DIRECTION_ALIASES`, minus up and down), the angle is that direction's fixed value (north 0°, northeast 45°, …).
3. **Portal.** Everything else is a portal: named doors in `interior` and `instance` layers, cross-layer gates whose label is not a direction word, destinations missing from the map, and up and down. `interior` and `instance` coordinates are never used for bearings, because the minimap's radial layout spreads those angles evenly and they carry no geographic meaning.

**Portal slots.** Portals sit on an outer track:

- Up is pinned to 0° and down to 180°.
- The other portals spread evenly over a 12-slot (30°) ring. Each takes the free slot nearest its ideal position `round((i + 0.5) · 12 / n)`; on a tie, the clockwise slot wins.
- More than ten non-vertical portals switch the ring to 24 slots.
- Order is the payload order of the exits.

**Snap.** An aim angle snaps to the nearest angled exit within ±30°. A tie goes to the smaller clockwise angle. An aim with no angled exit within tolerance has no target.

**Cycle order.** The `[` / `]` keys walk the angled exits by ascending angle, then the portals by ascending slot.

The module exports `resolveTargets`, `snapAngled`, `snapPortal`, `aimFromPointer`, `aimFromKeys`, `nextStep`, and the constants `SNAP_TOLERANCE = 30`, `DEAD_ZONE = 0.2`, `HOLD_MS = 400`, `STEP_DWELL_MS = 350`. `compass-model.js` in the prototype is the reference implementation of these rules.

### 3.2 Visuals

- **Pad.** A circular pad sized to the band height minus padding: about 198 px at 1451×790, with `--ui-scale` applied. It carries four cardinal ticks, a dotted dead-zone ring, and the seal-red current-position dot at its centre. The pad has no text.
- **Angled exits.** Gold pips at their true angle, at about 83% of the pad radius. A disabled exit is a hollow dashed pip. The aimed pip grows, brightens, and draws a faint ray from the centre.
- **Aim wedge.** A faint gold ±30° wedge marks the capture sector of the current pointer aim.
- **Portals.** Lozenge beads on a dashed outer track (⇧ up, ⇩ down, ✦ any other). A disabled portal is dashed. The track brightens while the pointer is on it.
- **Knob.** It rests at the centre. When it snaps, it leans toward the target: about 48% of the radius for an angled exit, 62% for a portal. With an aim but no target it leans weakly (30%) and stays unlit.
- **While walking.** During continuous movement the pad rim turns gold.
- **On a blocked move.** The pad shakes for about 260 ms, horizontally only.

### 3.3 Pointer

- **Aim.** Hovering the pad aims. Inside the dead zone (20% of the pad radius) there is no target. On the pad the aim snaps to angled exits; on the outer track it snaps to the nearest portal. Leaving the compass clears the aim and stops any walk.
- **Click.** A click moves once to the aimed target. A click with no target, or on a disabled target, shakes the pad and puts the reason in the readout.
- **Rapid clicks.** A click while a move is in flight queues at most one more step. On arrival, that step re-snaps the same aim angle in the new room.
- **Hold.** A press held for `HOLD_MS` on an angled target starts continuous movement (§3.5). Moving the cursor while holding steers. Releasing stops.

No drag is involved: the pointer never has to start at the knob.

### 3.4 Keyboard

The compass is one tab stop with `role="application"` and `aria-label="出口羅盤"`.

- **Arrow keys** set an eight-way aim. Two held arrows give the diagonal, and the aim snaps like the pointer. A tap only aims; it never moves.
- **`[` / `]`** cycle through every target, angled exits first and then portals (§3.1), so an exit crowded out of every arrow sector is still reachable.
- **Enter / Space** move to the aimed target. Key repeat is ignored.
- **Hold.** Holding an arrow or Enter for `HOLD_MS` starts continuous movement. Releasing every arrow and Enter stops it. Blur stops it too.

### 3.5 Continuous movement

- **Each step.** After each arrival (the next committed exploration panel), the compass waits at least `STEP_DWELL_MS` and then runs `nextStep(targets, aimAngle)`. That re-snaps the live aim against the new room's angled exits.
- **Stop conditions.** Movement stops with a shake and a readout reason when any of these happens:
  - no angled exit lies within ±30° (`這個方向沒有路了，停下腳步。`);
  - the snapped exit is disabled (its server reason);
  - the server rejects the move;
  - the frame leaves exploration (combat, dialogue, a drawer or card opens);
  - the input is released.
- **Portals never chain.** A portal only moves on a discrete click or Enter.
- **One move at a time.** The walk never sends a move while another is in flight. It is driven by commits, not timers alone.

### 3.6 Readout feed

The compass emits its aim to the shared readout (§5.3):

- Angled target: `前往 <octant glyph>` / destination name.
- Portal: `通道 ⇧|⇩|✦` / destination name.
- Disabled target: `無法通行` / server reason, in the warn tone.
- Aim with no target: `<glyph>` / `這個方向沒有出口`, in the quiet tone.

Destination names come from the committed local-map node label, falling back to the exit label, the same rule as today's `exitLabel`. The aimed node also lights on the minimap.

## 4. Presence Rail and Centred Verb Card

### 4.1 `PresenceRail.vue`

- **Placement.** The rail sits on the stage floor, right-aligned, inset left of the right-hand island column, with its baseline just above the band. It mirrors the player standee on the left. It shows only in exploration: it yields to `FoeLineup` in combat and hides during dialogue and while a centred card is open.
- **Entries.** In `ExplorationMenu.overviewMenu` order:
  1. Interact targets: a 64 px round gold medallion. With a `portrait_ref`, it shows the face crop through the existing face-rect data; without one, the name's first character in the display face.
  2. Present entities without an interact descriptor: a dashed muted medallion.
  3. A thin vertical separator, then objects as a steel lozenge.

  Each entry has a name plate below it.
- **Overflow.** At most six entries show. Beyond that, the sixth slot becomes `＋N`, which opens the centred card listing the rest (objects marked ◇).
- **Activation.**
  - An interact target opens the verb card (§4.3).
  - A bystander or an object submits its existing look payload directly.
  - `＋N` opens the overflow card. Picking a row there activates that entry as if it had been picked on the rail.
- **Hover and focus.** The medallion lifts and brightens, and the readout shows `<name>` / the affordance summary (`交談／公會服務`) or `查看`.
- **Motion.** Entries fade in and out as the panel changes.

### 4.2 `ChoiceCard.vue` (extracted)

Extract the presentational shell of `DialogueChoices.vue` into `ChoiceCard.vue`:

- the card frame, crest, and corner brackets;
- the digit-badged rows and the rule before a trailing row;
- the active-row fill and caret;
- the single-tab-stop keyboard composite: ArrowUp/Down wrap, Home/End, digits 1–N, Enter/Space, Escape, `aria-activedescendant`;
- the staggered entrance with its motion-level handling.

`DialogueChoices` keeps its view-model logic (picks, `⌨ 自由對話`, `↦ 移動…`, `✕ 結束對話`, the exits view) and renders through `ChoiceCard`, so the dialogue screen does not change visually.

New `ChoiceCard` consumers append a trailing `✕ 返回` row. Each one emits `pick(key)` and `back`:

- the verb card;
- the wait menu;
- the suggestions list;
- the presence overflow list.

### 4.3 Person focus flow

The focus state is client-local. It sends no server request and pushes no router frame; it replaces `DockVerbPopover`'s open/close state.

1. **Open.** The rail fades out. The command panel goes `inert` and dims to about 35% opacity. The place card and minimap step away, as in the dialogue screen.
2. **Standee.** The NPC standee slides in from the right into the `actor-right` anchor through `StageActor`. Without a portrait it uses the same silhouette, initial, and 無肖像 treatment as dialogue. The message window shows the NPC's name as the speaker line.
3. **Card.** The centred `ChoiceCard` lists `ExplorationMenu.verbMenuFor(target)` rows with digit badges, then `✕ 返回`. Today's `返回上一層` back row is rendered as this trailing row.
4. **Picks.**

   | Row | Result |
   | --- | --- |
   | 交談 | Enters the dialogue screen directly; the standee is already on stage, so the transition is continuous |
   | 交易 / 公會服務 | Opens its drawer, as today |
   | 戰鬥 | Submits `explore.engage` |
   | 查看 | Submits the look payload and closes the card |

5. **Close.** Escape or `✕ 返回` slides the standee out, brings the rail back, and returns focus to the medallion that opened the card.

## 5. Room Actions, Shared Readout, Focus Zones

### 5.1 Place card

`PlaceCard` stays display-first and gains two buttons:

- **查看房間** (magnifier icon, `aria-label="查看房間"`) beside the location heading. It submits the existing `look-room` payload.
- **等待** (hourglass icon plus label) beside the world time. It opens the centred `ChoiceCard` with the wait submenu rows: 等待直到黎明, 睡眠至完全恢復, and 休息 N 小時, which opens the existing `RestForm`. Then `✕ 返回`.
  - **Dream collaboration.** There is no separate dream row. Choosing 睡眠至完全恢復 opens a modal question, 進入夢境協作？, with 是 (sleep with the `dream` flag), 否 (plain sleep), and a ✕ at the top right that cancels the sleep and closes the question. The question comes before the single request because the server records the sleep's start tick and can only enter the dream as part of that same sleep.

The buttons are rendered only in exploration and while the exploration panel is available.

### 5.2 Command panel (exploration)

- The panel keeps its 1/3 width, so the message window never jumps between modes.
- The compass fills the panel height on the left. The right column holds the 建議 N pill (top right, hidden while suggestions are `unavailable`; it opens the suggestions `ChoiceCard`, whose 清除建議 row sits above `✕ 返回` and carries a trash-can icon so it is not mistaken for the back row) and the shared readout at the bottom.
- The panel shows no key hints.

### 5.3 Shared readout

The readout is the exploration screen's single explanation line: `aria-live="polite"`, a gold left rule, a small lead line and a 1–2 line text. Its content, by priority:

1. A transient flash for a blocked move (warn tone, about 1.6 s).
2. Whatever is aimed or hovered:
   - the compass aim (§3.6);
   - a rail entry (§4.1);
   - a place-card button (`查看房間` / `重新觀察四周`, `等待` / `讓時間流逝、休息或睡眠`);
   - the 建議 pill.
3. The idle summary `出口 N · 在場 M`, in the quiet tone.

The readout replaces `exploration-detail` as the place where server-authored disabled reasons appear.

### 5.4 Focus zones and the keyboard router

- Entering exploration focuses the compass.
- Tab order: compass → presence rail → place-card actions → 建議. Each zone is one composite with one tab stop and a visible focus ring.
- In the presence rail, ←/→ move and Enter activates. While no card is open, digits 1–9 activate the Nth visible rail entry from anywhere in the exploration screen. While a card is open, the card owns the digits.
- A centred card traps focus and returns it to its opener on close.
- **Router.** The exploration root frame changes from the `overviewMenu` sections listbox to the compass model. The rail and the place-card actions own their rows outside the router, like the top navigation bar's `navigationItems`. Remove `geometry: "sections"` from `KeyboardRouter` if nothing else uses it after the swap.
- `lib/controls-reference.js` gains the compass, rail, and card bindings so the help overlay documents them.

## 6. Components and Files

| File | Change |
| --- | --- |
| `web/webclient-app/components/compass-model.js` | New. Pure model from §3.1 and §3.5 |
| `web/webclient-app/components/ExitCompass.vue` | New. §3.2–3.6 |
| `web/webclient-app/components/PresenceRail.vue` | New. §4.1 |
| `web/webclient-app/components/ChoiceCard.vue` | New. Extracted from `DialogueChoices.vue` (§4.2) |
| `web/webclient-app/components/DialogueChoices.vue` | Renders through `ChoiceCard`; behavior unchanged |
| `web/webclient-app/components/PlaceCard.vue` | Two room-action buttons (§5.1) |
| `web/webclient-app/components/ActionDock.vue`, `dock-panes.js` | Exploration root pane hosts `ExitCompass`, the 建議 pill, and the readout |
| `web/webclient-app/AppClient.vue` | Mounts `PresenceRail`, the person-focus standee, and the centred card host; wires the focus state |
| `web/static/webclient/js/elosern/exploration_menu.js` | Keeps item and payload builders; `overviewMenu` drops its `geometry: "sections"` once the router no longer needs it |
| `web/static/webclient/js/elosern/keyboard_router.js` | Exploration root uses the compass; `sections` geometry removed if unused |
| `web/webclient-app/lib/controls-reference.js` | New bindings (§5.4) |
| `web/webclient-app/components/SceneOverview.vue`, `DockVerbPopover.vue` and their stories | Removed |
| `web/webclient-app/styles/app-shell.css` | Remove `.elosern-root` duplicates for the removed and restyled classes |
| `web/webclient-app/component-manifest.json` | Register the new components and stories; drop the removed ones |

## 7. Error and Absence Handling

- **No local map committed.** The exits still resolve, but only by direction word, and the rest become portals. `moveItems` already disables every exit while `current_node` is missing, so each pip or bead shows as disabled with `地圖資料尚未同步。`.
- **No exits.** The pad renders empty with no portal track, and the readout idles at `出口 0 · 在場 M`. Any click shakes.
- **No people or objects.** The rail renders nothing; no empty placeholder.
- **Exploration panel unavailable.** The compass, rail, and place-card buttons are not rendered. The panel keeps its existing degraded root.
- **Move rejected while walking.** The walk stops with the rejection's message in the readout.
- **Panel changes while a card is open.** If the focused person leaves (no longer in `interact`), the card closes, the standee leaves, and the readout flashes `<name> 已經離開了。`.

## 8. Testing

- **Unit (vitest), `compass-model.js`:**
  - each of the three angle sources, including a cross-layer exit and same-coordinate stairs;
  - the ±30° snap and its tie rule;
  - the dead zone and the ring zone;
  - portal slot assignment: pinned up and down, even spread, the 24-slot switch;
  - the cycle order;
  - `aimFromKeys` for all eight directions and for cancelling keys;
  - every `nextStep` stop reason.
- **Component tests:**
  - `ExitCompass`: click, hold, rapid-click queue, keyboard aim and cycle, and blur stopping a walk.
  - `PresenceRail`: overflow, the portrait fallback, bystander and object activation.
  - `ChoiceCard`: keys, digits, trailing back row.
  - `DialogueChoices`: existing tests unchanged and green.
  - `PlaceCard`: the buttons emit the right intents.
- **Storybook,** bound to real reducer-derived shapes through fixtures:

  | Component | Stories |
  | --- | --- |
  | `ExitCompass` | Wilderness8Way, GridIrregular, InteriorPortals, Stairs, DisabledExit, TenPortals, Walking (interactive) |
  | `PresenceRail` | Default, Overflow, NoPortraits, ObjectsOnly |
  | `ChoiceCard` | Verbs, Wait, Suggestions, Overflow |
  | Full exploration screen | One story |

- **Live client:** agent-browser screenshots at 1451×790 and 1920×1080 of each exploration state, plus a hold-to-walk run in the wilderness. Per AGENTS.md, check the geometry there, not only in Storybook.

## 9. Non-Goals

- The dialogue screen's `↦ 移動…` exits list keeps its current list form.
- No click-to-travel pathfinding on the minimap.
- No server or protocol changes. Every input already exists in the committed exploration and local-map panels.
- No change to combat, the skill dock, or the top navigation bar.
- No touch or controller-stick input. The design stays desktop pointer plus keyboard.

## 10. OpenSpec Changes and Order

The work is three changes, applied and archived strictly in order. Each one leaves the client fully working.

1. **`exploration-exit-compass`.** Add `compass-model.js` and `ExitCompass.vue` with the readout line, and host them in the exploration root pane in place of `SceneOverview`'s 出口 row. The 人物 / 物件 / footer rows stay temporarily below the compass in the right column. Also covers continuous movement, the router root change, and the controls reference for the compass.
2. **`exploration-presence-rail`.** Extract `ChoiceCard.vue` and move `DialogueChoices` onto it. Add `PresenceRail.vue`, the person-focus standee, and the centred verb card. Remove the 人物 / 物件 rows and `DockVerbPopover.vue`.
3. **`exploration-room-actions`.** Add the place-card buttons, the wait and suggestions cards, the 建議 pill, and the readout's final priority rules. Remove the footer row and `SceneOverview.vue` itself, the `sections` geometry if unused, and the `app-shell.css` duplicates. Update the help overlay's reference and the component manifest.

**Conflicts.** Change 2 and change 3 both touch the exploration pane in `ActionDock.vue` and `AppClient.vue`, so they must not run in parallel.
