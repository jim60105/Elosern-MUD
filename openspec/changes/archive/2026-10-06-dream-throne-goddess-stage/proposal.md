## Why

The dream stage was rethemed and re-plumbed in commit `f09feb1e` — a white throne
on a sea of clouds, an obscured goddess counterpart who pleases herself while
negotiating, and stage artwork served from the external official-artwork system
instead of a git-bundled client asset — but that work landed with no OpenSpec
record. This change backfills the missing artifacts so the shipped behavior has a
proposal, design, delta spec, and task list and can be archived like every other
change.

**This is a retroactive backfill of already-shipped behavior.**
`openspec/specs/dream-explicit-presentation/spec.md` already reflects the
contract restated below: the delta's two MODIFIED requirement bodies are
byte-identical to the current main spec, so the archive sync is content-neutral.
One bounded review round followed the implementation (a `rubber-duck` critique of
`f09feb1e`, no blocking findings): its adopted follow-ups — the panel's
failed-artwork fallback, the catalog-admissibility tripwire test, the corrected
requirement wording, and the documentation corrections — are part of this change
and are listed under What Changes.

Because the delta restates two requirement blocks the implementation commit already
applied in place, the archive sync rewrites those two blocks with identical text —
archive before any further edit to them. The commit's third spec change, the
`dream-explicit-presentation` Purpose sentence re-owning the arousal track to the
goddess counterpart, is already in the main spec and cannot be expressed by a delta,
so it is recorded here in prose only.

## What Changes

- Record the shipped dream-stage retheme as a `dream-explicit-presentation` delta:
  an obscured goddess-like counterpart of stable persona sits on a white throne
  standing on a sea of clouds and pleasures herself while speaking with the player
  who stands in the ankle-deep flood of her own fluids, her exaggerated well-used
  genitals spurting visibly, and that flood is recognized as hers.
- Record that the dream stage's artwork is served from the external
  official-artwork system as a server-resolved same-origin URL
  (`npc/dream_goddess/dream-throne.webp`), never bundled into the client, and
  degrades to no artwork when the official catalog does not admit the identity.
- Record the server-owned arousal track as the **goddess counterpart's** (not the
  player's): unchanged deltas, unchanged canonical five bands, unchanged
  `TRACK_VERSION`, her climax ends the dream, and no live `SexualState` is ever
  written.
- Record the dream panel wire schema bump v1 → v2 adding the bounded `scene_art`
  field, mirrored across the presenter constant, the registry registration, the
  UMD `PANEL_ALLOWLIST`, and the client available-form re-check.
- Record the review round's adopted follow-ups: the dream panel degrades to the
  flat stage when the artwork URL fails to load (a withdrawn or replaced file
  404s by design because the URL embeds the startup fingerprint); a tripwire test
  pins the artwork identity to the catalog's admitted kinds, stable-key contract,
  and stored extensions; the `dream-explicit-presentation` requirement prose now
  names the shipped staging (the counterpart seated on the throne, the player
  standing in her flood); and the developer/operator documentation describes the
  external artwork instead of the deleted bundled AVIF.
- No further production behavior beyond `f09feb1e` plus that review follow-up.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `dream-explicit-presentation`: two requirements are restated to match the
  shipped contract — `Dream collaboration uses the approved explicit frame`
  (cloud-throne goddess staging plus externally served scene artwork) and
  `Server-owned dream arousal advances only with completed exchanges` (the
  counter is the goddess counterpart's, not the player's).

## Impact

- Implementation, already committed as `f09feb1e`: `world/narrative/dream_surface.py`,
  `world/narrative/dream_track.py`, `prompts/dream.yaml`,
  `web/webclient/presentation/dream.py`,
  `web/static/webclient/js/elosern/protocol/constants.js`,
  `web/static/webclient/js/elosern/protocol/panels/dream.js`,
  `web/webclient-app/components/DreamPanel.vue`, the vitest/Storybook fixtures, the
  gallery-fallback pin, and the deletion of
  `web/webclient-app/assets/redesign/dream-white-bed.avif`.
- Review follow-up commit: `web/webclient-app/components/DreamPanel.vue` (failed
  artwork falls back to the flat stage), `world/narrative/dream_surface.py` (the
  identity's fixed-URL commentary), `world/narrative/tests/test_dream_surface.py`
  (the admissibility tripwire), `world/ai/tests/test_dream_presentation.py`
  (re-themed synthetic fixture), `web/webclient-app/tests/dream.test.js` (the
  failed-load vitest case), `docs/development/narrative-memory-and-recall.md`,
  `docs/development/official-artwork-deployment.md`, and the requirement-body
  rewording in both the main spec and this change's delta.
- `openspec/specs/dream-explicit-presentation/spec.md` was updated in place by that
  same commit, and the review follow-up reworded the first requirement body there
  and in this change's delta in the same form, so the delta stays byte-identical to
  the main spec and the archive sync remains content-neutral.
- Operator side, gitignored and **not** part of the commit:
  `art-official/npc/dream_goddess/dream-throne.webp`, the external
  `npc/<key>/<file>` official-artwork layout served same-origin through
  `/art/official/<fingerprint>/<path>`.
- No runtime behavior change from this backfill: no wire, storage, or dependency
  change beyond what already shipped.
