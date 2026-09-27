## Context

See proposal.md (Why). The state below comes from the code on master after C1 to C11c and C12 were archived, and after the two stage fixes that followed C11c (the scene caption plate, commit 33c83461, and the clipped stage, commit b26db1f9).

- **Portrait anchors** (`HudFrame.vue`, C4a, C10b):
  - `actor-left` and `actor-right` are `.stage-anchor.stage-actor-anchor` boxes with `bottom: var(--band-h)`, `height: min(62vh, 680px, calc(100% - var(--header-h) - var(--band-h)))`, `aspect-ratio: 2 / 3`, `z-index: 2`, and `pointer-events: none`. They set no `overflow`.
  - Their insets are the C10b tokens `--actor-left-inset` and `--actor-right-inset: max(6vw, calc(280px - var(--actor-h) / 3))`, grown where 6% would put the figure's face under the island column (the minimap card on the right). `--actor-h` is the anchor height. At 1920x1080 each anchor is about 670 × 446px and both insets are 6%.
- **The stage** (`HudFrame.vue`, b26db1f9): `.elosern-stage` and `.elosern-app-shell` are `overflow: clip`, `.stage-band` is `overflow-x: clip`, and focus moves use `preventScroll`. `test_no_stage_ancestor_scrolls_horizontally_full` asserts that no stage ancestor ever scrolls horizontally.
- **The scene caption** (`SceneBackdrop.vue`, `app-shell.css`, 33c83461): one single-line plate on the stage floor (`--scene-caption-h` 34px, 12px above the command-line row), in the backdrop layer under the portraits, centred between the two portrait anchor boxes (`left`/`right` from the `--actor-*` tokens). The label takes at most 55% of the row; label and alt text end in an ellipsis.
- **`StageActor.vue`** (C10b, C11b):
  - Props `portrait`, `name`, `side`, `dimmed`, `motionLevel`. The root is `[data-testid="stage-actor"][data-side][data-speaking]`.
  - A `null` portrait renders the name's initial and the name. A placeholder entry keeps its own label with the name's initial in the ring.
  - The figure is masked by an ellipse intersected with a fade at the feet. C11b crossfades a source change (`actor-xfade`).
- **`AppClient.vue`** (C10b, C11c):
  - `#actor-left` renders the player's `StageActor` outside creation.
  - `#actor-right` renders the host's `StageActor` inside `<Transition name="actor-enter" :css="hostTransitionCss" v-bind="inertWhileLeaving">`, where `hostTransitionCss` is `motionLevel !== 'off' && !modeHydrating` (the live-only rule).
  - `#map` renders `ParticipantFrame` while `contextActionsPanel.kind === 'combat'`.
- **Combat participants** (`web/webclient/presentation/combat_panel.py` `_validate_participant`):
  - Exactly `identity` (int), `token`, `display_name`, `team` (`party` | `foes`), `state` (`active` | `fled` | `knocked_out` | `defeated`), `hp_current`, `hp_maximum`, and `portrait_ref` (decimal string or null), in presenter order.
  - `portrait_ref` equals the `art` catalog key (`world/rules/art_view.py::portrait_catalog_key`).
- **`ParticipantFrame.vue`** (H3, C4c) renders 我方 / 敵方 rows with token, name, `hp_current/hp_maximum`, state marker, and a 38px catalog thumbnail. It fills the `map` anchor's whole width in combat, `--right-column - 28px` (332px at 1920, 289px at 1440, 218px at 1280, where `--right-column` is 246px), so its left edge is `--right-column - 12px` from the stage's right edge — wider than the 218px minimap card that `--actor-right-inset` clears at 1920 and 1440. Its product styling (`styles/app-shell.css`) stacks the name over the numerals in 60–72px rows, so six participants make it 516–576px tall.
- **Motion** (C11a–C11c):
  - `--motion-actor` is 350ms at `full`, 150ms at `reduced`, and 0 at `off`. `--motion-flash` is 120ms at `full` and 0 otherwise. `--motion-shift-sm` / `--motion-shift-lg` are 12px / 32px, and `--motion-travel` is 1 at `full` and 0 otherwise. `--motion-slow`, `--motion-trail`, and `--motion-trail-delay` drive the vitals' fill and trailing bar.
  - `lib/transition_hooks.js` exports `inertWhileLeaving`. `composables/use-mode-change.js` exports `modeChange` and `modeHydrating`.
  - C11c added `data-mode-change`, the flash (z-index 3, above the portraits), the veil, and the dock flip, and deferred the foes' entrance to C13.
- **Specs that forbid foes on stage today:**
  - The stage requirement: `actor-right` "SHALL carry no content in every other state".
  - The stage-actor scenario "Nothing is dimmed outside dialogue": `actor-right` carries no stage actor in combat.
  - The visibility matrix has no line-up row.
  - The participant-frame scenario: "`actor-right` holds no participant content".
- **Checked against the original plan of this change:** a 0.8-scale row of three at 65% offsets from the 6% inset crosses the stage centre at 1440x900 (left edge ≈661 < 720) and at 1280x720 (≈632 < 640), because C10b grew the right inset; and at 1920x1080 the front foe's face (x≈1582) sits under the participant frame's left edge (x≈1572), which paints above the portraits.

## Goals / Non-Goals

**Goals:**
- Foes stand on the stage in combat, opposite the player, from committed data only.
- Several foes read as one composed group in depth, without covering the player, the stage's centre, the scene caption, or each other's faces, and with every foe's face clear of the participant frame.
- Each foe shows a decorative HP gauge with a trailing bar (design §10.2, C13a paragraph), from the committed hit points.
- `ParticipantFrame` stays the complete, legible numbers panel.
- The row enters and leaves only on live changes, choreographed with C11c's flash, veil, and dock flip, at all three motion levels.

**Non-Goals:**
- Any beat behaviour, lock, or displayed-HP value during playback (C13b and C13c). C13c feeds the gauge its displayed value.
- Allies on stage. Party members stay in the participant frame and the party quickbar, and the player alone stands in `actor-left` (design §4).

## Decisions

### D1. One line-up component over `StageActor`
`components/FoeLineup.vue`, with its pure geometry and selection in `components/foe-lineup.js`:
- Props: `foes` (the committed active foes, presenter order), `artPanel`, `motionLevel`, and `max` (3; not a public knob, stories and tests pass it only to show the cap).
- `shown = foes.slice(0, 3)`. `entryFor(p)`: a `null` ref gives `null`; otherwise `artPanel?.portrait_catalog?.[p.portrait_ref] ?? null` (the raw entry, so a pending entry keeps its own card; a missing entry falls to `StageActor`'s name placeholder). The component builds no key and no URL.
- Template:
  ```
  <div class="foe-lineup" data-testid="foe-lineup" :data-count="shown.length"
       :style="{ '--foe-front-scale': slots[0]?.scale ?? 1 }" aria-hidden="true">
    <TransitionGroup name="foe" :css="motionLevel !== 'off'" v-bind="inertWhileLeaving">
      <div v-for="(p, i) in shown" :key="p.identity" class="foe-lineup__slot" data-testid="foe-slot"
           :data-portrait-ref="p.portrait_ref ?? ''" :style="slotStyle(i)">
        <StageActor :portrait="entryFor(p)" :name="p.display_name" side="right" :dimmed="false"
                    :motion-level="motionLevel" />
        <div class="foe-lineup__gauge" data-testid="foe-gauge">
          <span class="foe-lineup__ghost" :style="{ width }"></span>
          <span class="foe-lineup__fill" :style="{ width }"></span>
        </div>
      </div>
    </TransitionGroup>
  </div>
  ```
- `data-portrait-ref` is the hook C13b and C13c use to find a beat's actor or target on stage. It is the same key the beats carry (C12 D6).
- `activeFoes(participants)` (in `foe-lineup.js`) is the selection `AppClient` applies: `team === "foes" && state === "active"`, in order.

*Why a missing entry passes `null`, not ParticipantFrame's `{placeholder: true}`:* `StageActor` has one truthful fallback, the name's initial and the name (C10b). That is more informative on a large portrait than the frame's "肖像圖像尚未生成" card.

*Why only active foes:* a defeated, fled, or knocked-out foe no longer acts. The frame keeps showing it with its text marker. Removing it from the stage is also the anchor for C13c's "the portrait fades and drops out" beat.

*Alternative:* render `StageActor`s directly in `AppClient`. Rejected. The depth geometry, the cap, the gauges, and the membership transitions are one reusable unit, and the showcase documents its count states.

### D2. Geometry: a depth-staged row that grows leftward
All measures are fractions of the portrait anchor (`foe-lineup.js`), so the row keeps its proportions at every viewport:

| Shown | Heights, front to back (× anchor height) | Span (× anchor width) |
|---|---|---|
| 1 | 1 | 1 |
| 2 | 0.9, 0.78 | 1.27 |
| 3 | 0.8, 0.7, 0.61 | 1.40 |

- Each later foe shows `FOE_EXPOSED` = 46% of its own width past the foe in front: slot `i`'s right edge sits `right(i) = right(i-1) + scale(i-1) - 0.54 × scale(i)` anchor widths left of the row's right edge.
- Depth: each foe behind is smaller, stands `FOE_LIFT` = 3.5% of the anchor's height higher (up-stage), and is drawn behind (`z = count - i`). The front foe casts a soft `drop-shadow` onto the foe behind it, so figures that share a flat backdrop colour still separate. The front foe shrinks as the group grows, so three foes fit right of centre at 1440x900.
- The row (`.foe-lineup`) is the anchor's box stepped left: `right: calc(max(var(--actor-right-inset), var(--foe-face-clear) - var(--actor-h) * var(--foe-front-scale) / 3) - var(--actor-right-inset))`, with `--foe-face-clear: calc(var(--right-column) + 12px)` in `tokens.css`. That is the participant frame's left edge (`--right-column - 12px` from the stage's right edge) plus 24px of air, so the front foe's face (its slot's centre, `scale × actor-h / 3` from its right edge) always clears the frame, which paints above the portraits. The front foe's scale enters the formula, so it is written where that scale is known (the row, and the caption rule in D6), not as a root token. At short viewports (`max-height: 820px`, the 412px stage box at 1280x720) a full encounter's frame reaches down to the stage floor, so `--foe-face-clear` grows to `calc(var(--right-column) + 48px)` and the front foe's gauge clears the frame too.
- The anchor keeps its box. HudFrame's combat rule sets `overflow: visible` on `actor-right` (explicit; anchors set no overflow today). The stage's `overflow: clip` clips anything past the stage edge without making it scrollable.

Checked extents with three foes (row left edge; stage centre; player's right edge):
- **1920x1080:** ≈1101; 960; 562.
- **1440x900:** ≈738; 720; 482.
(Measured in the client; the browser geometry journey asserts them.)
- **1280x720:** ≈711; 640; 361.

With one and two foes the row ends further right. The face of the front foe clears the frame by 24px at every count and viewport.

*Why a cap of three:* a fourth foe at the same step would cross the centre at 1440x900. Most encounters have one to three foes. The frame lists the rest, so nothing is hidden.

*Alternative:* one uniform scale per count (1 / 0.9 / 0.8, as first planned). Rejected on review of the stage: a row of equal figures reads as a line-up for a photograph, not as a group in depth, and it cannot keep three foes right of centre at 1440x900 once the frame is cleared.

*Alternative:* shrink every foe to fit N. Rejected. At five foes the portraits would be thumbnails, which duplicates the frame and defeats the stage.

*Alternative:* a "+N" plate. Rejected (coordinator-approved decision). It would be a second, lesser count beside the frame's complete list.

### D3. Entering and leaving, live only
- **Mode entry and exit.** `AppClient` wraps the line-up in `<Transition name="foes-enter" :css="hostTransitionCss" v-bind="inertWhileLeaving">`, the host's live-only rule (C11c D3): at `off` there is no CSS phase, and across a reconnect (`modeHydrating`) the row mounts and goes in the commit's frame. Vue's `<Transition>` does not animate the initial render (no `appear`), so mounting in combat plays nothing either.
  - Entry, choreographed with C11c: the flash floods the stage (it paints above the portraits); after half the flash (`calc(var(--motion-flash) * 0.5)`, 60ms at `full`, 0 below) the row fades in over `--motion-actor` while each foe decelerates in from `translateX(calc(var(--motion-shift-lg) * (1.5 - 0.25 × index) * var(--motion-travel)))` — the front foe travels furthest (parallax). The row and its foes share one duration and one delay: Vue times the transition on the row element alone, so a foe transition longer than the row's would be cut by the class removal.
  - Exit: the row fades over `--motion-actor` (`--ease-exit`) while its foes drift `--motion-shift-sm` to the right. The leaving row is inert.
- **Membership changes inside combat.** `<TransitionGroup name="foe" :css="motionLevel !== 'off'" v-bind="inertWhileLeaving">` (Vue 3.5 passes the bound hooks and `css` to TransitionGroup), whose `after-leave` emits `settled` (design D6):
  - `.foe-enter-from`: the same slide and fade as the mode entry.
  - `.foe-leave-active`: `opacity` over `--motion-actor` (`--ease-exit`), in place (the slots are absolutely positioned). The leaving slot is inert.
  - Re-slotting glides: the slots' base transition runs `right`, `bottom`, and `height` over `calc(var(--motion-actor) * var(--motion-travel))`, and the row's own `right` (the front foe's scale changes its inset) glides the same way. The base transition never names `transform`, so TransitionGroup's FLIP move stays off: a FLIP moves the box but jumps its size.
- **Levels.** At `reduced` everything is a ≤150ms fade with no travel and no glide. At `off` every change is final in the commit's frame.

### D4. `ParticipantFrame` stays the numbers panel
It stays in the `map` anchor (C4c) and remains the only surface with tokens, numerals, and state markers. The line-up adds no numbers, names, or tokens on the stage. The frame's thumbnail is the same catalog entry as the stage actor, so the player can tie a row to a figure.

Visual refinement (C4c / H3 work, the frame's product rules in `styles/app-shell.css`): each row was 60–72px (12px padding, 10px gaps, 38–40px art), so a six-participant frame reached 516–576px and covered the front foe's gauge at 1440x900. Rows now use 6px padding and 6px gaps with a 32px token and a 36px thumbnail, a long name ends in an ellipsis, and at short viewports (`max-height: 820px`) a compact variant (28px token, 32px thumbnail, 14px name) applies. A six-participant frame then ends at about 552px at 1440x900, above the gauges at 563px. No behaviour changes; the frame requirement gains the ellipsis and compactness rule.

### D5. Gauges, speaking state, and accessibility
- Each slot carries a decorative gauge (design §10.2, C13a paragraph): 8px tall, `clamp(72px, 44%, 168px)` wide, centred under the figure on the scene caption's baseline (`bottom: calc(var(--command-line-h) + 12px + (var(--scene-caption-h) - 8px) / 2)`, less the slot's lift), so the gauges and the caption plate share one floor line above the expanded command-line row. A dark trough with the caption plate's gold hairline keeps it legible over light and dark art. The fill is the vitals' hit-point red (`var(--vit-hp)`, so the colour-blind override applies), moving over `--motion-slow`; the pale trailing bar follows over `--motion-trail` after `--motion-trail-delay`, so a drop shows as a gap. The ratio is `hp_current / hp_maximum`, clamped to 0..100. No numerals.
- Foe actors are never dimmed. C10b's rule "outside dialogue mode no stage actor is dimmed" is kept.
- The line-up root is `aria-hidden`, carries no focusable element, and sits in the `pointer-events: none` anchor. The frame remains the accessible list of participants.
- A foe's figure mask is tighter than the player's (`radial-gradient(ellipse 48% 58% at 49% 45%, #000 46%, transparent 100%)`), so neighbouring foes overlap as bodies rather than as pale cards of their portraits' flat backdrops. The placeholder's ring and initial scale with the slot (`--foe-scale`), so a back foe's placeholder is never larger than its body.

### D6. The scene caption clears the row
The caption plate sits on the stage floor between the portrait anchors (33c83461). The row reaches left beyond `actor-right`, so the caption's right side becomes
`max(<the anchor box rule>, <row inset> + var(--actor-h) * 2 / 3 * var(--foe-lineup-span, 0) + 16px)` and transitions `right` with the row (`calc(var(--motion-actor) * var(--motion-travel))`). `AppClient` binds `--foe-lineup-span` (the row's span in anchor widths) and `--foe-front-scale` on `.elosern-root`. The room only grows while the row stands: a row that shrinks inside combat (a foe fell or fled) keeps the room it had until that foe has faded — the line-up's inner `TransitionGroup` emits `settled` after each leave, and `AppClient` re-derives the reach from the committed count then — and a row that leaves the stage keeps it until the outer transition's `after-leave` releases it, so the caption never slides under a fading row or a fading foe. At `off` and across a reconnect both run in the commit's frame. The rule is not gated on `data-elosern-mode`, which flips at the commit. The plate stays centred between the player and the leftmost foe.

In a narrow caption (combat at 1440x900) the label now gives way last: it no longer shrinks (still at most 55%), so the alt text truncates first.

*Known imprecision:* with several foes falling at once, or a second foe falling while an earlier one still fades, the room is re-derived from the committed count when the first of those fades ends, so the caption starts gliding `right` a little before the last departing figure is gone. The plate paints below the portraits and glides over its own `--motion-actor` window, so the most this shows is a fading figure's art over the plate's edge for a few frames; the static geometry the spec asserts is unaffected.

### D7. Stage-actor edges (C10b refinement)
The mask ellipse was 54% wide around a centre at 52%, so the figure's box kept up to 28% opacity at its inner edge and about 58% at its top edge: a visible seam on a dark scene, which overlapping foes would multiply. The ellipse is now exactly as wide as the box (`ellipse 50% 62% at 51% 46%, #000 58%`, mirrored at 49%), and the vertical fade opens with a short rise (`linear-gradient(transparent, #000 5%, #000 70%, transparent 97%)`). The player and the host keep their look otherwise.

### D8. Art-panel consumer list
`webclient-art-panel` "Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded" lists the only surfaces that may render catalog entries. C10b deleted the "dialogue host avatar" it names. This change restates the list with the stage actors that stand the dialogue host and the combat foes in `actor-right`. The face-rect requirement is not modified: `StageActor` renders through `ReferenceArtwork`, whose own requirement applies the crop.

### D9. Tests
- **Vitest** `tests/core/foe_lineup.test.js`: 1 / 3 / 5 foes → 1 / 3 / 3 slots in order with `data-count`; image, pending card, missing entry, and null ref; `data-portrait-ref`; decorative (aria-hidden, no focusables, never dimmed); the gauge width follows the committed hit points with no numerals; the slot styles come from `foeSlots`, and every foe but the rearmost carries the `--before` depth-shadow class; a removed foe's slot is inert while leaving (real transition stubs) and `settled` is not emitted yet, and gone at once at `off` with one `settled`; no literal durations, no `transform` in the slots' base transition, and the fill and its trailing bar named on the vitals' tokens; the geometry helper (cap, falling scales, the exposed share, lift, z order, spans) and `activeFoes` / `foeHpPercent`.
- **Vitest** `tests/app_client_stage_actor.test.js`: in combat `actor-right` holds only the active foes from the catalog, lit and unfocusable, while the player stays lit; exploration and dialogue hold no line-up.
- **Vitest** `tests/mode_transitions.test.js`: a live entry gives the row `foes-enter-enter-active`, and leaving leaves an inert `foes-enter-leave-active` copy while `--foe-lineup-span` holds; a defeat inside combat leaves an inert `foe-leave-active` slot while the other takes the front place, and the span keeps the fallen foe's room until its fade has settled; a reconnect mounts the row at rest; at `off` the row comes and goes in the commit's frame and the span follows every change, including the release. The host reader selects only `actor-right`'s own child.
- **Vitest** `tests/hud_frame.test.js`: the combat `overflow: visible` rule, `--foe-face-clear`, and the caption rule. `tests/overlays/objective_tracker_integration.test.js`: `actor-right` holds the line-up and no frame numerals.
- **Browser** `web/tests/browser/test_browser_combat_stage.py`, injecting combat snapshots with its own participants and catalog (served portrait routes):
  - `test_foes_stand_opposite_the_player` (1920x1080, 1440x900, 1280x720 × one, two, and three foes): the row is inside `anchor-actor-right`; the front foe's bottom is on the band's top edge and each foe behind stands higher; heights are the table's fractions of the player's height (±1px); every foe is right of the stage centre and clear of `actor-left`; the front foe's centre is ≥24px left of the frame; each foe's gauge lies above the command-line row; the caption plate lies between `actor-left` and the leftmost foe, centred (±1.5px); nothing inside is focusable; the frame lists every participant with numerals.
  - `test_foes_beyond_three_stay_in_the_frame`: five active foes → three slots, five 敵方 rows.
  - `test_foes_enter_and_leave_full` (`motion_level=None`): the live entry's first frame has the row entering with a `0.35s` transition and non-identity foe transforms; a defeat leaves an inert slot while the caption keeps the two-foe room, which it releases only once that foe has faded; the exit leaves an inert row, then none, and the room goes with it; and no stage ancestor scrolls horizontally in any sampled frame.
  - `test_reload_in_combat_plays_no_entrance`, `test_foes_reduced_only_fade` (≤150ms, identity transforms, the room released once the fallen foe has faded), `test_foes_off_is_instant`.
  - Annotations: every journey `webclient-contextual-hud::foes-stand-opposite-the-player-during-combat`; the geometry journey also the stage requirement, the participant-frame requirement, and the scene-backdrop requirement.
- **Existing browser tests:** `test_browser_contextual_hud_combat.py::test_combat_participant_frame_presents_participants_and_portraits` asserts `actor-right` holds the line-up and no `participant-frame` descendant.
- **Evidence:** `test_node_suite_evidence.py::test_foe_lineup_vitest_evidence_passes`, annotated with the new ID. `Core/FoeLineup` joins the manifest and the four showcase evidence lists.

### D10. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| contextual-hud "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces" | main spec (C10c, 33c83461) |
| contextual-hud "Surface visibility is gated by the committed game mode" | main spec (C11c) |
| contextual-hud "Stage actors present the player and the dialogue host with a speaking state" | main spec (C10b, C10c) |
| contextual-hud "The combat participant frame presents the session's participants and their portraits" | main spec |
| contextual-hud "The scene backdrop renders the art payload truthfully behind the stage" | main spec (33c83461) |
| component-showcase "Every required UI component is a Vue SFC with a documented Storybook story" | main spec (C10c) |
| art-panel "Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded" | main spec |

- Every block is rebuilt on the current main text; only this change's edits differ. Every scenario title is kept, and new scenarios are added. No annotation moves.
- The new ID is covered as D9 lists.

**Archive order: C12 (`combat-beats-panel`, archived) → C13a (this change) → C13b (`webclient-combat-beat-queue`) → C13c (`webclient-combat-beat-choreography`).** C13c modifies "Foes stand opposite the player during combat" again, on this change's text: it keeps the pre-round roster during playback and feeds the gauge (which this change ships) its displayed value. C13c's artifacts are adjusted to say the gauge exists.

## Risks / Trade-offs

- [A portrait with a light flat backdrop glows on a dark stage] → The foe mask is tighter than the player's and the front foe's shadow separates overlapping figures; generated art varies, and the stories review both light and dark backdrops.
- [A tall foe covers part of the participant frame] → The islands paint above the portraits and the row steps in until the front face clears the frame; the frame is shorter now (D4).
- [Three foes leave little air right of centre at 1440x900 (≈18px)] → The browser geometry journey asserts the centre line at every supported viewport.
- [Foes four and later are not on stage] → Intentional (D2). The frame lists them.
- [TransitionGroup binding] → Verified against Vue 3.5: TransitionGroup takes the bound hooks and `css`; the Vitest inert case catches a miss.
- [Budget] → component and geometry (3h), AppClient, caption, and transitions (1.5h), story, manifest, and showcase evidence (1h), Vitest (1h), browser (1.5h), specs and gates (0.5h). About 8.5h.

## Migration Plan

None. The client is unreleased, and nothing is persisted.
