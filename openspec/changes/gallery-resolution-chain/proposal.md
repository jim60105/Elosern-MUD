## Why

Cards exist but nothing reads them. `world/art/presenter.py::resolve_entity`
still resolves exactly one `ArtAssetRecord` per subject, so a gallery of ten
images shows the same picture as a gallery of one, an equipment change never
swaps the portrait, and every avatar surface crops a 3:4 portrait with a blind
centre anchor that only statistically keeps the face in frame.

This change makes the gallery *visible*: one deterministic resolution chain, one
media route that can serve a card's file, and one normalized face rectangle
travelling with every resolved image so a 1:1 avatar frame can offset to the
face instead of guessing.

## What Changes

- New `world/art/gallery_match.py`: the deterministic chain — compute the stored
  four-slot equipment snapshot; keep cards whose binding masks all match it; most
  masked slots wins; tie broken by newest `created_at`; else the subject's
  `default_image_id`; else the existing classic `done` asset record; else the
  fallback seam; else today's truthful placeholder.
- An unbound card is never auto-selected: with no mask match and no default set,
  the chain falls through even when unbound cards exist, so no image the player
  did not choose appears by surprise.
- Monster subjects resolve through the same chain minus the binding steps.
- New terminal fallback seam `fallback_for(subject)`, returning `None` in this
  change. `gallery-builtin-fallbacks` fills it in without touching this chain.
- The classic asset record stays in the chain as the step *after* the default, so
  monsters, scenes, and any not-yet-migrated portrait keep resolving exactly as
  they do today. **Refinement of design §11**, which sketched "new resolution
  reads only galleries": keeping the classic step buys a zero-migration
  transition for one extra, strictly-lower-priority chain step.
- `resolve_subject` / `resolve_character` / `resolve_entity` payloads gain
  `face_rect`: the resolved card's rectangle when a URL is present, `null` for
  every placeholder.
- `web/art_media.py` serves `gallery/<kind>/<subject-key>/<image-id>.<ext>`,
  admitted only when the record addressed by the identity's own path segments
  holds a card with exactly that identity — a direct record lookup, not a scan.
- `web/art_media.py` also gains a `defaults/<key>.<ext>` branch serving one fixed in-repo
  directory, so `/art/...` stays the single media URL vocabulary the wire accepts once
  `gallery-builtin-fallbacks` supplies images. **Refinement of design §7.2**, which sketched
  serving the built-in set as raw static assets: routing them keeps one URL grammar, one
  confinement discipline, and one wire rule.
- The `art` panel catalog and the `roster` rows carry `face_rect` through their
  exact-field wire validators. The addition is purely additive for the live Vue
  client under `web/webclient-app/`, which reads catalog and roster entries by key
  (`entry.url`, `entry.placeholder`, `entry.context`) and ignores keys it does not
  use; it performs no `schema_version` check. The seven avatar surfaces that crop
  with `object-fit: cover` today are the eventual D9 consumers, but this change
  only makes the rectangle available to them — consuming it stays a TODO for the
  Vue rewrite (D12).

**Open follow-up, not covered by any of these seven changes.** Design §6 says the
avatar surfaces should CSS-offset by the rectangle, replacing today's blind
centre crop. Five live components (`ParticipantFrame`, `CharacterSwitcher`,
`PartyStrip`, `PartyDrawer`, `NarrativeFeed`) plus `ArtPanel` still crop with
`object-fit: cover`. D12 deferred all frontend work while the Vue rewrite is in
flight, and that decision stands here — but the consequence is that `face_rect`
ships with no live consumer until a separate frontend change wires it.

No backward compatibility or data migration.

## Capabilities

### New Capabilities

- `art-gallery-resolution`: the deterministic display-resolution chain, the
  unbound-card rule, the monster variant, the terminal fallback seam, and the
  `face_rect` contract on every resolution payload.

### Modified Capabilities

- `art-queue-worker`: the media-serving requirement admits card-referenced
  gallery identities under the same confinement rules, resolved by direct record
  lookup.
- `webclient-art-panel`: each portrait catalog entry additionally carries the
  resolved face rectangle, null for placeholders.
- `webclient-character-roster`: each roster row's portrait vocabulary gains the
  same face rectangle.

## Impact

- `world/art/gallery_match.py` — new module: snapshot matching and the chain.
- `world/art/presenter.py` — chain integration, `face_rect` in every payload,
  gallery URL building from validated card identities.
- `web/art_media.py` — gallery identity pattern and card-reference check.
- `web/webclient/presentation/art.py`, `web/webclient/presentation/roster.py` —
  `face_rect` serialization and exact-field wire validation.
- `world/art/tests/`, `web/webclient/presentation/tests/` — chain, route, and
  payload coverage; new presentation test modules registered in
  `.github/evennia-shards.json` in this change.
- `web/webclient-app/stories/fixtures.js` and the two JS suites carrying a
  `portrait_catalog` fixture — updated so the fixtures stay representative of the
  payload; the Vitest and Storybook gates are re-run even though no component
  changes.
- Unaffected: the queue, the worker, the SD client, generation, the gallery write
  API, and every player-facing command.
