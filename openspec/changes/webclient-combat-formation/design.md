# Design: Shared-scale combat formation with glance plates

Builds on `webclient-combat-formation-engine`. Its design holds the measured inputs, the party cap (1–5 figures), the
foe maximum (15) and the reference table.

## Context

- `CompanionLineup.vue` lays the party out as an overlapping row inside `actor-left`. `FoeLineup.vue` depth-stages at
  most three foes inside `actor-right` and draws a floor name plate and gauge per foe.
- `ParticipantFrame.vue` (story `Data/ParticipantFrame`) sits in the `map` anchor under the place card in combat. It
  is the only surface with numeric HP for foes and companions. The vitals dock (`StatusPanel`) holds the player's.
- `StageActor.vue` renders a figure at 100% of its slot height; the slot's box defines the drawn size.
- `tmp/core-panel-design-notes.md` is the reference for HUD panels: no boxes, feathered ground, brass hairlines,
  thin tapered strokes, one tabular readout, glyph plus accessible name, tooltip on demand.

## Decisions

### D1. Applying the engine

- AppClient computes `formation` while the stage mode is combat (including the held round). It calls
  `formationInputFromStage` on the stage box, the computed tokens and the vitals dock box, with the displayed party
  count and the active foe count (`beatStage.foes` while a round plays).
- A `ResizeObserver` on the stage and the vitals dock recomputes in the next animation frame.
- In combat, HudFrame sets `inset: 0` on `actor-left` and `actor-right`, so slot coordinates are stage coordinates.
  Each line-up receives `formation.party` / `formation.foes` and renders its slots with `left/top/width/height` in px.
- Outside combat the prop is `null` and today's CSS layout applies unchanged, which is what keeps exploration and
  dialogue identical.

### D2. The map anchor in combat

`[data-elosern-mode="combat"] [data-anchor="map"] { display: none; }`. The participant frame component is deleted
and the place card is hidden. Evidence: with the place card kept, the prototype found no valid formation for 11 or
more foes at any viewport except 2560x1440, and single foes dropped to 0.72–0.78 because their plates hit the card.

Decision-first argument: in a fight, the location name and the world time change no decision. The scene caption and
the log still carry the place.

### D3. Shared scale through motion

- Every slot transitions `left, top, width, height` on `calc(var(--motion-actor) * var(--motion-travel))` with
  `var(--ease-standard)`, set on both line-ups by one class, and the formation object changes in one Vue tick.
  Both sides therefore start, move and end together, and their heights are equal in every frame.
- Joining and leaving foes use the existing fade (`foe-enter`/`foe-leave`) at the formation scale.
- At `reduced` and `off` the slot transition is `none`.
- Entry into combat:
  - party slots move from their exploration boxes, which AppClient captures before the commit's render, to the
    formation;
  - foes keep the "enters as the flash releases" timing.
- Exit is the reverse.
- On reconnect or mount, the transition is not applied (the existing `modeHydrating` flag).

### D4. FigurePlate (glance)

- **Layout:** `components/FigurePlate.vue` takes `name`, `side`, `hpCurrent`, `hpMaximum`, `form` (`full`/`compact`) and
  `slot` (its box). It is positioned absolutely in the HudFrame `plates` layer (`z` between the portrait anchors and
  the islands; `pointer-events: none` in this change).
  - Full: `--text-sm` serif name, then one row: the 4px stroke (flex) and the readout.
  - Compact: the stroke and the current value only.
- **Stroke:** a 4px·S line with `clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%)`.
  - Allies use the vitals HP hue; foes the existing foe gauge red gradient.
  - A trailing segment uses the vitals trail tokens.
  - Empty ground is a paper wash.
- **Readout:** `--f-mono` 600 `tabular-nums lining-nums`; the current value in `--paper-50`, `/ max` in `--paper-500`
  at a smaller size; a 1px dark text shadow.
- **Chrome:** a `::before` ground of `var(--panel)` plus the backdrop blur, masked to fade upward and to the sides (the
  plate is anchored at its bottom, on the figure's head); an `::after` brass crown hairline along the bottom edge
  (`--band-edge` → `--band-edge-dim` → transparent). There is no border, radius, shadow or lozenge.
- **Accessibility:** the plate is `role="group"` with `aria-label` "<name>，<我方|敵方>，生命 <cur>/<max>" plus the session
  token. The visible name is `aria-hidden` when compact.
- **Motion:** the plate appears with its figure's motion (fade, rising out of its anchored bottom edge at `full`),
  with tokens only.
- **Removed:** the floor `foe-lineup__name`/`foe-lineup__gauge` (and the `foe-gauge` test id).

### D5. Test-id migration (explicit)

| Removed | Replacement | Tests to change |
|---|---|---|
| `participant-frame` and its rows | `figure-plate` (`data-identity`, `data-side`, `data-form`), `figure-plate-stroke`, `figure-plate-readout` | `tests/core/participant_frame.test.js` and `tests/combat/participant_frame.test.js` deleted; `tests/overlays/deferred_surfaces_absent.test.js` updated; browser methods found by `grep -rln "participant-frame\|participant_frame\|foe-gauge" web/tests/browser` |
| `foe-gauge`, `.foe-lineup__name` | the foe's `figure-plate` | `tests/core/foe_lineup.test.js` |

### D6. Storybook

- Remove `Data/ParticipantFrame` and add `Core/FigurePlate` (full, compact, damaged, long name, foe vs ally) in
  `component-manifest.json`.
- `Core/AppShell` gains the matrix corners at both viewports' widths: `CombatSoloOneFoe`, `CombatSoloFifteenFoes`,
  `CombatThreeFigures(…)FiveFoes`, `CombatFullPartyOneFoe`, `CombatFullPartyEightFoes` and `CombatFullPartyElevenFoes`
  (the participant cap), plus `CombatEnterJourney` (exploration → combat at full) and `CombatReducedMotion`.
- `Core/FoeLineup` and `Core/CompanionLineup` gain `Formation` stories.

## Risks / Trade-offs

- [The place card disappears in combat] → it is a deliberate decision-first trade, the only one that fits the
  formation; it returns at once on leaving combat.
- [A ResizeObserver plus inline px positions vs CSS] → one pure function drives both sides, so no second copy of the
  geometry exists in CSS. The source-level two-copies test the notes call for is therefore not needed. The plates
  layer and the anchors read only the engine's numbers.
- [Many browser tests read `participant-frame`] → listed by grep in the tasks; each is migrated, never deleted
  without its replacement assertion.
- [Interim between this change and `webclient-combat-figure-plates`] → plates show no conditions; archive the two
  back to back.

## Migration Plan

Pre-release client. Rollback is reverting the commits.

## Open Questions

None.
