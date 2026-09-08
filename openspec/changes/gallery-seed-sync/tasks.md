## 1. Setting, ignore rule, and compose mount

- [ ] 1.1 Add `ART_SEED_ROOT = os.environ.get("ART_SEED_ROOT", os.path.join(GAME_DIR, "art-seed"))` to `server/conf/settings.py`, documented as a directory root following the `PROMPT_ROOT` precedent
- [ ] 1.2 Add `art-seed/` to `.gitignore`
- [ ] 1.3 Add `- ${ART_SEED_DIR:-./art-seed}:/app/art-seed:ro,z` to the `evennia` service volumes in `compose.yaml`, and do NOT copy a seed directory into the image in `Containerfile`
- [ ] 1.4 Add the `ART_SEED_ROOT` entry to `.env.example` and the `ART_SEED_DIR` compose-only entry to the external-reader allow-list in `server/conf/tests/test_env_overrides.py`
- [ ] 1.5 Add both rows to `docs/development/settings-and-environment.md` with type, default, and the "absent directory means synchronize nothing" rule
- [ ] 1.6 Update `tests/test_container_contract.py` to assert the new volume entry

## 2. Seed synchronization module

- [ ] 2.1 Create `world/art/gallery_seed.py` with `sync_all()` walking `<seed root>/<kind>/<subject-key>/` for the closed kind set `character` / `monster`
- [ ] 2.2 Derive each file's card `image_id` deterministically from its path relative to the seed root (a stable uuid5-style derivation) so idempotency needs no bookkeeping
- [ ] 2.3 Skip a file whose derived id is already a card of the subject: no copy, no append, no rewrite
- [ ] 2.4 Copy accepted files into `gallery/<kind>/<subject-key>/<image-id><ext>` under the store root through `world/art/paths.py::resolved_under_store_root`, preserving the source extension when it is a store extension
- [ ] 2.5 Append each card through the gallery write API with `source` `seed`, `prompt`/`seed`/`checkpoint` `None`, empty `requested_fields`, and `binding` `None`
- [ ] 2.6 Skip unsupported extensions, invalid subject keys, and unknown kind directories with bounded diagnostics; never delete, replace, or reorder an existing card
- [ ] 2.7 Parse the optional `manifest.json` (`default`, `face_rect`): validate the rectangle with the standard rules, apply the default only when the subject has no `default_image_id`, and degrade to sorted-name plus the shared rectangle with one diagnostic on any invalid manifest
- [ ] 2.8 Emit `gallery_seed_sync` through the `world.observability` facade for the skip, the summary, and each bounded diagnostic
- [ ] 2.9 Never raise out of `sync_all()`: a missing, unreadable, or malformed tree is a logged skip

## 3. Startup wiring

- [ ] 3.1 Register `sync_all()` as a named startup step in `server/conf/at_server_startstop.py`, ordered after the gallery orphan prune
- [ ] 3.2 Confirm the step is failure-isolated like the existing art startup steps and never aborts boot

## 4. Tests

- [ ] 4.1 `world/art/tests/test_gallery_seed.py`: a missing seed root logs one event, creates nothing, and does not raise
- [ ] 4.2 Idempotency: two runs against an unchanged tree append exactly the first run's cards and copy nothing on the second
- [ ] 4.3 Incremental: a newly added file appends exactly one card and leaves existing cards untouched
- [ ] 4.4 Skips: unsupported extension, invalid subject key, unknown kind directory — each skipped with a diagnostic while valid entries still sync
- [ ] 4.5 Provenance: seed cards carry `source` `seed` with no prompt pair, seed, checkpoint, fields, or binding, and are deletable and default-settable
- [ ] 4.6 Manifest: valid manifest sets the default and rectangle; absent manifest uses sorted name and the shared rectangle; invalid manifest degrades with one diagnostic; an already-chosen default is preserved
- [ ] 4.7 Generated cards for a synchronized subject are unchanged in content, order, and binding
- [ ] 4.8 `server/conf/tests/test_env_overrides.py` and `tests/test_container_contract.py` pass with the new entries
- [ ] 4.9 Annotate new tests with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`

## 5. Verification

- [ ] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art server.conf`
- [ ] 5.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_container_contract`
- [ ] 5.3 `uv run --locked python -m tools.observability_lint check`
- [ ] 5.4 `uv run --locked python -m tools.spec_traceability check`
- [ ] 5.5 `openspec validate gallery-seed-sync --strict`
