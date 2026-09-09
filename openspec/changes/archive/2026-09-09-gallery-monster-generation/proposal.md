## Why

The gallery was designed as one system serving every portrait subject, with
monsters differing only by holding fewer capabilities — one card, no binding, a
registry-driven description. The decomposition delivered the monster half of the
*model* (the kind directory, the one-card cap, the unbound rule, the
`monster_anon` fallback) but never opened the *generation* trunk to it:
`world/art/service.py::request_gallery_image` derives its subject through
`character_subject_for` and so raises for anything else. A monster gallery card
can therefore only come from seed synchronization.

The main specs already promise otherwise. `art-staff-commands` states that a
requeued monster subject's "gallery request SHALL respect the one-card cap", but
`commands/art.py::CmdArtRequeue` routes monsters to the classic `requeue()` — the
spec and the code disagree today.

This change opens the trunk and makes `@art requeue portrait:monster:<tier>` do
what its spec already says. Routing the *automatic* monster paths through it is
the follow-on change `gallery-monster-autogen`.

## What Changes

- `request_gallery_image` becomes the seam the design declared: it accepts a
  character entity or a monster subject (`entity_or_subject`) and derives the
  subject from either. It is not a character function taught to tolerate
  monsters — the preconditions it enforces are read from the subject kind's
  capability declaration, so the trunk is kind-driven and each kind contributes
  only what it declares.
- The capability declaration from `gallery-kind-capabilities` gains the three
  request-precondition fields this change consumes, and only now that it
  consumes them: whether the kind requires the canonical-age precondition,
  whether it supports a prompt field selection, and whether it supports free
  text. The character declares all three; the monster declares none.
- A request naming a capability its kind does not declare — a field selection, a
  custom prompt, or a binding for the monster kind — is a typed rejection at the
  seam, before any render or write. Silently ignoring an argument the kind cannot
  honour would make the card's `requested_fields` provenance a lie.
- The prompt field catalog is scoped to the kinds that declare field support, so
  `appearance` and the equipment slots remain a character vocabulary and a
  monster request cannot name one.
- `@art requeue <monster key>` issues one gallery generation request honouring
  the declared one-card cap, closing the existing spec/code divergence. The
  classic reset stays for scene keys only.
- `requeue_character_portrait` is generalized and renamed to a kind-neutral name;
  `commands/art.py::CmdArtRequeue`, its only caller, is updated in this change.
  The retry seam was already renamed by `gallery-failure-visibility`, so this
  change generalizes its internals without touching `CmdArtRetry`.

## Capabilities

### New Capabilities

None. This change puts the monster portrait kind onto capabilities that already
exist.

### Modified Capabilities

- `art-gallery-kind-capabilities`: the declaration gains the age-precondition,
  field-selection, and free-text capability fields.
- `art-gallery-generation`: the request seam serves every gallery-bearing kind
  and enforces per-kind preconditions from the declaration.
- `art-gallery-prompt-fields`: the catalog applies only to kinds that declare
  field support.
- `art-staff-commands`: `@art requeue` routes a monster subject to the gallery.

## Impact

- `world/art/service.py` — `request_gallery_image`, `requeue_character_portrait`
  (generalized and renamed), and the retry seam's internals.
- `world/art/gallery_kinds.py` — three added capability fields.
- `world/art/gallery_prompt.py` — catalog validation scoped by declared capability.
- `commands/art.py` — `CmdArtRequeue` only. `CmdArtRetry` needs no code change:
  `gallery-failure-visibility` already gave it a kind-neutral gallery arm that
  iterates gallery records rather than kinds, and already renamed the seam it
  calls.
- Tests under `world/art/tests/` and `commands/tests/test_art.py`.
- No settings, no environment variables, no wire schema, no frontend payload, and
  no new player-facing command (design D14).

## Sequencing note

This change depends on **both** `gallery-kind-capabilities` (it extends that
change's declaration and reads it in the seam) and `gallery-failure-visibility`
(which renames the retry seam and owns the current shape of `commands/art.py`).
Land it third of four. `gallery-monster-autogen` lands after it.
