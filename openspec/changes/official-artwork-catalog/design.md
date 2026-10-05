## Context

See proposal.md for motivation. The engine already owns three external-content seams this change reuses rather than reinvents: `ART_SEED_ROOT` + `world/art/gallery_seed.py` (no-follow directory walking, bounded diagnostics, manifest convention), `ART_STORE_ROOT` + `world/art/paths.py` (confinement), and `web/art_media.py` (the single closed `/art/` media vocabulary). The approved source design is `docs/superpowers/specs/2026-10-05-external-art-assets-and-silhouette-fallbacks-design.md` §§3–4, 10.

## Goals / Non-Goals

**Goals:**
- One read-only, restart-scoped, startup-indexed catalog over an externally prepared directory, plus its serving branch.
- Predictable failure behavior: invalid entries degrade per-entry; an absent root is normal.

**Non-Goals:**
- No resolution-order or payload changes (owned by `official-art-resolution-contracts`), no personal selections (owned by `official-art-personalization`), no compose/deployment surface (owned by `official-artwork-deployment`), no species catalog for monsters (separate design; the `monster/` kind exists in the layout contract but this change invents no species keys, aliases, or threat-tier mappings).

## Decisions

- **New module `world/art/official.py`, snapshot-only reads.** Alternative considered: lazy directory walks per resolution — rejected: the design forbids per-request filesystem dependence, and a startup snapshot gives one place for admission validation and fingerprinting. Alternative: reuse `gallery_seed`'s sync loop shape that copies into the store — explicitly rejected (design amendment 2): official artwork is resolved in place, never copied or mirrored into mutable cards.
- **Ownership by the art service's startup step list** (like seed sync) rather than a new Script: the catalog is derived state, not persistent state; restart-rebuild is the required refresh semantics and a watcher/hot-reload is forbidden.
- **Directory-root setting following the `PROMPT_ROOT`/`ART_SEED_ROOT` precedent** (env override of the same name; the `settings-environment-overrides` inventory contract then demands `.env.example` + guide entries via its existing requirement, no requirement delta).
- **Fingerprint = content hash computed at load.** Alternatives: mtime (useless across bind-mount re-prepares and volume restores) and a maintained version file (a release registry in disguise — forbidden by the design). Stale fingerprint 404s rather than serving history, per design §10.
- **Media URL shape `official/<fingerprint>/<root-relative-path>`.** Keeping the root-relative path in the URL makes the browser cache key identity-bound and the 404-for-stale-fingerprint rule trivial; the fingerprint segment is validated against the catalog entry for that path. The alternative (opaque id-only URLs) would need a second lookup table and hides the natural debugging structure.
- **Admission reuses existing validators** — closed extension vocabulary, bounded image decode limits, geometry validators — instead of a new image policy, so official, store, and seed images share one definition of "valid image."
- **Manifest convention identical to seed metadata** (`default`, `face_rect`, `stage`; deterministic filename order otherwise) so operators who know the seed format already know this one; invalid manifest degrades to fitted defaults rather than rejecting images.

## Risks / Trade-offs

- [Large official roots slow startup indexing] → bounded by the existing per-file byte cap and decode limits applied during admission; a pathological tree costs one startup pass, and the boundary event reports counts for operators. Mitigation is operator-side (prune the tree); no incremental indexing is added.
- [Restart-only refresh surprises operators editing files live] → intentional per the design's maintenance-window model; the `official_art_catalog_loaded` event makes the indexed state explicit at every start.
- [Fingerprint of every file could be slow for very large trees] → hashing streams file bytes once at load with the existing read budget; correctness (never per-request) is the contract, and the boundary event's duration is implicitly visible in startup logs.

## Migration Plan

Purely additive: deploy with the new setting unset and the behavior is today's, exactly. Rollback is reverting the code; the official directory is never written by the game, so no cleanup is needed.

## Open Questions

None — the source design fixes layout, naming, and fingerprint semantics.
