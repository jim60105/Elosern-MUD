## 1. Settings and request behavior

- [x] 1.1 Add `ART_SD_SERVER_RETAIN_IMAGES = _env_bool("ART_SD_SERVER_RETAIN_IMAGES", True)` immediately after `ART_SD_PREPIN_SAMPLES_FORMAT` in `server/conf/settings.py`; verify the existing subprocess settings tests establish default `True`, typed boolean overrides, and fail-closed invalid words with unchanged configuration precedence.
- [x] 1.2 Add `ART_SD_SERVER_RETAIN_IMAGES` to the env-pop list in `server/conf/test_settings.py`; verify the existing bootstrap/inventory contract covers this variable and inherited false or invalid values cannot dirty test settings.
- [x] 1.3 Update `world/art/sd_worker.py::build_txt2img_request()` so false adds both top-level `do_not_save_samples=True` and `do_not_save_grid=True`, while true omits both; verify no fields enter `override_settings`, no new `/sdapi/v1/options` call is introduced, and no engine-store or response-processing path changes.

## 2. Tests and traceability

- [x] 2.1 Extend `world/art/tests/test_sd_worker.py` with the two request-builder cases: default retention omits both fields, and false sets both to boolean true at top level and not in `override_settings`; assert existing generation parameters remain intact. Reuse deterministic fixtures and injectable transports, with no live server calls.
- [x] 2.2 Extend the table-driven subprocess cases in the existing `server/conf/tests/test_env_overrides/` package (`_support.py` and `test_defaults_coercion_and_fail_closed.py`) with the new knob's default `True`, empty default, case-insensitive `1/true/yes/on` and `0/false/no/off` coercion, and invalid-word `ImproperlyConfigured` including variable/raw value/rule. In `test_seam_precedence_derived_and_sanitization.py`, exercise bootstrap imports with inherited false and separately `maybe`, asserting successful import and effective `True`. Ensure existing exact inventory checks cover the added knob without new test modules.
- [x] 2.3 Run an existing successful-generation/store test with `ART_SD_SERVER_RETAIN_IMAGES=False`, asserting returned bytes are processed and persisted normally; reuse its offline fixtures and annotate this establishing test for the worker requirement.
- [x] 2.4 Import and apply `covers_requirement` from `tools.spec_traceability` to establishing tests for the new worker requirement and amended environment requirement. Obtain canonical existing requirement IDs with `uv run --locked python -m tools.spec_traceability list`; resolve the added requirement's literal ID through that same command once it enters the main-spec index during spec synchronization, rather than manually constructing it. Verify traceability with `uv run --locked python -m tools.spec_traceability check` against the synchronized main contract before handoff/archive.

## 3. Deployment documentation

- [x] 3.1 Add a commented `ART_SD_SERVER_RETAIN_IMAGES=true` entry in `.env.example`'s sd-webui tuning section and increment the environment-variable header count; verify the inventory/count contract recognizes the new settings reader and the documented default matches code.
- [x] 3.2 Add rows near `ART_SD_PREPIN_SAMPLES_FORMAT` in `docs/development/settings-and-environment.md` and `docs/gm/prompts.md`, preserving their existing zh-tw table style; verify both state boolean/default true, false suppressing sd-webui sample/grid copies only, engine art-store unaffected, and request-scoped rather than persistent server mutation.
- [x] 3.3 Confirm `compose.yaml` remains unchanged because `env_file: .env` supplies the knob; confirm `docs/game/commands.md` and `.github/evennia-shards.json` remain unchanged because there is no player command or new test module.

## 4. Focused acceptance

- [x] 4.1 Run the existing `world.art.tests.test_sd_worker` and `server.conf.tests.test_env_overrides` labels using the project's uv-managed test-settings workflow and a temporary env file containing `MUD_TEST_SETTINGS=1`; verify both pass offline and the engine's existing successful-generation/store tests remain green.
- [x] 4.2 Run `uv run --locked python -m tools.contract_gate` and `openspec validate sd-server-image-retention-switch --strict`; verify both succeed and all artifacts, documentation, tests, and implementation agree before marking tasks complete.
