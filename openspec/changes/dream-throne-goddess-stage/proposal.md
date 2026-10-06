## Why

The dream stage was rethemed and re-plumbed in commit `f09feb1e` — a white throne
on a sea of clouds, an obscured goddess counterpart who pleases herself while
negotiating, and stage artwork served from the external official-artwork system
instead of a git-bundled client asset — but that work landed with no OpenSpec
record. This change backfills the missing artifacts so the shipped behavior has a
proposal, design, delta spec, and task list and can be archived like every other
change.

**This is a retroactive backfill of already-shipped behavior.** No new code is
written by this change, and `openspec/specs/dream-explicit-presentation/spec.md`
already reflects the contract restated below: the delta's two MODIFIED
requirement bodies are byte-identical to the current main spec, so the archive
sync is content-neutral.

## What Changes

- Record the shipped dream-stage retheme as a `dream-explicit-presentation` delta:
  the collaborator inhabits a white throne standing on a sea of clouds, an
  obscured goddess-like counterpart of stable persona pleasures herself while
  speaking with the player, her exaggerated well-used genitals spurt visibly, and
  the ankle-deep flood across the floor is recognized as her fluids.
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
- No production, test, or web source changes: the implementation already shipped
  as `f09feb1e` and is documented here.

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
- `openspec/specs/dream-explicit-presentation/spec.md` was updated in place by that
  same commit; this change adds no further edit to `openspec/specs/**`.
- Operator side, gitignored and **not** part of the commit:
  `art-official/npc/dream_goddess/dream-throne.webp`, the external
  `npc/<key>/<file>` official-artwork layout served same-origin through
  `/art/official/<fingerprint>/<path>`.
- No runtime behavior change from this backfill: no wire, storage, or dependency
  change beyond what already shipped.
