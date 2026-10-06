## Context

See proposal.md for motivation. `dream-explicit-presentation` is an existing
capability resting on three seams that already existed before `f09feb1e`: the
server-authored dream surface (`world/narrative/dream_surface.py`), the pure
read-model arousal track (`world/narrative/dream_track.py`), and the external
official-artwork system (`world/art/official.py` plus the `/art/official/`
branch of `web/art_media.py`). The dream panel's wire version is mirrored across
four sites pinned by the repository's panel schema-version parity contract
(`tests/test_panel_schema_version_parity_contract.py`).

This is a backfill: every decision below is one that **shipped** in `f09feb1e`,
not an option still under consideration.

## Goals / Non-Goals

**Goals:**
- Document the shipped dream-stage retheme and its externally served artwork as
  the design of record.
- Record the panel wire-schema v1 → v2 bump, the new `scene_art` field, and the
  four mirrored version sites.

**Non-Goals:**
- No new behavior, no refactor, no compatibility layer — the code is already
  shipped and this backfill changes no source file.
- Not the official-artwork catalog itself (owned by `official-artwork-catalog`),
  not the other panels' schemas, not the player's live sexual state.

## Decisions

- **Stage artwork is an external official asset, never a git-bundled client
  import.** The scene identity is the closed constant pair
  `DREAM_GODDESS_NPC_KEY = "dream_goddess"` /
  `DREAM_GODDESS_SCENE_IDENTITY = "npc/dream_goddess/dream-throne.webp"`, written in
  the official catalog's `npc/<key>/<file>` layout; `scene_art_url()` resolves it at
  present time through `official.current_catalog().url_for(...)` into the
  same-origin `/art/official/<fingerprint>/<path>` URL, and returns `""` when the
  startup snapshot does not admit the identity. Alternatives considered: keeping the
  bundled `dream-white-bed.avif` import (rejected — official artwork is too large for
  git and must ship under its own license outside the repository) and copying official
  bytes into the runtime store (rejected — the catalog resolves in place, read-only,
  from its startup snapshot).
- **An absent official root is a valid no-art configuration.** With no catalog
  snapshot the URL is empty, the panel renders no `<img>`, and the rethemed prose
  stands on its own. This is the same degradation every other missing-official-art
  case uses, so the dream stage invents no second absence policy.
- **The bundled asset and its gallery pin are removed together.**
  `web/webclient-app/assets/redesign/dream-white-bed.avif` is deleted and its entry
  is dropped from `APPROVED_NON_RUNTIME_IMAGES` in
  `world/art/tests/test_gallery_fallback.py`, keeping the closed
  non-runtime-image set exactly equal to the tracked tree.
- **Dream panel wire schema v1 → v2 adds one bounded field, mirrored four ways.**
  v2 adds `scene_art` (the server-resolved official-media URL, `""` when absent).
  The four sites that must agree are: (a) `DREAM_SCHEMA_VERSION = 2` in
  `web/webclient/presentation/dream.py`; (b) the registry registration in
  `web/webclient/presentation/registry.py`, which references
  `schema_version=DREAM_SCHEMA_VERSION` by identifier, so it follows the constant
  with no literal to bump; (c) `PANEL_ALLOWLIST.dream: 2` in
  `web/static/webclient/js/elosern/protocol/constants.js`; and (d) the client
  available-form re-check `payload.schema_version !== 2` in
  `web/static/webclient/js/elosern/protocol/panels/dream.js`. The client validator
  adds `scene_art` to its exact-field list and bounds it as a string of at most 256
  characters via `MAX_SCENE_ART_URL`, mirroring
  `world.art.presenter.MAX_PORTRAIT_MEDIA_URL` — the one existing shared wire
  ceiling for server-authored media URLs. Alternatives: bumping only the presenter
  constant (rejected — the parity contract and the client would reject v2 payloads)
  and selecting a fresh per-field cap (rejected — a second wire ceiling would drift
  from the shared one).
- **The arousal counter is re-owned to the goddess counterpart, mechanically
  unchanged.** The `dream_track.py` module docstring now owns the deterministic,
  session-only pleasure/arousal/climax track to the dream's goddess counterpart and
  states that her climax (reached at the six-exchange convergence) ends the dream and
  the player's live sexual state is never involved. Deltas, the canonical five bands,
  and `TRACK_VERSION` are unchanged, no live `SexualState` handler is written, and
  the existing requirement's "no live character effects" contract is untouched.
  Alternative: rebalancing the track alongside the retheme (rejected — player-visible
  pacing is a separate, still-valid contract; the retheme is wording and framing
  only).
- **Opening/ending prose and the system prompt are rethemed, prompt structure
  unchanged.** `OPENING` and the two ending strings in `dream_surface.py` describe
  the cloud-throne staging and the goddess's climax; `prompts/dream.yaml` keeps
  `schema_version: 1`, the exact three-field JSON contract (`scene`/`dialogue`/
  `phase`), the approved-explicit-vocabulary mandate, and the rule that the
  server-supplied arousal phase stays authoritative — only the staged scene
  description changed. Alternative: a new prompt schema version (rejected — the
  response contract and its validator are unchanged, so a version bump would be a
  compatibility claim with nothing behind it).

## Risks / Trade-offs

- [Artwork absent from the operator's official directory] → a valid no-art
  configuration: `scene_art` is `""`, the panel's `v-if` drops the `<img>`, and the
  prose carries the scene. Proven by the catalog-resolution test with an empty
  snapshot.
- [A client stuck on schema v1 rejects the v2 payload] → the client mirror ships in
  the same commit (allowlist entry plus validator re-check), so server and client
  bump together and no released client speaks v1.
- [The rethemed prompt drifts from the server-supplied phase] → the prompt states
  the server phase is authoritative and the generated response is validated against
  the track; the shipped guardrail and track tests are unchanged.
- [Deleting a tracked image breaks the closed non-runtime-image contract] → the same
  commit removes its one allowlist entry, so the set stays exact.

## Migration Plan

None. The behavior is already deployed as `f09feb1e`: no stored record, wire
migration, or data rewrite, and no compatibility layer. Rollback is reverting that
commit.

## Open Questions

None — the behavior is already shipped and fixed.
