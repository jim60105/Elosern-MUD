# Design: Defeated foes and downed allies

## Context

- `StageActor.vue` dims a listener through `data-speaking="false"` with `filter: brightness(var(--actor-dim))` (0.6).
  It plays beat gestures on `.stage-actor__beat`, including `defeat` (fade and drop), and renders `ReferenceArtwork`,
  which covers the finished portrait, the placeholder initial card and the failure marker.
- Participant states are `active`, `fled`, `knocked_out` and `defeated`. Foes leave the line-up today when not active;
  a held round keeps them until their defeat beat.
- Motion tokens: `--motion-beat-defeat`, `--ease-exit`, and `--motion-travel` (0 at reduced).

## Decisions

### D1. Channels per state (never brightness alone)

| State | Shape | Tone | Text (plate) | Mark |
|---|---|---|---|---|
| Listener / unselectable dim | none | brightness 0.6, colour kept | none | none |
| Defeated foe | collapse: `scaleY(.8)` about the base (`transform-origin: 50% 100%`): the head drops 20%, the feet stay planted, and with no rotation and no translation the box stays inside its slot | `grayscale(1) brightness(.45)`, opacity .8 | `✕ 已擊破`, empty dashed stroke | broken seal over the chest |
| Downed ally | kneel: `scaleY(.92)` about the base: the head drops 8%, no rotation | `grayscale(.6) brightness(.7)`, opacity 1 | `▼ 倒地`, empty dashed stroke | none |

The defeated look is darker and lower in opacity than any dim. The seal and the collapse are the shape channel, and
已擊破/倒地 the text channel.

### D2. The seal mark

An inline SVG inside StageActor (`aria-hidden`, `pointer-events: none`): a circle ring in `--seal-400` with a
jagged crack path across it and a small missing wedge. It is sized at 28% of the figure width and centred at 42% of
the figure height. CSS draws it from tokens; there is no bitmap. Because it sits on the figure wrapper, it shows the
same over a portrait, a placeholder or failed art.

### D3. Where the treatment lives

`StageActor` gets `fallen` and sets `data-fallen`. Pose and tone apply on a new `.stage-actor__fall` wrapper around
`.stage-actor__beat`, so the beat gestures and the fall compose. Both poses only shrink the box vertically, so a fallen
figure stays inside its formation slot and out of the gap and the gutters. A knocked-out controlled figure takes the
down look too; its values stay in the vitals dock.

### D4. Motion

- `full`: a `transition` on transform/filter/opacity over `--motion-beat-defeat` with `--ease-exit`, and the seal's
  opacity transition delayed by the same duration. This is triggered when the beat queue applies the defeat beat (it
  sets the participant's displayed state).
- `reduced`: `--motion-travel` is 0, so the transform jumps while the filter and seal fade at ≤ 150ms.
- `off` and hydration: no transition.

The beat queue stops removing a defeated foe from `beatStage.foes`; the foe stays with `fallen: "defeated"`.

### D5. Drawn set

`drawnFoes = participants.filter(team === "foes" && state !== "fled")`, capped at 15. A defeated or downed figure
keeps its slot. A flee removes the figure (fade) and re-forms.

## Risks / Trade-offs

- [A rotated slump would push the box past its slot] → rejected: an 8° rotation moves a 440px figure's top by about
  61px (sin 8° × h); both poses are vertical only, and a Vitest checks the transformed box stays inside the slot.
- [A sink below the floor (`translateY` about the base) would leave the slot] → rejected: lowering by 12% about the
  base puts the feet 12% below the slot's floor, into the plates and the band. Both poses are a pure `scaleY` about
  the base, so the feet stay planted, and a Vitest checks the transformed box's top lies inside the slot and its bottom
  on the slot's floor.
- [Fallen foes keep the shared scale small] → accepted: they keep their slots so nothing reflows mid-fight; a lone
  survivor among fallen foes stays at the scale the full line-up needed.

## Migration Plan

Pre-release; rollback by revert.

## Open Questions

None.
