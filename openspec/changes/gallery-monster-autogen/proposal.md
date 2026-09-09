## Why

`gallery-monster-generation` opens the shared generation trunk to monster
subjects, so a staff `@art requeue portrait:monster:<tier>` produces a gallery
card. The automatic path is still on the classic pipeline:
`world/art/service.py::_sync_registry_subjects` routes every
`MONSTER_TIER_REGISTRY` entry through the classic `queue_ensure`, so a fresh
database still gives every monster tier a classic fixed-identity asset record and
no gallery card. The generic monster kind is the last portrait subject that still
writes one — design D8 and §4.3 put it on the gallery.

Leaving it here would also mean the two halves disagree: an operator-forced
regeneration lands in the gallery while startup keeps producing a classic record
for the same subject, and the display chain would resolve whichever happened last.

## What Changes

- Generic-monster startup synchronization routes through the gallery generation
  request under the same automatic-generation guard every character path uses —
  gallery-empty AND no job in flight — rather than through a monster-specific
  loop.
- The classic monster asset record is **REMOVED** from the startup sync's writes.
  Scenes keep theirs unchanged; the scene kind becomes the only classic-record
  producer.
- Pre-existing classic monster records are left in place: not deleted, not reset.
  They keep resolving through the display chain's classic step and stay visible in
  `@art status`, so nothing needs migrating (there are no released users).
- The automatic-ensure helper in `service.py` is generalized so one function
  serves every gallery-bearing kind. The character's canonical-age check becomes
  one declared precondition inside it rather than a hardcoded step, so the
  helper's name and body stop being character-specific.
- Every monster failure stays bounded: a failing tier never aborts startup and the
  remaining tiers still synchronize.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-gallery-autogen`: automatic portraits cover the monster kind, and the
  requirement is stated per declared capability rather than per character path.
- `art-asset-lifecycle`: startup synchronization stops writing classic
  generic-monster asset records and routes those subjects to the gallery.

## Impact

- `world/art/service.py` — the shared automatic-ensure helper and
  `_sync_registry_subjects`.
- Tests under `world/art/tests/`, including startup-sync fixtures and
  idempotency-across-restarts coverage.
- `docs/superpowers/specs/2026-09-08-character-gallery-art-design.md` §12 — record
  that monster generation reached the gallery and retire the recorded gap.
- No settings, no environment variables, no wire schema, no command surface, no
  frontend payload.

## Sequencing note

Lands last of four, after `gallery-monster-generation`: the seam it routes
startup through does not accept a monster subject until that change lands. It
touches only `world/art/service.py`, so it conflicts with nothing else once that
predecessor is in.
