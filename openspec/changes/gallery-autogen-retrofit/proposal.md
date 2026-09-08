## Why

Everything a gallery needs now exists except the thing that fills it on its own.
Today the ensure seams — player creation, validated import, named-NPC spawn, and
startup recovery — still produce one fixed-identity `portrait/character/<key>.<ext>`
asset that the resolution chain reaches only as a lower-priority fallback. That
leaves two parallel portrait mechanisms for the same character, and a newly
created character whose only image is one the player can neither replace nor keep
alongside another.

This change retires the classic character-portrait output in favour of the
gallery, keeping every existing eligibility, atomicity, and failure-isolation
guarantee exactly as specified.

## What Changes

- `schedule_portrait_ensure` and `schedule_occupant_portrait` keep their shape —
  the canonical-age check at schedule time, the `transaction.on_commit`
  registration, the total failure isolation — and route through
  `request_gallery_image` instead of the subject-keyed `ensure`.
- The auto-generated image is one **unbound** card built from the subject's
  standard deterministic description (the authored appearance block and nothing
  else), with no free text and the shared default face rectangle. It does not
  depend on the gallery prompt field catalog: it requests exactly the description
  the seams produce today. Unbound means
  the resolution chain shows it only as the subject's default — which, being the
  first card, it becomes automatically.
- Auto-generation becomes gallery-idempotent: a subject whose gallery already
  holds a card, or whose generation is already in flight, is left alone. This
  preserves the existing "two quests sharing a stable key produce one image" rule
  and keeps startup recovery from stacking duplicates across restarts.
- `finalize_player_portrait` gains an explicit skip flag (default: generate).
  Skipping establishes the portrait policy as usual and simply starts the
  character with an empty gallery, which resolves through the fallback chain.
- `@art requeue <portrait:character:...>` issues a gallery generation request
  instead of resetting a classic record, and `@art retry` naturally stops seeing
  character subjects because they no longer own classic records.
- Character subjects stop producing classic asset records. Existing
  `portrait/character/*` files stay readable through the chain's classic step
  until they are deleted; nothing migrates them and nothing needs to.
- Scenes and monster tiers are untouched by this change: they keep the classic
  single-asset pipeline exactly as specified today.

No backward compatibility or data migration: no released users; existing
fixed-identity portraits remain resolvable through the chain's classic step.

## Capabilities

### New Capabilities

- `art-gallery-autogen`: the retrofitted auto-generation contract — one unbound,
  appearance-only, shared-rectangle card per subject; gallery-based idempotency;
  and the player-creation skip flag.

### Modified Capabilities

- `art-asset-lifecycle`: startup recovery is satisfied by the subject's gallery
  rather than by a classic record, and requests only for an empty gallery with no
  in-flight job.
- `spawn-named-portraits`: a completed spawn job publishes exactly one unbound
  gallery card carrying the shared default rectangle, and a shared stable key
  resolves to one gallery holding one auto-generated card.
- `art-staff-commands`: `@art requeue` on a character subject issues a gallery
  generation request instead of resetting a fixed-identity record, and creates no
  classic record for a character subject.

## Impact

- `world/art/service.py` — `_ensure_character_portrait`, the recovery scan,
  `retry_character_portrait`, and `requeue_character_portrait` route to the
  gallery; the classic character path is removed.
- `world/rules/character_creation.py::finalize_player_portrait` — the skip flag.
- `world/rules/starting_companions.py`, `world/imports/loader.py`,
  `world/quests/scene_builder.py` — call sites verified, unchanged in shape.
- `commands/art.py` — the character branch of `@art requeue`.
- `world/art/tests/`, `world/rules/tests/`, `commands/tests/` — retrofit coverage.

**Sequencing note.** This change and `gallery-prompt-composition` both edit
`world/art/service.py::_ensure_character_portrait` and the recovery scan. Land
this one FIRST: it rewrites those functions to call the gallery seam, and
`gallery-prompt-composition` then makes their field selection explicit. Running
the two in parallel is a guaranteed rewrite conflict in the same functions.
- Unaffected: the scene pipeline, the monster tier pipeline, the queue and worker
  contracts, the resolution chain, the seed sync, the fallback set, and every
  player-facing command.
