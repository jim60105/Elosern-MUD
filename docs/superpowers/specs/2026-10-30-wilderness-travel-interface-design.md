# Wilderness Travel-Mode Interface

**Date:** 2026-10-30
**Status:** Design approved through the blueprint and the Storybook prototype on 2026-10-30. Written-spec review pending.
**Implementation status:** Not implemented by this document.
**Scope:** Sub-project 2 of the [wilderness travel mode blueprint](2026-10-30-wilderness-travel-mode-blueprint-design.md). It defines the browser travel layout (layout A), its components, the movement inputs and walking queue, the travel log, and the settlement transitions. It consumes the protocol defined in [Wilderness Sight and Fog Reveal](2026-10-30-wilderness-sight-and-fog-reveal-design.md).
**Proposals:** Eight OpenSpec changes, listed with their dependency order and implementation batches in section 15.

The approved visual reference is the prototype in `docs/design/wilderness-travel/` (Storybook `Design/WildernessTravel`). Where this spec and the prototype differ, this spec wins. The prototype's mock rules (`travel-model.js`) are not production code.

## 1. Goal and boundaries

While the party stands on a wilderness cell, the browser shows a full-bleed ink map instead of the AVG stage. The player plans and walks the day's leg on that map, reads one log line per noteworthy event, and sees how far the party can still walk.

Out of scope: the text client (unchanged), the camp card and campfire beat (sub-project 3), the rules and protocol of sight and reveal (sub-project 1), the dialogue and combat layouts (unchanged), and new art.

## 2. Mode selection

- The server mode stays `exploration`. The client derives `travelMode` from the committed room: true when `room.subject_id` starts with `wilderness:` and the mode is `exploration`.
- Entering or leaving travel mode crossfades the stage over `--motion-scene`. At motion level `off`, the switch lands in the commit's frame.
- Dialogue and combat that start in the wilderness use their existing layouts, with the region's scene art as the backdrop. When they end, the travel layout returns.

## 3. Layout

The travel layout uses the existing `HudFrame` slots:

| Slot | Travel component | Notes |
| --- | --- | --- |
| `backdrop` | `TravelMap` | Full-bleed map; replaces `SceneBackdrop` |
| `vitals` | `PartyMedallions` | Replaces `CompanionLineup`; the vitals island keeps its existing place above it |
| `map` | `PlaceCard` | Unchanged; the location label is `<district>・<terrain>` and the time label carries the light phase |
| `presence` | `PresenceRail` | Unchanged; same-cell figures only |
| `choices` | Event cards | Landmark arrival, and the camp and campfire cards from sub-project 3; may span the open stage height above the band |
| `band-message` | `TravelLog` | Replaces the per-step narration in `MessageWindow` |
| `band-command` | `LegPanel` | Replaces the movement parts of `ExitCompass` and `ActionDock` |

`MapDrawer` hides its area tab in travel mode; the world tab is unchanged. The `actor-left` and `actor-right` anchors stay empty in travel mode. The stage vignette is lighter than the AVG default so the map edges stay legible.

New components live in `web/webclient-app/components/travel/`.

## 4. `TravelMap`

### 4.1 Inputs

`TravelMap` reads only the committed store:

- The wilderness `area_map` window: cells as decoded runs, live-sight entities, distant-sighting markers, the light phase, and the current ground radius.
- The party cell.
- The current `travel.plan` result, if any.
- The walking state (section 6).

It never derives reveal, passability, durations, or stages.

### 4.2 Painting

Painting happens once per state change, on a canvas sized to the window:

1. **Terrain field.** A fixed number of samples per cell. Elevation comes from bilinear interpolation of the per-cell band, plus a cosmetic, deterministic client-side noise for texture. Hillshade uses light from the north-west. Contours are drawn at band changes, with every third band darker. The terrain colour comes from a warped lookup, so region borders do not follow the cell grid. Colours: umber ground, ochre hills, moss woods, slate water on a dark ink base.
2. **Reveal mask.** Revealed coverage is bilinear over the cells, with a deterministic jitter that gives a brushed edge, and the edge pools darker. Unrevealed areas are transparent, so the map root's hatched ink is one fog surface inside and outside the window.
3. **Ink strokes.** These are clipped to the reveal mask:
   - Rivers and roads are smoothed polylines built by connecting the centres of adjacent flagged cells with Chaikin smoothing. Rivers have a bank wash, a water body, and a current line; roads have a dark underlay and a gold dash.
   - Woods are three jittered conifer dabs per cell.
   - The ford shows stepping stones.
   - Summits are concentric rings, one per prominence tier, drawn only on local maxima of prominence.
   - District edges are dotted.
   - Settlement walls are drawn at their footprint edge.
   - A faint cell grid appears only within live sight.
4. **Light.** These passes paint only over painted pixels (source-atop):
   - Outside live sight, colour drains and the map dims (memory).
   - The phase wash: none by day, violet at dawn, amber at dusk, deep blue at night.
   - At night, a faint moonlit disc around the party.

Starting values for the phase look, to tune in implementation:

| Phase | Wash | Memory dim | Desaturation |
| --- | --- | --- | --- |
| day | none | 0.20 | 0.40 |
| dawn | `rgba(120,110,170,0.16)` | 0.32 | 0.50 |
| dusk | `rgba(196,112,48,0.18)` | 0.36 | 0.50 |
| night | `rgba(20,34,78,0.36)` | 0.42 | 0.75 |

Budget: one repaint takes at most 50 ms at 1451×790 and 2560×1440 on the development machine. Camera moves never repaint.

### 4.3 Overlay

An SVG layer above the canvas draws:

- the live-sight ring (dashed);
- the party token, a seal-red disc with a gold rim and a breathing halo that stops at motion `off`;
- eight neighbour nodes around the token. The aimed node is filled and its cell highlighted. A blocked node is dashed and hollow;
- the route preview: one mark per step, shaped and coloured by predicted stage (gold disc for normal, amber diamond for light, rust ring for moderate and severe). Steps after `stop_index` are faint outlines, and steps after nightfall are dimmed. A moon mark sits on the nightfall step and a camp mark on the stop step. The destination is outlined;
- landmarks as the band ornament's diamond;
- hostiles in live sight as seal tokens with a soft halo;
- bearing rays for distant sightings;
- a hover outline (dashed on unrevealed cells).

HTML chips, for crisp text, give:

- landmark names, above the diamond;
- the hostile name, count and threat;
- the ford label;
- the aim readout (`方位・地形`, or `方位・阻擋原因`);
- the hover label (terrain or landmark name, or 未探明);
- distant-sighting cards (`方位・約 N 公里` over the silhouette). These are projected from the open-stage centre onto its edge, so they never sit under the band, the place card, or the medallions.

A north mark and a 5 km scale bar sit at the top-left of the open stage.

### 4.4 Camera and zoom

- The camera follows the party cell, centred in the open stage between the header and the band. Moves glide over 380 ms × `--motion-travel`.
- A locked route frames the bounding box of the party, the route, and the destination inside the open stage, between the medallion and place-card columns, shrinking the cell size if needed (minimum 14 px × `--ui-scale`). Walking returns to following.
- Zoom has cell sizes from 18 to 46 px × `--ui-scale` in steps of 4. The mouse wheel and `+` / `-` change it. The default is 30.

## 5. Inputs

The map is one focus stop (`role="application"`, with an `aria-label` that states the controls). Keyboard and pointer reach every action. Every input has a visible state in the aim chip or the leg panel.

| Input | Keyboard | Pointer |
| --- | --- | --- |
| Aim a neighbour | Arrow keys; two arrows aim a diagonal. The aim stays after release. | Hover a neighbour cell |
| Step once | Enter with an aim | Click a neighbour cell |
| Walk while held | Hold arrows for 400 ms; release stops | — |
| Preview a route | — | Hover a revealed, non-adjacent cell |
| Lock a route | — | Click a revealed cell |
| Depart on the locked route | Enter (no aim), or 出發 | Click the locked cell again, or 出發 |
| Stop walking | Any key | 停步 |
| Clear aim or route | Esc | — |
| Zoom | `+` / `-` | Wheel |

Clicking the party's own cell does nothing. A click on an unrevealed cell does nothing beyond the hover outline.

Hovering or locking sends `travel.plan` with the destination, the pace, and `stop_at_night`. Hover requests are debounced (150 ms), and a newer request supersedes an older one. Results apply only while their request is current.

## 6. Walking

The walking state lives in the store. It holds the departed plan, the progress (steps committed), and the walk kind (`route` or a direction).

- **Route walk:**
  - On departure, the client keeps the plan as returned and queues its steps up to `stop_index`.
  - It sends one `explore.move` with `walk: {pace, stop_at_night}`, waits for that step's commit, then waits `STEP_DWELL_MS` (350 ms, 0 at motion `off`) before sending the next step.
  - The queue stops on any of these: an interrupt flag in the step result, a refusal, a disconnect or presentation-epoch change, any key press, 停步, or the end of the queue.
- **Held walk:** Steps in the held direction repeat with the same rules until release, a block, or an interrupt flag.
- **During a walk:**
  - The map shows the remaining steps of the departed plan.
  - The leg panel shows the departed plan with walked ticks spent.
  - Neighbour nodes and hover are hidden.
- **After a stop:**
  - Focus returns to the map unless an event card opened.
  - A walk stopped short of its destination keeps the destination locked, so a new `travel.plan` comes from the new position.

## 7. `LegPanel`

From top to bottom:

1. **Intent line.** One of:
   - 點選已探明的格子規劃路線
   - 瞄準<方位>・一步, with the step's minutes, or 無法通行
   - 前往<目的地>, with steps, duration, and stop time
   - 已到今天的節制門檻 / 建議紮營
   - 夜裡只看得見身邊 / 建議紮營到天亮 (night with the nightfall stop on)
   - 前往<目的地> / 行進中・任意鍵停步 while walking
2. **Leg gauge.** One tick per step:
   - With a plan, ticks follow the plan's predicted stages. A moon sits on nightfall, and a camp line at the stop.
   - Without a plan, the gauge shows the party's remaining capacity by stage on the current terrain, with the pace stop marked. The server supplies capacity as a per-stage cell count on the status payload.
   - Ticks differ by height as well as colour.
3. **Legend.** Per-stage counts and the stop reason (依節制在此紮營, 入夜即停, 精力不足以再走, 抵達目的地).
4. **Controls.**
   - Pace is a radio group: 保守, 標準, 強行.
   - 入夜停步 is a switch.
   - Both are client view preferences, persisted with the existing view settings. They are disabled while walking.
5. **Actions.**
   - 出發 (disabled without a locked plan), which becomes 停步 while walking.
   - 紮營 opens the camp card (sub-project 3).
   - 環顧 requests the current cell's full scenery prose into the travel log.

## 8. `PartyMedallions`

Each present member is shown as a round face crop with:

- the name;
- a 精力 bar with notches at 70, 40, and 20 %;
- the stage name when not 精神充沛;
- a crescent while asleep.

The controlled member is ringed. Stages also lower saturation and brightness, so colour is never the only cue. The accessible name is `<名字>：精力 N%（<階段>）`.

## 9. `TravelLog` and travel log events

- **Rendering.** The band's message region shows log entries grouped under day headings, newest at the bottom, in an `aria-live="polite"` region. Each entry has a time, a glyph per kind (◆ landmark, ▲ hostile, ◐ fatigue, ☾ night, ⛺ camp, ≈ ford, · plain), and one line of zh-TW text. The glyph keeps kinds distinguishable without colour. The full log overlay stays available.
- **Source.** The server emits structured travel log events with each committed wilderness step, time skip, and look. The client never infers importance from prose. The event kinds are:

  | Kind | Raised when |
  | --- | --- |
  | `region_entered` | The party enters a region |
  | `woodland_entered` | The party enters woodland |
  | `ford_crossed` | The party crosses a ford |
  | `hostile_sighted` | A hostile is sighted |
  | `landmark_sighted` | A landmark is sighted |
  | `landmark_reached` | The party reaches a landmark (carries the lit district, if any) |
  | `fatigue_stage` | A member's fatigue stage changes |
  | `dusk` | Dusk begins |
  | `nightfall` | Night begins |
  | `camp_result` | A camp ends (sub-project 3) |
  | `look` | The player looks around |

  Events carry the parameters their text needs; the server renders the text.
- **Per-step narration.** The ordinary per-step room narration is not shown in travel mode. It remains in the full log.

## 10. Landmark card

Arriving on a landmark (`landmark_reached`) opens a card in the `choices` anchor, with:

- the landmark's scene art in a 16:6 frame;
- 抵達地標;
- the name;
- `◆ <district>已探明` when this arrival lit it;
- the landmark prose;
- 繼續 (Enter or Esc).

The card takes focus and returns it to the map when it closes.

## 11. Accessibility and motion

- All text is at least 16 px × `--ui-scale`. Focus rings are visible on every control and on the map (an inset frame).
- Stages, hostiles, landmarks, and log kinds use shape or glyph as well as colour.
- Motion `off` removes the camera glide, token breathing, and step dwell, and lands every transition in its commit's frame.
- The travel log is the screen-reader channel for walking. The leg panel's intent line is the channel for aim and plan.

## 12. Errors

- `travel.plan` error codes show in the intent line (for example 目的地尚未探明, 無法抵達, 路線超過 60 步) and clear the preview.
- A step refusal stops the queue and shows the refusal in the intent line and the log.
- A stale or unreadable `area_map` window shows the last committed map dimmed, with the leg panel disabled, until the next snapshot.

## 13. Testing

- **vitest:**
  - The run-length window decoder.
  - The walking queue: it sends the next step only after a commit, and stops on each interrupt flag, a refusal, a key press, a disconnect, and an epoch change.
  - The input mapping (aim persistence, diagonal aims, a held walk, Enter with and without an aim, Esc).
  - The intent line for each state.
  - The capacity gauge.
  - Debounced and superseded plan requests.
- **Storybook:** Stories move from the prototype to the production components (Morning, Route Preview, Dusk, Night, Woodland, Landmark Arrival, Motion Off), driven by fixture payloads in the protocol's shape.
- **Browser tests:**
  - Entering and leaving travel mode at a settlement gate.
  - A route walk interrupted by `hostile_in_sight`.
  - Keyboard-only stepping.
  - Screenshots at 1451×790 and 2560×1440.
- **Performance:** the repaint budget in section 4.2.

## 14. Dependencies

The layout, medallions, travel log, neighbour stepping, and held walking can ship before sub-project 1 through an adapter that turns today's node-form 15 × 15 `area_map` into the same decoded cell grid the run-length window produces. The destination input, route preview, distant sightings, and interrupt flags need sub-project 1.

## 15. Proposal set and implementation batches

Sub-project 2 is proposed as eight changes, each one engineer-day of runnable vertical behaviour. They live under `openspec/changes/<name>/` and are proposal-only until applied.

| Order | Change | Scope | Direct prerequisites | Existing active prerequisites | Frontend visual |
| --- | --- | --- | --- | --- | --- |
| 1 | `wilderness-travel-interface` | Mode selection, `HudFrame` slot remapping, `MapDrawer` area-tab hiding, live map refresh, temporary adapter, `PartyMedallions` | none | none | yes — slot remap and `PartyMedallions.vue` |
| 2 | `wilderness-travel-map-ui` | Canvas painting pipeline, shared glyph states, overlays, measured camera and zoom, repaint-budget evidence | 1 | none | yes — canvas painter, SVG/HTML overlays, camera and zoom |
| 3 | `wilderness-travel-walking-ui` | Persistent neighbour aim, keyboard and pointer stepping, store-owned commit/dwell held walking | 1 | none | no — input and queue behaviour; only the temporary `TravelWalkControls` surface is visible and change 5 deletes it |
| 4 | `wilderness-travel-log-ui` | Commit-qualified structured server notices, causal publication delivery, `TravelLog`, refusal handling | 1 | none | yes — `TravelLog.vue` band log and full-log hand-off |
| 5 | `wilderness-travel-leg-ui` | Server-authored capacity and quotes, persisted pace and nightfall preferences, leg gauge, guarded actions | 3, 4 | none | yes — `LegPanel.vue` intent line, gauge, legend, controls |
| 6 | `wilderness-travel-window-ui` | Shared run-length decoder cutover, disclosed annotations, authoritative sight and phase presentation, notice capture | 2, 4 | `wilderness-area-map-reveal` | partly — no new visible component; changes what the painted map and chips show from supplied facts |
| 7 | `wilderness-travel-planning-ui` | Accessible destination selection, debounced current-only `travel.plan` queries, route previews | 5, 6 | `wilderness-travel-planning` | yes — destination cursor and route preview overlay |
| 8 | `wilderness-travel-route-ui` | Guarded route execution, every supplied interrupt, short-stop replanning, landmark card focus | 7 | `wilderness-travel-interrupts` | yes — `LandmarkCard.vue` arrival card and focus hand-off |

The visual column drives evidence, not scope: a `yes` or `partly` change carries the Storybook story and the 1451×790 / 2560×1440 screenshot review named in its `tasks.md`, and its appearance and copy are human-reviewed against the prototype. A `no` change is verified by behavioural Vitest and browser assertions only.

### 15.1 Parallel implementation batches

The order above is a safe serialized sequence, not eight build edges. Batches below run concurrently; each one has a single integration owner for the shared `AppClient`, travel store, status schema, protocol audits, and test manifests, because those files are the only hard serialization surface.

| Batch | Changes | Visual? | Can run in parallel because | Serialized inside the batch |
| --- | --- | --- | --- | --- |
| A | 1 | yes | Root change; everything else depends on its slot remapping and store projection | — |
| B | 2, 3, 4 | 2 and 4 yes, 3 no | All three need only batch A; map painting, input/queue, and log publication touch different components | `AppClient`, travel store, `docs/game` protocol notes, shard manifests |
| C | 5, 6 | 5 yes, 6 partly | Both need batch B; 5 is client-only capacity and preferences, 6 is the decoder and sight presentation | Shared decoder extraction, `area_map` schema versus status schema ordering |
| D | 7 | yes | Needs 5 for preferences and 6 for the window, plus sub-project 1's `wilderness-travel-planning` | — |
| E | 8 | yes | Needs 7 for the queue and sub-project 1's `wilderness-travel-interrupts` | — |

Changes 1 to 5 follow the adapter path and are implementable before sub-project 1 lands. Changes 6 to 8 wait on the named sub-project 1 changes; no change in this set re-specifies server sight, reveal, routing, or interrupt rules.
