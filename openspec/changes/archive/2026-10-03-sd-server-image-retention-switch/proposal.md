# Proposal: sd-server-image-retention-switch

## Why

The engine stores its generated art locally, but sd-webui can also retain duplicate images in its own outputs directory. Deployments need an environment-configurable way to suppress those server-side copies without changing the engine's art store or the shared server's persistent configuration.

## What Changes

- Add `ART_SD_SERVER_RETAIN_IMAGES = _env_bool("ART_SD_SERVER_RETAIN_IMAGES", True)` next to `ART_SD_PREPIN_SAMPLES_FORMAT` in the art settings. The positive name follows `ART_REMBG_ENABLED`; the default preserves current behavior.
- When retention is disabled, `build_txt2img_request()` adds top-level `do_not_save_samples: true` and `do_not_save_grid: true`. When enabled, both fields are omitted. Neither field belongs in `override_settings`, and this switch never uses `/sdapi/v1/options`.
- Remove the new variable from inherited environments in the test-settings bootstrap, and extend the existing subprocess boolean-override and request-builder tests.
- Add a commented `.env.example` entry in the sd-webui tuning section and increment its environment-variable header count; document the knob in the existing Traditional Chinese settings and GM tables.
- Preserve the engine's art persistence, generation response processing, and other request settings. No compatibility layers or migrations are needed for this unreleased project.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `internal-art-worker`: add the request-scoped server-retention requirement alongside the existing txt2img request contract.
- `settings-environment-overrides`: extend the exact env-backed inventory and boolean conversion contract with the new default-true setting.

## Impact

Implementation touches `server/conf/settings.py`, `server/conf/test_settings.py`, `world/art/sd_worker.py`, `world/art/tests/test_sd_worker.py`, the existing `server/conf/tests/test_env_overrides/` package, `.env.example`, `docs/development/settings-and-environment.md`, and `docs/gm/prompts.md`. Establishing tests use `covers_requirement` from `tools.spec_traceability`; reuse an existing successful-generation/store test to establish persistence with retention disabled.

`compose.yaml` remains unchanged: `env_file: .env` already supplies `ART_SD_*` variables. No player command changes, so `docs/game/commands.md` remains unchanged. No new test modules, so `.github/evennia-shards.json` remains unchanged. This is a bounded one-engineer-day change with no prerequisite active change; it does not touch the active square-face-rect or gallery-push-refresh implementation surfaces.
