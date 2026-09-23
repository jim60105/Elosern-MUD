# Tasks — translate model download policy

## 1. The knob

- [ ] 1.1 Add `ART_TRANSLATE_DOWNLOAD_ENABLED = _env_bool("ART_TRANSLATE_DOWNLOAD_ENABLED", True)` to the translation block of `server/conf/settings.py`, with a comment mirroring the `ART_REMBG_DOWNLOAD_ENABLED` stanza; verify `ART_TRANSLATE_DOWNLOAD_ENABLED=off` imports to `False` and `=maybe` raises the named settings error.
- [ ] 1.2 Add `ART_TRANSLATE_DOWNLOAD_ENABLED` to the pop list in `server/conf/test_settings.py`; verify an inherited `ART_TRANSLATE_DOWNLOAD_ENABLED=false` shell value cannot perturb a test run (defaults to `True` under test settings).
- [ ] 1.3 Extend the inventory contract in `server/conf/tests/test_env_overrides/_support.py`: the name→env map, the default map (`True`), a coercion row (`off` → `False`), and a rejection row (`maybe` → boolean-word rule); verify `server/conf/tests/test_env_overrides/` passes, including the AST exact-set check against `.env.example` and settings reads.

## 2. The download track in the backend

- [ ] 2.1 In `world/art/translate_ct2.py`, gate `_check_layout` failure on `settings.ART_TRANSLATE_DOWNLOAD_ENABLED`: false keeps today's exact immediate `art_translate_unavailable` before any library import; true routes the failing layout through a new `_populate(model_dir)` step before the re-check. Verify the existing unavailable-path tests still pass with the flag false.
- [ ] 2.2 Implement `_populate`: stdlib-only fetch of `https://argos-net.com/v1/translate-zh_en-1_9.argosmodel` with connect/read timeouts and a 128 MiB response-size cap, no retries; verify with `zipfile` integrity, member-path safety (everything under `translate-zh_en-1_9/`, no absolute/`..` paths), and the required-entry list (`model/config.json`, `model/model.bin`, `model/shared_vocabulary.json`, `sentencepiece.model`, `README.md`); unpack exactly those pieces (never `stanza/`), landing each via temp file + `os.replace`. Verify with a local fixture zip served over a stubbed opener: success populates the layout, and each failure mode (bad zip, unsafe member, missing entry, oversize, timeout) raises `art_translate_unavailable`.
- [ ] 2.3 Add the per-process failure latch: the first `_populate` failure records itself so later calls skip the fetch and fail immediately with `art_translate_unavailable`; a completed layout is never re-fetched. Verify a scripted first-failure followed by a second translation attempt performs exactly one network attempt.
- [ ] 2.4 Emit the lifecycle events from the backend module via `world.observability`: exactly one `art_translate_model_download_done` info (url, bytes, duration_ms) on success and exactly one `art_translate_model_download_failed` warn (url, exception chain) on the first failure; verify the seam's own event counts (`art_translate_done` / `art_translate_failed`) are unchanged for the calling job and that the job still settles `done` on the untranslated description.

## 3. Backend tests

- [ ] 3.1 Add `CTranslate2Backend` download-track tests to `world/art/tests/test_translate.py`: complete layout ⇒ zero network (spy count 0); missing layout + flag true ⇒ one fetch then successful translation against the unpacked fixture; every fetch failure degrades through the normal `art_translate_failed` warn without crashing the caller. Verify the whole art suite imports no `ctranslate2`/`sentencepiece` and attempts no network at default settings (fake backend keeps the suite hermetic).
- [ ] 3.2 Add the air-gapped regression: flag false against an absent directory reproduces today's byte-exact behavior — immediate `art_translate_unavailable`, no library import, zero network attempts, record settles `done` untranslated. Verify the existing "server never fetches" expectations now hold under `DOWNLOAD_ENABLED=false` and the suite-level network-spider sees zero model requests in both modes at test settings.

## 4. Seeder script volume-name fix

- [ ] 4.1 In `scripts/fetch-translate-model.sh`, replace the hard-coded printed volume name with a resolver: exact `evennia-translate`, then `${COMPOSE_PROJECT_NAME:-mud}_evennia-translate`, then a `podman volume ls --format '{{.Name}}'` suffix match on `_evennia-translate`; fall back to the project-prefixed default annotated "unresolved" when `podman` is absent or nothing matches, with unchanged exit status. Verify by running the script's resolver function against a stubbed `podman` on PATH returning `mud_evennia-translate` (printed command names that volume) and against no `podman` (annotated default).
- [ ] 4.2 Update the script's header comment and the busybox example to the resolved name; verify `scripts/fetch-translate-model.sh --help` output matches and `bash -n` passes.

## 5. Inventory docs and settings guide

- [ ] 5.1 Add the commented `#ART_TRANSLATE_DOWNLOAD_ENABLED=false` entry with its boolean/type/default/air-gapped comment block to the translation stanza of `.env.example` (wording mirroring the rembg download stanza); verify the AST inventory contract finds a reader for it and no dead variable.
- [ ] 5.2 Update `docs/development/settings-and-environment.md`: the `ART_TRANSLATE_DOWNLOAD_ENABLED` table row (布林, default `True`) and the seed-policy paragraph rewritten to the dual track (first-use fetch into the `evennia-translate` volume when enabled; `false` + `scripts/fetch-translate-model.sh` pre-seed as the air-gapped configuration); verify every env-backed name in the guide table matches `_support.py`'s inventory.

## 6. Container contract and verification

- [ ] 6.1 Confirm no compose/Containerfile change is needed (the `/app/server/.translate` volume and layer-scan assertions are unchanged); run `tests/test_container_contract.py` and verify the no-baked-model scan still passes.
- [ ] 6.2 Integration check: with a temp `ART_TRANSLATE_MODEL_DIR`, a stubbed URL fetcher, and `ART_TRANSLATE_DOWNLOAD_ENABLED=true`, drive `translate_description` end to end and observe populate → build → translate; kill-and-restart the process against the same directory and observe zero further fetches. Verify `openspec validate add-translate-model-download-policy --strict` passes and `world/art/tests/test_translate.py` plus `server/conf/tests/test_env_overrides/` are green.
