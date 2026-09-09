## Why

The gallery is supposed to be one system that serves every portrait subject,
with each subject kind differing only in how much of that system it is allowed
to use. The code does not say so anywhere. Instead the per-kind rules are
scattered as inline `if subject.kind is ArtSubjectKind.MONSTER` / `… is SCENE`
branches across `gallery.py`, `gallery_match.py`, `queue.py`, and
`gallery_seed.py`, and the only shared declaration — `GALLERY_KIND_DIRECTORIES` —
carries just the store directory. A reader cannot answer "what may a monster
gallery do?" from any single place, and a new kind added to `ArtSubjectKind`
would silently fall through every `.get()` on that dict rather than failing
loudly.

This blocks the monster work directly. Putting monsters on the shared generation
trunk means the request seam has to ask "does this kind take a field selection?
a binding? an age precondition?" — and the honest answer to that question is a
declaration, not another chain of kind comparisons bolted onto a
character-shaped function.

## What Changes

- New `world/art/gallery_kinds.py` declaring one frozen capability record per
  subject kind: whether the kind has a gallery at all, its store-path directory
  segment, the maximum number of cards it may hold, and whether it supports
  equipment bindings. `SCENE` is declared explicitly as "no gallery" rather than
  being an absence.
- The card maximum is nullable, and null means genuinely unbounded. The character
  kind is uncapped today and stays uncapped by declaring null — approximating "no
  cap" with a large sentinel would let the generalized replace-at-cap rule impose
  a silent character cap, which is exactly the regression this change must not
  introduce. Only null and `1` are admitted values, enforced by the contract test:
  no kind needs an intermediate cap, and admitting arbitrary values would demand
  an N-card eviction algorithm no real declaration exercises.
- The module is **dependency-neutral**, exactly like `world/art/fallback_keys.py`
  and for the same reason: it imports nothing and is keyed by the subject kind's
  string value. `world/art/subjects.py` imports `gallery_prompt`, so a capability
  table that imported `subjects` would close an import cycle the moment the
  prompt layer needs to consult it.
- Every existing gallery kind branch reads the declaration instead of naming a
  kind: the gallery-bearing guards in `record_for` / `validate_card` /
  `enqueue_gallery_job` / `resolve_card`, the monster one-card cap and unbound
  rule in `append_card`, the binding-step skip in `resolve_card`, and the cap
  handling in `gallery_seed`.
- `GALLERY_KIND_DIRECTORIES` is replaced by accessors derived from the table, so
  the store-path vocabulary has exactly one origin.
- A contract test asserts the table covers every `ArtSubjectKind` member
  exhaustively, so adding a kind without declaring its gallery capability fails
  at test time instead of degrading silently.
- **Behaviour-preserving.** Characters, monsters, and scenes behave exactly as
  they do today; no seam gains or loses a capability in this change. The
  request-precondition fields the monster work needs (field selection, free text,
  age check) are deliberately NOT declared here — they are added by the change
  that actually consumes them, so this table never carries a field nothing reads.

## Capabilities

### New Capabilities

- `art-gallery-kind-capabilities`: the closed per-kind gallery capability
  declaration, its exhaustiveness contract, and the rule that every gallery
  module reads kind rules from it rather than comparing kinds inline.

### Modified Capabilities

- `art-gallery-model`: the monster one-card cap and the unbound-monster rule are
  restated as consequences of the declaration rather than as monster-specific
  prose.
- `art-gallery-resolution`: the monster binding-step skip is restated as "the
  chain runs the binding steps only for a kind whose declaration supports
  bindings".
- `art-gallery-seed-sync`: seed cap enforcement reads the declared maximum
  instead of testing for the monster kind.

## Impact

- New `world/art/gallery_kinds.py` plus its contract test.
- `world/art/gallery.py` — `record_for`, `validate_card`, `append_card`, and the
  `GALLERY_KIND_DIRECTORIES` export.
- `world/art/gallery_match.py` — the gallery-bearing guard, the binding-step
  skip, and the identity prefix check.
- `world/art/queue.py` — `enqueue_gallery_job`'s scene refusal.
- `world/art/gallery_seed.py` — the cap handling and the reverse
  directory→kind map.
- `world/art/worker.py` — the gallery output-identity directory lookup.
- Import sites of `GALLERY_KIND_DIRECTORIES` move to the new accessors.
- No settings, no environment variables, no wire schema, no command surface, no
  frontend payload, and no observable behaviour change.
