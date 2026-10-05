## Batch:

- depends-on: official-artwork-catalog, official-content-provenance, builtin-silhouette-stage-fallback
- conflicts: `world/art/presenter.py` payload branch and the portrait origin wire vocabulary with `builtin-silhouette-stage-fallback` — expressed as a declared dependency so the supervisor serializes it: that change establishes the closed origin vocabulary (`runtime | silhouette | placeholder`) and the decorative `fallback` field, and this change EXTENDS the shipped vocabulary with `official` exactly once (if an operator lands them in the reverse order, this change establishes the vocabulary and the silhouette change rebases). `world/art/gallery_match.py` chain/payloads and `world/art/gallery.py` read-model vocabulary with `official-art-personalization` (declared downstream; serialize this change first); the `webclient-art-panel` portrait-catalog requirement is edited sequentially by silhouette → this change → personalization. Integration must be serialized, not merged in parallel: one presenter, one chain, one payload vocabulary.

## Why

With a catalog (change 1) and content references (change 3), resolution must weave official artwork into the deterministic presentation chain and make the three image kinds — official read-only, mutable runtime, built-in silhouette — distinguishable in every versioned contract, per the source design §6–§7. Today a payload's URL presence is indistinguishable across sources, which the design explicitly forbids.

## What Changes

- Extend the deterministic resolution chain to the design's presentation order: (1) the image selected by the existing runtime gallery rules (personal official selection joins this step in `official-art-personalization`), (2) existing valid classic runtime artwork, (3) the mounted catalog's default official image for the entity's content reference, (4) the attribute-selected built-in silhouette. A stale/unresolvable official default reference falls through the remaining chain without error; resolution stays a pure function of stored state plus the startup snapshot; no network call is added anywhere.
- Add an origin discriminator to every resolution payload (the closed vocabulary `runtime | silhouette | placeholder` established by `builtin-silhouette-stage-fallback`, extended here with `official`): official entries, runtime entries, and silhouettes must remain distinguishable, and origin or generation success must never be inferred from the presence of a URL. Official payloads carry the fingerprinted same-origin URL from change 1, validated geometry from directory metadata or fitted defaults, and the validated manifest-declared stage where present or identity placement as default/fallback; they expose no filesystem root, deployment source, license text, or prompts.
- Update the affected versioned contracts together with their producers, dual-side validators, and frontend consumers: the art panel portrait catalog and the roster row portrait vocabulary carry the origin discriminator (the contextual-HUD stage actors render committed catalog entries verbatim and need no rule change — verified by contract tests).
- Keep portrait age/eligibility validation ordering: eligibility runs before official or runtime character artwork may be presented; neither directory metadata nor a direct image URL bypasses the existing checks. Safe built-in placeholder selection may still use validated attributes when no named portrait policy exists.
- Suppress the automatic initial portrait generation when eligible official artwork already satisfies the entity's content reference; manual generation stays available; the creation-time skip flag keeps its meaning (prevents automatic generation, not access to safe prebuilt artwork); updating the directory never switches a player-selected generated image to an official default.

## Capabilities

### New Capabilities

- `official-art-resolution`: the extended deterministic presentation chain with the official-default step, the payload origin discriminator and official payload fields, fall-through over stale/absent official references, eligibility ordering, and the auto-generation suppression rule's observable side (an official-satisfied subject presents official artwork without a generated card).

### Modified Capabilities

- `art-gallery-resolution`: the ordered chain gains the official-default step before the terminal fallback seam (both the character and monster-variant wordings), and resolution payloads carry the origin discriminator beside the existing face-rect/stage carriage.
- `art-gallery-autogen`: the idempotency guard gains the official-satisfied condition — an automatic path requests nothing when eligible official artwork already satisfies the subject's content reference — while every existing guarantee stays unchanged.
- `webclient-art-panel`: portrait catalog entries carry the origin discriminator; a resolving official image is distinguishable from a runtime image and a placeholder.
- `webclient-character-roster`: roster rows carry the same origin-bearing portrait vocabulary the art panel catalog carries.

## Impact

- Code: `world/art/gallery_match.py` (chain), `world/art/presenter.py` (official payload branch, origin), `world/art/service.py` (auto-generation suppression guard), `web/static/webclient/js/elosern/protocol.js` + Python wire validators (art/roster portrait vocabularies), frontend portrait consumers rendering committed fields only.
- Contract gate for changed wire vocabularies; no database change; no gameplay/mechanics change; official presentation never mutates state or performs I/O beyond the snapshot.
