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
- No new feature, no refactor, no compatibility layer — the code shipped in
  `f09feb1e`, and the only source edits this change adds are the bounded review
  follow-ups recorded below.
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
  stands on its own. The dream stage reuses the catalog's own no-art rule — never
  invent a URL — so it introduces no second absence policy; its observable outcome
  is `""` and no `<img>`, whereas the art presenter keeps a URL and falls through to
  a silhouette/placeholder payload.
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
  characters through a module-local `MAX_SCENE_ART_URL = 256`, whose value mirrors
  the shared server-authored media ceiling
  `world.art.presenter.MAX_PORTRAIT_MEDIA_URL` (numerically equal to the protocol
  bundle's exported `MAX_MEDIA_URL`); the dream validator declares its own copy
  rather than importing that constant, so the mirror holds by value. Alternative:
  bumping only the presenter constant (rejected — the parity contract and the client
  available-form re-check would reject every v2 payload).
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
- [`scene_art` is bounded by UTF-16 code units and gets no same-origin prefix check,
  unlike the sibling URL fields] → accepted as shipped: the identity is a module
  constant, so the URL is ASCII and fixed-length
  (`/art/official/<64 hex>/npc/dream_goddess/dream-throne.webp`, well inside every
  ceiling) and always same-origin; a data-driven identity would need the sibling
  `requireString`/`/art/` prefix discipline first.
- [Documentation still described the pre-retheme staging] → fixed in the review
  follow-up: `docs/development/narrative-memory-and-recall.md` now describes the
  externally served stage artwork (and the text client's prose-only view), and
  `docs/development/official-artwork-deployment.md` names the dream identity and the
  verification step that proves it indexed.

## Review Round

An independent `rubber-duck` critique of `f09feb1e` (whole-implementation review,
self-contained request) returned **no blocking findings** and one implementation
consequence plus five non-blocking items. Dispositions:

- **Adopted — failed artwork must not leave a broken image.** The stage URL embeds
  the startup fingerprint of the file bytes, so replacing or withdrawing the file
  404s by design; `DreamPanel.vue` now drops the `<img>` on a load error (falling back
  to the flat stage) and retries only when the published URL changes, covered by the
  vitest case.
- **Adopted — a committed tripwire for the artwork identity.** Admission is silent
  (a refused or unindexed identity simply yields `""`), and the deferred authored
  npc/profile provenance will give the `npc` kind a registry-membership check that
  `dream_goddess` would fail. A test now asserts the identity parses as
  `<kind>/<key>/<file>` with an admitted kind, a valid stable subject key, and a
  stored extension.
- **Adopted — requirement prose accuracy.** The first requirement said the
  collaborator "inhabits a white throne"; it now states the shipped staging (the
  counterpart seated on the throne, the player standing in her flood). The change's
  delta and the main spec were reworded in the same form so the archive sync stays
  content-neutral.
- **Rejected — a server-side `/art/official/` prefix + ceiling re-check in
  `scene_art_url()`.** The value can only be the catalog's own URL or `""`, and the
  proposed guard would import the heavy `world.art.presenter` → Evennia gallery chain
  into a pure narrative read model to defend an unreachable case; the fixed ASCII
  identity and its 114-character URL are documented at the constant instead, with the
  client bound recorded as deliberately inert.
- **Deferred — an ops note that a schema bump strands a stale browser tab.** The
  property is inherent to every panel bump, the project is pre-release with no
  released clients, and the reload requirement is already implied by the
  server-and-client-ship-together decision.

## Migration Plan

None. The behavior is already deployed as `f09feb1e`: no stored record, wire
migration, or data rewrite, and no compatibility layer. Rollback is reverting that
commit.

## Open Questions

None — the behavior is already shipped and fixed.
