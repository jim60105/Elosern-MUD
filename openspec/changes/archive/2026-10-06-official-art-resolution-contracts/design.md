## Context

See proposal.md for motivation. The catalog (`official-artwork-catalog`) supplies snapshot lookup + fingerprinted serving; the reference resolver (`official-content-provenance`) supplies entity→content-reference binding. This change weaves them into the deterministic chain and versioned payloads. Source design §6–§7 and §11's offline rules.

## Goals / Non-Goals

**Goals:**
- One chain, one vocabulary: official / runtime / silhouette remain distinguishable everywhere a portrait payload travels.
- Zero new mutation or I/O in presentation; eligibility ordering preserved.

**Non-Goals:**
- Personal official selections, geometry overrides, and gallery read-only rows (owned by `official-art-personalization`). Silhouette payload semantics and the stage mask (owned by `builtin-silhouette-stage-fallback`; its step-8 slot in the chain already exists as the fallback seam).

## Decisions

- **Official default slot after the classic asset, before the fallback seam** (step 6 of 8): keeps every existing runtime branch byte-for-byte ahead of official, satisfying "runtime images outrank official defaults" without touching steps 1–5, and the monster variant falls through the slot because it has no producer (structural, not conditional). The alternative — official ahead of cards — was rejected: it would let a server-side artwork swap silently replace a player's chosen default.
- **Origin discriminator as a new payload field with a closed vocabulary** (`official` | `runtime` | …silhouette value added by the silhouette change) rather than inferring from URL prefixes: the design forbids URL-shape inference and both wire validator sides mirror exact schemas anyway; adding one bounded enum field is the smallest versioned contract.
- **Auto-generation suppression lives in the autogen guard, not the chain**: the observable side ("official-satisfied subject presents official art without a card") is already forced by the chain; only the request-site guard is new, so one module (`service.py`'s guard) changes instead of every lifecycle path.
- **Stale official reference fall-through with no preference deletion** is chain behavior; the preference side (retaining the personal selection) belongs to personalization, so the chain simply treats "reference resolves to nothing" as a pass.
- **Presentation uses the startup snapshot exclusively** (catalog contract), so the chain's purity clause extends naturally: stored state + startup snapshot.
- **The official step presents only a wire-shippable URL.** An official identity embeds an
  operator-chosen filename, and the shared portrait media-URL ceiling is a bounded wire field, so
  the payload branch presents the official default only when `url_for` returned a URL inside that
  ceiling; an over-budget URL resolves nothing and the chain continues exactly as for an absent
  reference, so one oversized file can never fail the whole art/roster panel for the room. The
  ceiling constant lives in `world/art/presenter.py` (the payload vocabulary owner, which the panel
  validators already import their origin vocabulary from) and a test pins it equal to the panel
  validators' shared `MAX_MEDIA_URL`.
- **The `official` origin exists only beside its URL.** `official` names the branch that produced
  the payload's own media, so both wire validators refuse an `official` origin that carries no URL
  or a non-null (`done`/generated) status; a reference resolving no URL falls through instead of
  producing a url-less official row.
- **The presenter re-validates the catalog's geometry.** The official payload branch runs the
  directory metadata/fitted rectangle and the declared stage through the same gallery validators a
  stored card uses and degrades to the fitted default/identity with the existing bounded
  diagnostics — the snapshot's load-time validation is not treated as a substitute for the payload
  boundary's.
- **No roster schema-version bump.** The roster's portrait vocabulary gains the origin discriminator
  while `ROSTER_SCHEMA_VERSION` stays 2, exactly as `builtin-silhouette-stage-fallback` added the
  origin and the decorative `fallback` field to the art panel's version 2 without a bump: server and
  client ship together (the existing deploy contract), so no mixed-version tolerance is required.

## Risks / Trade-offs

- [Versioned portrait vocabularies change in three surfaces at once (art catalog, roster rows, payload)] → they ship together in this one change with the dual-side validators updated atomically; the contract gate is the verification.
- [Suppressing auto-generation when official satisfies hides generated-art absence from operators expecting cards] → `official_art_*` catalog diagnostics and the autogen guard test make the suppression explicit; staff generation paths are untouched.
- [A species-capped tier's official art could suppress the one card an automatic path would otherwise produce] → accepted: monsters have no official-reference producer before the separate species catalog lands, and every automatic path (including the startup synchronization that walks every monster tier) re-evaluates the guard, so a vanished directory re-enables the automatic request on the next path while a present directory leaves the existing runtime card untouched; manual generation stays available.
- [The new capability's requirement ids exist only after the archive sync] → this change's tests deliberately carry no `covers_requirement("official-art-resolution::…")` annotation (`tools.spec_traceability` rejects an id that is not in a main spec); the archive step adds at least one annotation per new requirement id, on the `official-artwork-catalog` precedent. The `webclient-art-panel`, `webclient-character-roster`, `art-gallery-resolution`, and `art-gallery-autogen` ids already exist and are used where the behavior matches.

## Migration Plan

Payload fields are additive; deploy with the catalog empty and every new branch is inert. Rollback reverts the change; no stored state to unwind (nothing new is persisted).

## Open Questions

None.
