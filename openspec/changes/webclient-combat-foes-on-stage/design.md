## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C11c and C12 are archived.

- **Portrait anchors** (`HudFrame.vue`, C4a):
  - `actor-left` and `actor-right` are `.stage-anchor.stage-actor` boxes with `bottom: var(--band-h)`, `height: min(62vh, 680px, calc(100% - var(--header-h) - var(--band-h)))`, `aspect-ratio: 2 / 3`, `z-index: 2`, and `pointer-events: none`.
  - They are inset `left: 6%` and `right: 6%`. At 1920x1080 each is about 670 × 446px.
- **`StageActor.vue`** (C10b, C11b):
  - Props `portrait`, `name`, `side`, `dimmed`. The root is `[data-testid="stage-actor"][data-side][data-speaking]`.
  - A `null` portrait renders the name's initial and the name (via `portraitGlyph`).
  - C11b crossfades a source change (`actor-xfade`) and eases the dim over `--motion-fast`.
- **`AppClient.vue`** (C10b, C11c):
  - `#actor-left` renders the player's `StageActor` outside creation.
  - `#actor-right` renders the host's `StageActor` inside `<Transition name="actor-enter" v-bind="inertWhileLeaving">` while the mode is `dialogue` and the view model is available.
  - `#map` renders `ParticipantFrame` while `contextActionsPanel.kind === 'combat'`.
- **Combat participants** (`web/webclient/presentation/combat_panel.py` `_validate_participant`):
  - Exactly `identity` (int), `token`, `display_name`, `team` (`party` | `foes`), `state` (`active` | `fled` | `knocked_out` | `defeated`), `hp_current`, `hp_maximum`, and `portrait_ref` (decimal string or null), in presenter order.
  - `portrait_ref` equals the `art` catalog key (`world/rules/art_view.py::portrait_catalog_key`).
- **`ParticipantFrame.vue`** (H3, C4c) renders 我方 / 敵方 rows with token, name, `hp_current/hp_maximum`, state marker, and a 38px catalog thumbnail. A missing entry renders its own placeholder card, and a null ref renders none.
- **Motion** (C11a–C11c):
  - `--motion-actor` is 350ms at `full`, 150ms at `reduced`, and 0 at `off`.
  - `--motion-shift-lg` is 32px, and `--motion-travel` is 1 at `full` and 0 otherwise.
  - `lib/transition_hooks.js` exports `inertWhileLeaving`.
  - C11c added `data-mode-change`, the flash, the veil, and the flip, and deferred the foes' entrance to C13.
- **Specs that forbid foes on stage today:**
  - C10c's stage requirement: `actor-right` "SHALL carry no content in every other state".
  - C10b's stage-actor scenario "Nothing is dimmed outside dialogue": `actor-right` carries no stage actor in combat.
  - C11c's matrix row for `actor-right` in combat: "not rendered".
  - The main-spec participant-frame scenario: "`actor-right` holds no participant content".

## Goals / Non-Goals

**Goals:**
- Foes stand on the stage in combat, opposite the player, from committed data only.
- Several foes read as a group without covering the player or the stage's centre.
- `ParticipantFrame` stays the complete, legible numbers panel.
- The row enters and leaves only on live changes, at all three motion levels.

**Non-Goals:**
- Any beat behaviour, lock, or HP display (C13b and C13c).
- Allies on stage. Party members stay in the participant frame and the party quickbar, and the player alone stands in `actor-left` (design §4: "Party mini-portraits … ✓ (in participant frame)").
- HP bars on the stage actors (C13c).

## Decisions

### D1. One line-up component over `StageActor`
`FoeLineup.vue`:
- Props:
  - `foes`: an array of committed participant rows
  - `artPanel`
  - `max`: 3, not a public knob; stories and tests pass it only to show the cap
- It computes `shown = foes.slice(0, 3)` and `entryFor(p)`:
  - `p.portrait_ref == null` gives `null`
  - otherwise `artPanel?.portrait_catalog?.[p.portrait_ref] ?? null`
- Template:
  ```
  <div class="foe-lineup" data-testid="foe-lineup" :data-count="shown.length">
    <TransitionGroup name="foe" v-bind="inertWhileLeaving">
      <div v-for="(p, i) in shown" :key="p.identity" class="foe-lineup__slot"
           :style="{ '--foe-index': i }" :data-portrait-ref="p.portrait_ref ?? ''"
           data-testid="foe-slot">
        <StageActor :portrait="entryFor(p)" :name="p.display_name" side="right" :dimmed="false" />
      </div>
    </TransitionGroup>
  </div>
  ```
- `data-portrait-ref` is the hook C13b and C13c use to find a beat's actor or target on stage. It is the same key the beats carry (C12 D6).

*Why a missing entry passes `null`, not ParticipantFrame's `{placeholder: true}`:* `StageActor` has one truthful fallback, the name's initial and the name (C10b). That is more informative on a large portrait than the frame's "肖像圖像尚未生成" card. A pending placeholder entry from the catalog is still passed through and shows its own label.

*Why only active foes:* a defeated, fled, or knocked-out foe no longer acts. The frame keeps showing it with its text marker, so no information is lost. Removing it from the stage is also the natural anchor for C13c's "the portrait fades and drops out" beat.

*Alternative:* render `StageActor`s directly in `AppClient`. Rejected. The overlap geometry, the cap, and the move transitions are one reusable unit, and the showcase needs to document its count states.

### D2. Geometry: an overlapping row that grows leftward
- The line-up is `position: absolute; right: 0; bottom: 0; height: 100%; width: 100%` inside `actor-right`, whose combat rule adds `overflow: visible`.
- Slot scale `s` = `1`, `0.9`, or `0.8` for one, two, or three shown foes. It is set as `--foe-scale` on the root from `data-count`.
- Each slot is `position: absolute; bottom: 0; right: calc(var(--foe-index) * 65% * var(--foe-scale)); height: calc(100% * var(--foe-scale)); aspect-ratio: 2 / 3; z-index: calc(3 - var(--foe-index))`.
- The first foe (presenter order) stands nearest the edge and in front. Later foes step toward the centre and behind it.

Checked extents with three foes:
- **1920x1080:** the anchor is about 670 × 446px. A slot is about 357px wide, and the row spans 357 + 2 × 0.65 × 357 ≈ 821px. The right edge is 1805px, so the left edge is at about 984px, right of the stage centre (960px). The player occupies about 115–561px.
- **1280x720:** the stage box is 412px tall. A slot is about 220px wide, and the row spans about 505px. The right edge is about 1203px, so the left edge is at about 698px (centre 640px). The player occupies about 77–352px.

So the row never crosses the stage's vertical centre line and never touches `actor-left`. As portrait art (C10b), it may sit behind the HUD islands, the `choices` anchor (not rendered in combat), and the command-line row.

*Why a cap of three:* a fourth slot at 0.8 scale would cross the centre at 1920 (about 1170px wide). At 1280 it would reach the player's box once the scale drops further. Most encounters have one to three foes. The frame lists the rest, so nothing is hidden.

*Alternative:* shrink every foe to fit N. Rejected. At five foes the portraits would be thumbnails, which duplicates the frame and defeats the stage.

*Alternative:* a "+N" plate. Rejected (coordinator-approved decision). It would be a second, lesser count beside the frame's complete list.

### D3. Entering and leaving, live only
- **Mode entry and exit.** `AppClient` wraps the line-up in `<Transition name="foes-enter" v-bind="inertWhileLeaving">`, the same pattern as C11c D3's host actor.
  - Enter from, and leave to: `opacity: 0; transform: translateX(calc(var(--motion-shift-lg) * var(--motion-travel)))`.
  - The active classes run `opacity` and `transform` over `--motion-actor`, with `--ease-enter` on enter and `--ease-exit` on leave.
  - Vue's `<Transition>` does not animate the initial render without `appear`. So a reload or reconnect in combat mounts the row in place, which is C11c's "a reconnect replays nothing".
  - The live exploration → combat change inserts the row after mount, so it slides in beside C11c's flash, veil, and flip.
  - `data-mode-change` is therefore not needed as a selector here: `<Transition>` already gives the live-only property.
- **Membership changes inside combat.** `<TransitionGroup name="foe">`:
  - `.foe-leave-active`: `opacity` over `--motion-actor` with `--ease-exit`. The leaving slot is inert through the bound hooks. TransitionGroup does not accept hook props through `v-bind` on some Vue versions, so if that is the case the same four hooks are passed as explicit `@before-leave` / … listeners.
  - `.foe-enter-from`: the same offset and fade as mode entry.
  - `.foe-move`: `transition: transform var(--motion-actor) var(--ease-standard)`, so the remaining foes glide to their new slots when the front foe leaves.
  - Initial children do not animate (no `appear`).
- **Levels.** At `reduced` everything is a ≤150ms fade with no travel. At `off` every change is final in the commit's frame.

### D4. `ParticipantFrame` stays the numbers panel
It is unchanged in component and position (`map`, C4c). The line-up adds no numbers, names, or tokens on the stage. The frame's 38px thumbnail is the same catalog entry as the stage actor, so the player can tie a row to a figure. The frame requirement's scenario is restated: `actor-right` holds the line-up's decorative actors and no frame row, numerals, or token.

### D5. Speaking state and accessibility
- Foe actors are never dimmed. C10b's rule "outside dialogue mode no stage actor is dimmed" is kept.
- The line-up and its actors carry no focusable element, sit in the `pointer-events: none` anchor, and add no accessible text beyond `StageActor`'s image alt and placeholder label. This is the same as the host actor.
- The frame remains the accessible list of participants.

### D6. Art-panel consumer list
`webclient-art-panel` "Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded" lists the only surfaces that may render catalog entries. C10b added the host stage actor but did not restate this list, so it is stale. This change restates it:
- It names the stage actors (the player's in `actor-left`, the dialogue host's, and the foe line-up's in `actor-right`).
- It replaces "the dialogue host avatar", which C10b deleted with the dialogue box's `.av`, with the dialogue host's stage actor.

The face-rect requirement is not modified. `StageActor` renders through `ReferenceArtwork`, whose own requirement already applies the crop.

### D7. Tests
- **Vitest** `tests/core/foe_lineup.test.js`:
  - one, three, and five active foes render one, three, and three slots in presenter order, with `data-count`
  - non-active foes and `party` rows are never passed by `AppClient` (covered in the app test); the component renders whatever it is given, capped
  - an image entry, a pending placeholder entry, a missing entry, and a null ref: image, entry placeholder, name placeholder, name placeholder
  - `data-portrait-ref` per slot
  - no element with a tabindex, and no actor is dimmed
  - with `stubs: { transition: false, 'transition-group': false }`, a removed foe's slot is `inert` while leaving
- **Vitest** `tests/app_client_stage_actor.test.js`:
  - in combat, `#actor-right` holds `foe-lineup` with only active foes
  - in exploration, `#actor-right` is empty
  - in dialogue, it holds the host
  - a combat → exploration change leaves an inert line-up
- `tests/hud_frame.test.js`: the combat `actor-right` rule allows overflow.
- **Browser** `web/tests/browser/test_browser_combat_stage.py`. It injects combat snapshots built from `_journey_support._combat_panel()` with its `participants` replaced, plus `_art_panel(...)`.
  - `test_foes_stand_opposite_the_player` (1920x1080, 1440x900, 1280x720, with one and three active foes):
    - the line-up is inside `anchor-actor-right`
    - the first slot's right edge is 6% of the stage width from the right edge (±1px), and every slot's bottom equals the band's top (±1px)
    - the leftmost slot's left edge is right of the stage centre and does not intersect `anchor-actor-left`
    - the slot heights are 1.0 or 0.8 of the player actor's height (±1px)
    - no element inside it is focusable
    - the participant frame still lists every participant with numerals
  - `test_foes_beyond_three_stay_in_the_frame`: with five active foes, three slots show and the frame shows five 敵方 rows.
  - `test_foes_enter_and_leave_full` (`motion_level=None`):
    - after a live exploration → combat injection, the line-up's computed `transition-duration` includes `0.35s` and its transform is not identity on the first frame
    - after a combat → exploration injection, a leaving `foe-lineup` has `inert`, and eventually none remains
    - a defeated foe (state change in an update) leaves an inert slot
  - `test_reload_in_combat_plays_no_entrance`: after a reload in combat, the line-up is present with no running transition.
  - `test_foes_off_is_instant` (default `off`): in the frame after each injection, the line-up is fully present or absent.
  - Annotations:
    - all journeys: `webclient-contextual-hud::foes-stand-opposite-the-player-during-combat`
    - the geometry journey also: `webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces` and the participant-frame ID
- **Existing browser tests:**
  - `test_browser_contextual_hud_combat.py::test_combat_participant_frame_presents_participants_and_portraits` gains the assertion that `actor-right` holds the line-up and no `participant-frame` descendant.
  - `test_browser_contextual_hud_stage.py`: any "actor-right is empty" assertion in combat is updated.
- **Evidence:** `test_node_suite_evidence.py` gains `test_foe_lineup_vitest_evidence_passes`, annotated with the new ID.

### D8. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| contextual-hud "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces" | C10c `webclient-dialogue-choices-overlay` |
| contextual-hud "Surface visibility is gated by the committed game mode" | C11c `webclient-mode-transitions` |
| contextual-hud "Stage actors present the player and the dialogue host with a speaking state" | C10b `webclient-dialogue-stage-actors` |
| contextual-hud "The combat participant frame presents the session's participants and their portraits" | main spec (no series change touches it) |
| component-showcase "Every required UI component is a Vue SFC with a documented Storybook story" | C10c |
| art-panel "Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded" | main spec |

- Every scenario title is kept. Bodies change only where they said `actor-right` is empty in combat. No annotation moves.
- The new ID is covered as D7 lists.
- `openspec validate` may report that blocks based on unarchived series changes cannot apply yet. That is expected.

**Archive order: C12 (`combat-beats-panel`) → C13a (this change) → C13b (`webclient-combat-beat-queue`) → C13c (`webclient-combat-beat-choreography`).** C12 itself archives after C11c. C13c modifies "Surface visibility…" again, on this change's text. If a base block changes before archive, re-sync this change's blocks and keep only its own edits: the foe line-up in `actor-right`, the matrix row, the foe actors, the frame's scenario, and the consumer list.

## Risks / Trade-offs

- [A tall foe portrait covers part of the `map` anchor's participant frame at 1280x720] → Portrait anchors already may sit behind HUD islands (C10b). The islands are above the portraits in z-order, so the frame stays readable.
- [Foes four and later are not on stage] → Intentional (D2). The frame lists them, and C13c plays their beats on the frame's numbers only.
- [TransitionGroup hook binding differs from `<Transition>`] → D3 names the explicit-listener fallback. The Vitest inert case catches a miss.
- [Budget] → component and geometry (2.5h), AppClient and transitions (1.5h), story, manifest, and showcase evidence (1h), Vitest (1h), browser (1.5h), specs and gates (0.5h). About 8h.

## Migration Plan

None. The client is unreleased, and nothing is persisted.
