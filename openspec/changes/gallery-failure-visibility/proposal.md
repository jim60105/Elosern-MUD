## Why

`art-gallery-generation` already requires a failed gallery settle to record its
bounded error code on the subject's `GalleryRecord` "so an operator surface can
report it". No such surface exists: nothing in production reads
`GalleryRecord.last_error_code`, `world/art/gallery.py::clear_error` has no
caller at all, and `settle_gallery_generated` never clears a prior error — so a
subject that failed once carries a stale code forever and no operator can see it.

The recovery path is broken in the same place. `queue.failed_keys()` excludes
gallery jobs by contract, and since `gallery-autogen-retrofit` a character
subject never writes a classic asset record, so `failed_keys()` can no longer
yield a character subject on a fresh database. `CmdArtRetry`'s character branch
is therefore unreachable in production; the test that covers it manufactures a
classic character record through `queue.ensure`, a state the production code can
no longer produce. Today a failed portrait is recoverable only by restarting the
server (the startup recovery scan re-fires because the gallery is empty and no
job is in flight) or by an operator who already knows the exact subject key and
runs `@art requeue`.

## What Changes

- A successful gallery settle SHALL clear the subject's recorded generation
  error, so the field means "the last generation failed", not "a generation
  failed once".
- `world/art/gallery.py` gains one read-only cross-record accessor reporting the
  subjects whose gallery carries an error, alongside the existing
  `referenced_stored_identities` accessor — the single-writer rule keeps the
  record class inside that module, so every cross-record read goes through an
  accessor.
- `@art status` gains a gallery section: one line per gallery record with its
  subject key, card count, whether a default is set, and the recorded error code
  with its age. The existing kind filter applies to it. Gallery **job** records
  stay invisible exactly as today — this reports gallery *state*, not queue rows.
- `@art health` gains exact gallery counts: records, cards, and subjects
  currently carrying an error.
- `@art retry` re-drives every subject whose gallery carries a recorded error
  through the gallery request seam, and its unreachable classic-character branch
  is **REMOVED**. Classic scene records keep their existing re-enqueue behaviour.
- When the seam declines an erroring subject because its gallery is no longer
  empty — a seed card arrived, or an operator kept an image — the recorded error
  is moot and SHALL be cleared. Without this the error can never clear (the
  automatic guard suppresses the only path that would have cleared it) and
  becomes permanent noise on the new status surface.
- `world/art/service.py::retry_character_portrait` is **RENAMED** to a
  kind-neutral name. This change establishes the command's only caller of that
  seam, and `gallery-monster-generation` later generalizes its internals to serve
  every gallery-bearing kind; doing the rename here, where `CmdArtRetry` is
  already being rewritten, keeps that later change free of call-site churn.
- No player-facing surface is added and no new command is introduced (design
  D14); `docs/game/commands.md` is untouched.

## Capabilities

### New Capabilities

None. This change closes the operator half of contracts that
`art-gallery-generation` and `art-staff-commands` already state.

### Modified Capabilities

- `art-gallery-model`: the recorded generation error gains a lifecycle — cleared
  on the next successful append — and one read-only accessor enumerating the
  subjects that carry one.
- `art-gallery-generation`: the failed-settle requirement's promised operator
  surface is named, and a successful settle SHALL clear the recorded error.
- `art-staff-commands`: `@art status`, `@art health`, and `@art retry` gain their
  gallery arms; `@art retry`'s classic-character branch is removed.

## Impact

- `world/art/gallery.py` — clear-on-success call site's public API and the new
  read-only accessor.
- `world/art/queue.py` — `settle_gallery_generated` clears the error after the
  card append commits, inside the existing `queue_lock -> gallery_lock` order.
- `commands/art.py` — `CmdArtStatus`, `CmdArtHealth`, `CmdArtRetry`.
- `world/art/service.py` — `retry_character_portrait` renamed; the moot-error
  clear on a declined retry.
- Tests under `world/art/tests/` and `commands/tests/test_art.py`; the existing
  `test_retry_skips_a_character_portrait_with_a_non_integer_age` test is rewritten
  against the gallery path it now exercises, and
  `world/art/tests/test_service.py`'s references to the renamed seam are updated.
- No settings, no environment variables, no wire schema, no frontend payload.
