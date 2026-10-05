## Batch:

- depends-on: (none)
- conflicts: none (settings.py and docs are touched only here; the media-route module is shared with `official-art-resolution-contracts`, sequenced after this change)

## Why

Official artwork is too large for the code repository and must be distributable independently under its own license notice, but the game needs one boring, read-only, filesystem-based source for it. The approved design (docs/superpowers/specs/2026-10-05-external-art-assets-and-silhouette-fallbacks-design.md §§3–4, 10) replaces the earlier installer/release-management model with a single externally prepared artwork directory that the game only reads.

## What Changes

- Declare `ART_OFFICIAL_ROOT`: a directory-root setting defaulting to a gitignored `art-official/` directory under the game root, overridable by an environment variable of the same name (the `ART_SEED_ROOT`/`PROMPT_ROOT` precedent), documented in `.env.example` and the settings guide.
- Add a startup official-artwork catalog owned by the art service: it indexes the `monster/<species-key>/`, `preset/<preset-key>/`, `npc/<npc-or-profile-key>/` layout of the mounted root once at startup, serves ordinary resolution from that snapshot, and never calls Git, S3, an archive extractor, or any network at runtime.
- Admit only valid image files confined to the configured root using the existing closed image-format vocabulary, geometry validators, and bounded image limits; reject symlinked/out-of-root paths, unsupported formats, unreadable/undecodable files, and oversized images; ignore unsupported content directories and unknown registry references with bounded diagnostics instead of rejecting the whole root. A content key must satisfy the shared stable-key contract, and a `preset` key must additionally be declared by the player-preset registry — the one registry that exists today; `npc`/`monster` registry membership arrives with `official-content-provenance` and the separate monster species catalog, so those kinds admit any structurally valid key and never a tier or a display name.
- Honor the optional per-content `manifest.json` (`default` filename, `face_rect`, `stage`) following the seed-metadata convention: deterministic filename order without a valid explicit default; missing metadata is normal; invalid metadata emits a bounded diagnostic and falls back to the fitted face rectangle and identity stage placement without blocking unrelated artwork.
- Compute one file-content fingerprint per catalog image once at catalog load, and extend the closed `/art/` media route with an official identity branch that serves only catalog-admitted images under root confinement (outdated fingerprints after a maintenance restart may 404).
- Record the catalog-load boundary and bounded invalid-entry diagnostics through the `world.observability` named-import facade with stable English event ids.
- A missing or empty artwork root is a valid no-art configuration: the catalog loads empty, startup succeeds, and resolution degrades to the existing chain.

## Capabilities

### New Capabilities

- `official-artwork-catalog`: the read-only external official-artwork directory contract — the `ART_OFFICIAL_ROOT` setting, the `monster/preset/npc` content-kind layout and root-relative stable asset identity, startup snapshot indexing, admission validation and bounded diagnostics, the optional per-content manifest, the per-file content fingerprint, and the catalog-load observability boundary.

### Modified Capabilities

- `art-queue-worker`: the `/art/` media route admits official-content identities addressing catalog-indexed files under the same closed-extension, no-symlink, root-confinement discipline as gallery and built-in-default identities, with the startup fingerprint as the cache token.

## Impact

- Code: `server/conf/settings.py` (the setting), `server/conf/at_server_startstop.py` (the boot step that owns catalog load, registered beside `art_seed_sync`), new `world/art/official.py` (catalog) and `world/art/no_follow.py` (the no-follow open primitives extracted from `world/art/gallery_seed.py`, which now imports them instead of keeping a private copy), `web/art_media.py` (official branch), `.gitignore`, `.env.example`, `docs/development/settings-and-environment.md`. `ART_OFFICIAL_ROOT` follows the existing `ART_SEED_ROOT`/`PROMPT_ROOT` directory-root procedure, so the `settings-environment-overrides` inventory contract needs no requirement change — only compliance (the variable joins `.env.example` and the settings guide, which its existing requirement already mandates).
- Tests: new `world/art/tests/test_official_catalog.py`, the official branch in `web/webclient/tests/test_art_media.py`, the `ART_OFFICIAL_ROOT` cases in `server/conf/tests/test_art_settings.py`, the directory-root union in `server/conf/tests/test_env_overrides/test_inventory_and_shard_ownership.py`, the stubbed step roster in `server/conf/tests/test_startup_observability.py`, and the repository-wide offline contract in `tests/test_art_offline_contract.py`. No shard-manifest entry is added: the package labels `world.art` and `web.webclient.tests` already own those modules exactly once, and an explicit entry would break the single-owner contract.
- No runtime network access, no release registry, no activation pointer, no hot reload; existing `ART_STORE_ROOT`/`ART_SEED_ROOT` behavior unchanged.
