## 1. Setting and layout contract

- [x] 1.1 Declare `ART_OFFICIAL_ROOT` in `server/conf/settings.py` (default `art-official/` under `GAME_DIR`, same-named env override, `ART_SEED_ROOT` precedent), gitignore the default directory, and verify with a settings unit test that the env override and default both resolve and the directory is untracked
- [x] 1.2 Add `ART_OFFICIAL_ROOT` to `.env.example` and document it in `docs/development/settings-and-environment.md`, and verify the settings inventory contract test passes with the new variable

## 2. Catalog core

- [x] 2.1 Create `world/art/official.py` with the startup index over the `monster|preset/npc/<key>/<file>` layout using no-follow directory walking (gallery_seed discipline), and verify with unit tests that valid synthetic content indexes with root-relative identities and deterministic ordering
- [x] 2.2 Implement admission validation — closed extension vocabulary, decodable under the existing bounded image limits, strictly in-root, non-symlink regular files — and verify per-entry refusal tests for out-of-root symlinks, unsupported formats, undecodable and oversized files each prove unrelated valid entries still index
- [x] 2.3 Implement optional per-content `manifest.json` handling (`default`, `face_rect`, `stage`; fitted-default and identity-stage degradation, bounded diagnostic, missing manifest silent) and verify manifest tests cover valid, invalid, missing, and per-image-invalid-rectangle cases
- [x] 2.4 Compute the per-file content fingerprint once at load and expose `fingerprint_for(identity)` plus snapshot lookup, and verify a test that byte replacement plus reload changes the fingerprint and that resolution performs no hashing
- [x] 2.5 Wire catalog load into the art service startup step list and verify a startup-integration test proves an absent root yields an empty catalog, startup succeeds, and no network/extraction call occurs (patched socket tripwire per repo convention)

## 3. Observability

- [x] 3.1 Emit the `official_art_catalog_loaded` boundary event plus bounded per-entry refusal events with a diagnostic budget through the `world.observability` named-import facade, and verify event tests assert counts, context keys (kind/key/relative path, never absolute roots), and the suppressed-count reporting; run the observability lint check over changed modules

## 4. Media serving

- [x] 4.1 Add the `official/<fingerprint>/<root-relative-path>` branch to `web/art_media.py` as a catalog lookup only (closed extension map, in-root confinement, no caller-supplied paths), and verify route tests: admitted identity serves bytes, stale fingerprint / unindexed path / escape / symlink return 404 with no acquisition attempt
- [x] 4.2 Prove serving does not copy official bytes into the store in a test that fetches an official identity and asserts the runtime store tree is byte-for-byte unchanged

## 5. Verification

- [x] 5.1 Add the new test modules to the shard manifest and run the package-adjacent tests for settings, catalog, media route, plus the contract gate for changed modules, verifying all pass with synthetic artwork only
