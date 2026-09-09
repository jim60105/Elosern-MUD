# Design: align-gallery-art-consumption-specs

## D1 — One mapping, one owner capability

The rect→crop mapping ships as the pure module `face-rect.js::faceObjectPosition`,
imported by every framed-portrait surface (combat `ParticipantFrame`, party
strip/drawer, narrative-feed dialogue host avatar, interact target avatars,
dock target rows, `CharacterSwitcher`, `ReferenceArtwork`). Pinning it once in
`webclient-art-panel` — the capability that already owns the portrait catalog
and scene rendering — keeps one requirement to amend when cropping changes.
Per-surface crops stay observable through their own surfaces' existing
portrait requirements; only the shared rule and its universal application need
recording, so no combat/party/HUD deltas are filed.

## D2 — The centered fallback is part of the contract, not a detail

`faceObjectPosition` returns the centered `50% 50%` pair for `null`,
`undefined`, any non-finite field, any field outside `[0, 1]`, `x + w > 1`,
`y + h > 1`, or a non-positive `w`/`h`. The server already validates rects on
write, so a malformed rect reaching the browser signals a corrupt card the
presenter failed to degrade — the mapping must not compound that failure by
throwing or producing an off-frame percentage. The delta pins the fallback
explicitly; the rounding-tolerance boundary test (`tests/data/face_rect.test.js`)
is the executed evidence.

## D3 — ReferenceArtwork joins the re-frozen manifest, not a new showcase clause

The showcase spec already ends with: "On completion of the contextual HUD
redesign the required-component manifest SHALL be re-frozen at the complete
redesign set and the component-coverage gate SHALL enforce that frozen set."
The shipped manifest (51 entries, gate green) satisfies that clause, so
`World/ReferenceArtwork` needs no showcase delta — only its own behavioral
requirement in the art-panel capability: placeholder entries render no `img`,
a failed media load degrades to the labelled placeholder, and a URL change
re-arms the image element.

## D4 — Evidence is the shipped Vitest trio

`tests/data/face_rect.test.js` (mapping, fallback, tolerance),
`tests/core/reference_artwork.test.js` (placeholder, load-error, URL change),
and the crop assertions folded into `tests/combat/participant_frame.test.js`,
`tests/data/party_strip.test.js`, `tests/data/party_drawer.test.js`, and
`tests/action/dock_menu.test.js` already execute in the full Vitest suite.
At archive time the mapping and frame requirements gain their
`covers_requirement` annotations on registered rows in the Python node-suite
evidence harness (`web/webclient/tests/test_node_suite_evidence.py`) that
execute the face-rect and reference-artwork Vitest files — the same pattern the
waiting/practice requirements use. The annotations cannot live on the Vitest
files themselves: `tools.spec_traceability` discovers associations only from
Python `test_*.py` files.
