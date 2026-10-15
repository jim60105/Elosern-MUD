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

### D2. The map anchor in combat (and the place card requirement)

`[data-elosern-mode="combat"] [data-anchor="map"] { display: none; }`. The participant frame component is deleted
and the place card is hidden. Evidence: with the place card kept, the prototype found no valid formation for 11 or
more foes at any viewport except 2560x1440, and single foes dropped to 0.72–0.78 because their plates hit the card.

The place card requirement is amended to "exploration only" with an absent-in-combat scenario, and the matrix's
consistency scenario now says "shown in exploration, hidden in combat, dialogue and creation".

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
  - Full (112×52px·S): line 1 the `--text-sm` serif name (with the session token after it only while two drawn
    participants share the name); line 2 the 4px stroke (flex, ≥ 40px·S) and the readout; line 3 reserved for the
    condition glyphs of `webclient-combat-figure-plates`.
  - Compact (72×36px·S): line 1 the stroke (≥ 30px·S) and the current value; line 2 reserved for one glyph.
- **Stroke:** a 4px·S line with `clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%)`.
  - Allies use the vitals HP hue; foes the existing foe gauge red gradient.
  - A trailing segment uses the vitals trail tokens.
  - Empty ground is a paper wash.
- **Readout:** `--f-num` 600 `tabular-nums lining-nums` (amended at apply time from `--f-mono`: the chrome-type
  contract reserves the monospace role for command input, keycaps, badges and map art, and gauge values use the
  numeral role, as the vitals readout does); the current value in `--paper-50`, `/ max` in `--paper-500`
  at a smaller size; a 1px dark text shadow.
- **Chrome:** a `::before` ground of `var(--panel)` plus the backdrop blur, masked to fade upward and to the sides (the
  plate is anchored at its bottom, on the figure's head); an `::after` brass crown hairline along the bottom edge
  (`--band-edge` → `--band-edge-dim` → transparent). There is no border, radius, shadow or lozenge.
- **Accessibility:** the plate is `role="group"` with `aria-label` "<name>，<我方|敵方>，生命 <cur>/<max>" plus the session
  token. The visible name is `aria-hidden` when compact.
- **Motion:** the plate appears with its figure's motion (fade, rising out of its anchored bottom edge at `full`),
  with tokens only.
- **Removed:** the floor `foe-lineup__name`/`foe-lineup__gauge` (and the `foe-gauge` test id).

### D4b. Beat lunges stay out of the card

The beat step toward the centre shrinks from 24px to `12px·S`, so a lunging figure stays inside its 16px·S gutter and
never enters the card's columns, even for its 240ms gesture (the beats requirement is amended).

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

### D7. Heads are never covered; plates are never covered (user decision at apply time)

The user ruled: no standing figure's head — front rank or back rank — may ever be covered, by a plate, a target
marker or another figure; lower bodies may be covered; nothing may cover a plate. The engine
(`components/combat-formation.js`, archived with `webclient-combat-formation-engine`) is amended in this change:

- **Head proxy.** A head is the central 30% of a figure box's width and its top 22% (`HEAD_WIDTH`, `HEAD_HEIGHT`).
  Measured on the shipped standing art, a head with its hair spans about 15–18% of the box's width and the top
  16–17% of its height, so the proxy is conservative. A per-figure head from the committed face rectangle would
  need the art in the engine's input; the proxy keeps the engine pure.
- **New fit conditions.** No plate or marker slot overlaps any head; a front-rank box never overlaps a back-rank
  head; no two heads of one rank overlap (the step is at least 30% of the figure width).
- **Plate placement.** In the front rank of a two-rank side, a plate above the head would lie across the back
  rank's faces (no half-step offset can clear them: the 112px·S plate is wider than the back figures' offset
  allows). Those plates stand on the side's floor line instead, over their own figures' lower bodies: the lowest
  line's bottom 8px·S above the command-line row (a new optional input, `--command-line-h`, 44px·S by default) and,
  for the party, 8px·S above the vitals dock. A second plate line stands above the first. Back-rank plates stay above
  their heads.
- **Beat steps.** A figure acting in a round leans up to 12px·S toward the centre; the engine returns each figure's
  `lunge`, cut to the clear space before the next head of its rank, and the line-ups set it on the slot as
  `--motion-beat-lunge`, so no head reaches another at the step's peak. (Widening the head spacing by the full
  12px·S instead would leave 13–15 foes with no fitting layout at 1451x790–1920x1080.)
- **Scope of "ever".** The rule holds for every resting layout and at the beat step's peak. A glide between two
  layouts (entering or leaving combat, a re-formed line) and a foe fading where it stood are transitions between two
  compliant layouts and are not separately constrained.
- **The plate's ground** stays inside its slot's height (it only feathers out sideways), so the drawn plate is no
  taller than the slot the engine checks.
- **Plates are never covered.** The plates layer paints above every figure (z 3 over the portrait anchors' z 2), and
  plate slots avoid the vitals dock, the command-line row, the band and the top band.

Normative anchors that move (before → after, scale + foe slot form + foe ranks; party sizes 1–5):

- 1451x790: six foes 0.72F1 → 0.66F1 for every party size; fifteen foes beside a solo player 0.55C2 → 0.50C2.
- 1600x900 and 1920x1080: five foes 0.78F1 → 0.72F1 (parties 1–5); six foes 0.78F1 → 0.66F1; seven foes 0.60F1 →
  0.55F1; a five-figure party against one to four foes 0.78F1 → 0.72F1; fifteen foes 0.55C2 → 0.50C2.
- 2560x1440: five foes 0.84F1 → 0.78F1; six 0.84F1 → 0.66F1; seven 0.84F1 → 0.66F2; eight 0.78F1 → 0.66F2; nine
  0.66F1 → 0.55F2 (parties 1–5); a five-figure party against one to four foes 0.84F1 → 0.78F1; fifteen foes
  0.55F2 → 0.50F2.

The spec's anchor scenario changes accordingly: five party figures against one to five foes stay 0.72 and against
six become 0.66; fifteen foes beside a solo player become 0.50 compact (was 0.55 compact, user-approved in the
engine change). The pinned table in `tests/core/combat_formation.test.js` is re-pinned in the same commit.

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
- [A second floor-plate line reaches a front figure's torso] → only in two-rank sides whose step is too narrow for
  one line; the head stays clear by the fit rule, but that second line may cross the front figure's torso (at
  1451x790 and the 0.50 floor it starts about 35% below the figure's top).
- [Same-rank neighbours overlap at the shoulders] → heads stay apart by the 30% step floor; bodies may overlap
  side by side, as in the exploration row.

## Migration Plan

Pre-release client. Rollback is reverting the commits.

## Open Questions

None.
