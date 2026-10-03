## Why

Canvas-filling portraits make a child and an adult equally tall on the cinematic stage. Players need a manual per-card presentation correction, including offsets for off-center figures, without changing the source image or avatar crop.

## What Changes

- Add a twelfth card field, `stage = {scale, x, y}`, validated and atomically stored through `world/art/gallery.py::set_stage`; tolerant reads supply identity for missing or malformed stored stage values without migration.
- Register `gallery.stage.update`, accepting one exact subject/card/triple payload and reusing gallery resolution, rejection, observability, idempotency, and affected-panel publication.
- **BREAKING**: Add `stage` to the exact gallery-row and resolved-art wire shapes; update Python, dependency-free Node, dialogue/stage, roster consumers and fixtures together in one deployable, with no schema-version bump or compatibility layer.
- Apply stage-only bottom-center scaling and frame-relative offsets in `ReferenceArtwork`; move the drawer full-figure art slot to that branch while leaving every face-rect cover crop unchanged.
- Add the 比例調整 rail control and a dedicated local-preview modal with synchronized range/number controls, drag offsets, reset, and a static CSS-mask adult reference using the existing `/art/defaults/man.webp` asset.
- Extend substantive Python/Node/Vitest coverage, requirement traceability, shard registration, Storybook stories and component-manifest coverage alongside implementation.

## Capabilities

### New Capabilities

None. This extends existing gallery and art capabilities.

### Modified Capabilities

- `art-gallery-model`: twelve-key card contract, bounded stage triple, tolerant read identity and sole-writer atomic seam.
- `webclient-gallery-management-actions`: seventh exact management action and its existing publication/error/event discipline.
- `webclient-gallery-panel`: stage-bearing real rows and null synthetic rows, mirrored without new chips or version change.
- `webclient-art-panel`: stage-bearing resolved portrait/scene payloads, degradation defaults and unchanged placeholder semantics.
- `webclient-gallery-ui`: local transform editor, full-figure rendering, accessibility and offline storyboard extension.

## Impact

One cohesive engineer-day change, not a batch: backend persistence/action/wire and browser rendering/editor must land together because exact-field validators reject partial deployment. Implementation touches the art gallery/presenter, gallery actions and registration, presentation validators and actor portrait production, mirrored Node protocol validators, Vue gallery components/helpers and drawer art usage, tests/fixtures, `.github/evennia-shards.json`, Storybook/manifest and owning specifications. No new asset, route, package, player command, money representation, AI prompt, rules behavior, migration or compatibility layer. `docs/game/commands.md` remains untouched.

Authoritative approved scope: `docs/superpowers/specs/2026-10-03-gallery-stage-transform-design.md` (D1–D7 and §§3–9). Visual grounding: existing gallery chrome, face editor, shared DrawerHeader, AVG redesign A10/A11 and `docs/design/elosern-redesign2/gallery-storyboard.md`.
