# Proposal: Align the browser's gallery-art consumption contract with the shipped face-rect cropping

## Why

The gallery pipeline specs (`art-gallery-model`, `art-gallery-resolution`,
`art-gallery-seed-sync`, `art-gallery-generation`) fully specify how the server
produces and carries the normalized `face_rect`, and
`webclient-art-panel` specifies that every portrait catalog entry with a media
URL carries the rectangle and every placeholder carries `null`. What no main
spec records is the browser's consumption of that field, shipped in
`ce8aa13 feat(webclient): consume gallery art payloads with face-rect crops`:

1. **One shared pure mapping.** `web/webclient-app/components/face-rect.js`
   exports `faceObjectPosition(rect)`, which maps the rect center to a CSS
   `object-position` percentage pair — under `object-fit: cover`, aligning the
   image's p% point with the frame's p% point keeps the authored face region
   centered in a frame of any aspect. A malformed rect (any non-finite field,
   a field outside `[0, 1]`, `x + w > 1`, `y + h > 1`, or a non-positive `w`/`h`)
   returns the centered `50% 50%` crop instead of throwing, so one bad card
   can never blank a portrait surface.
2. **Every framed portrait applies it.** The crop is consumed uniformly by the
   combat `ParticipantFrame` (ally and foe), the party strip and 同伴 · 隊伍
   drawer, the dialogue host avatar in the narrative feed, the interaction
   target avatars in the dock, the dock's target rows, and the top-bar
   character switcher — the browser renders the server's composition choice
   rather than a fixed center crop on every framed-portrait surface. The
   美術展示 catalog browser's own grid tiles and full view keep the centered
   default crop, and scene backdrops consume scene media rather than portrait
   entries; both are explicitly outside the contract.
3. **The shared `ReferenceArtwork` frame.** New required-manifest component
   `World/ReferenceArtwork` renders a portrait entry with cover fit and the
   rect-aligned crop, renders no `img` at all for a null-URL/placeholder entry
   (the truthfully labelled placeholder stands instead), degrades a failed
   media load to that placeholder, and re-attempts cleanly when the URL
   changes.

The component-coverage gate passes against the re-frozen 51-entry manifest
(including `ReferenceArtwork`), which the showcase spec's re-freeze clause
already governs — no showcase delta is needed. This change records only the
browser consumption contract; it edits no code.

## What changes

- `webclient-art-panel`: two ADDED requirements — the shared face-rect →
  `object-position` mapping with its malformed-input centered fallback and
  universal framed-portrait application (naming the combat participant frame,
  party strip/drawer, dialogue host avatar, interact target avatars, dock
  target rows, and character switcher as its consumers), and the
  reference-artwork frame's truthful placeholder / load-error / URL-change
  behavior. One capability owns the browser's whole rect-consumption contract,
  so no per-surface requirement edits are needed.

## Out of scope

- Server-side rect validation, defaults, and payload carriage — already
  specified by the `art-gallery-*` capabilities and unchanged.
- The showcase required-set re-freeze — governed by `webclient-component-showcase`'s
  existing completion clause; the shipped manifest satisfies it.
- Scene backdrop rendering — the art panel's scene requirement is unchanged;
  scenes carry no rect and keep their center cover crop.
