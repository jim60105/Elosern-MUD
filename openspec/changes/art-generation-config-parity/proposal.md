# Proposal: art-generation-config-parity

## Why

The MUD's sd-webui integration (`world/art/sd_worker.py`) was written without a
live server and has now been cross-audited line-by-line against the proven,
tested implementation in the HeartReverie
`sd-webui-image-gen` plugin (`lib/client.ts`, `lib/generation.ts`,
`plugin.json` settings schema). The audit result:

- **The core txt2img call is correct**: request body
  (`prompt`/`negative_prompt`/`steps`/`cfg_scale`/`width`/`height`/
  `sampler_name`/`scheduler`), the `override_settings.sd_model_checkpoint` +
  `samples_format: "png"` + `override_settings_restore_afterwards: true`
  pattern, and the reason the opt-in pre-pin exists (Forge validates the
  persistent `samples_format` *before* applying `override_settings`) all match
  the reference exactly. No request-shape fix is needed.
- **Three real gaps remain** versus that verified reference, and they remove
  degrees of freedom the reference already exposes in its settings UI:
  1. **No server-option discovery.** The reference settings UI fills its
     model / sampler / scheduler / styles / modules dropdowns from
     `/sdapi/v1/sd-models|samplers|schedulers|prompt-styles|sd-modules`. Our
     staff must hand-copy those exact strings into env/secret settings; a typo
     becomes a generation-time HTTP 400 → `failed` record.
  2. **The generation seed is dropped.** The reference parses `info.seed` and
     stores it per image so any image can be reproduced/regenerated. Our
     client never reads `info` at all and `ArtAssetRecord` has no seed field,
     so no finished artwork can ever be reproduced.
  3. **No auth.** The reference sends HTTP Basic credentials when the server
     requires them. An auth-enabled sd-webui (the normal way to expose one on
     a LAN) is unreachable for us, and even the pre-pin and future
     option-list calls would 401.

Secondary corrections from the same audit: our transport sends a
`Content-Type: application/json` header on GETs (reference does too, but it is
a needless nit once GETs become common), and it has no per-call timeout
override (hardcoded `ART_SD_TIMEOUT_SECONDS`), which the option/probe calls
added by this and the follow-up change need.

Also parity gaps that *are* configuration freedom: the reference lets the user
pick **styles** (sent as the `styles` request field) and — on Forge — extra
**modules** (`forge_additional_modules`, e.g. TE/VAE, loaded together with the
checkpoint). We have no knob for either.

## What Changes

- Extend the internal sd-webui client with **bounded option enumeration**:
  `list_models/list_samplers/list_schedulers/list_styles/list_modules` GET the
  five reference endpoints through the existing deadline-bounded transport
  (with a per-call timeout cap), map the reference field shapes
  (`title`→`model_name`, `name`, scheduler `label`→`name`, style `name`,
  module `model_name`), and validate response size/shape with named errors.
- Add **Basic auth**: `ART_SD_USERNAME`/`ART_SD_PASSWORD` plain settings
  (defaults empty, sanctioned only in `server/conf/secret_settings.py`, never
  environment-readable, never logged). Every request carries the
  `Authorization: Basic` header the reference sends if and only if BOTH
  settings are non-empty; with either empty, no header is sent (a
  half-configured pair is treated as anonymous, never `user:`).
- Add a **seed pipeline**: the client returns a `GeneratedImage(data, seed)`
  result (transport PNG bytes + `info.seed` parsed defensively, missing/garbage
  `info` yields `seed=None` and never fails a job); `ArtAssetRecord` persists a
  nullable `seed`; `@art status` shows it; the fake client and the browser
  harness fake gain the same interface.
- Add **two free-text knobs** (comma-separated name lists, exact pass-through):
  `ART_SD_STYLES` → the request's `styles` field; `ART_SD_MODULES` → Forge
  `override_settings.forge_additional_modules` + the reference's fixed
  `forge_unet_storage_dtype` companion (Forge-targeted; documented). Both
  omitted from the request when empty, like sampler/scheduler today.
- Add the staff command **`@art options <models|samplers|schedulers|styles|modules>`**
  which prints the live server's exact selectable names (bounded count + cap)
  so the env/secret values above can be copied verbatim — the settings-UI
  dropdowns of the reference, translated to the MUD's staff surface.
- Small transport correction: no `Content-Type` header on GETs; `_http_json`
  gains a `timeout_seconds` parameter defaulting to the existing setting.

No player-facing surface changes. No backward compatibility work (unreleased,
0 users): seed is added as nullable; existing records simply show no seed.

## Capabilities

### New Capabilities
- `art-sd-server-integration`: the internal sd-webui client's server-facing
  contract — option enumeration endpoints with bounded validation, Basic auth
  from secret-file settings, and per-call timeout discipline.

### Modified Capabilities
- `art-queue-worker`: the worker contract's client result becomes
  `GeneratedImage(data, seed)`; asset records persist the generation seed;
  `@art status` surfaces it.
- `art-staff-commands`: new `@art options` subcommand (Developer-only).
- `settings-environment-overrides`: the env-backed set grows from exactly 19 to
  exactly 21 (`ART_SD_STYLES`, `ART_SD_MODULES`); auth credentials are named
  explicitly as secret-file-only settings.

## Impact

- Code: `world/art/sd_worker.py` (enumeration, auth, seed, timeout param,
  request builder), `world/art/fake_sd_client.py` and
  `web/tests/browser/fake_sd_client.py` (interface), `world/art/worker.py` +
  `world/art/service.py` (settle carries seed), `world/art/store.py` (+`seed`),
  `world/art/presenter.py` untouched (never staff data), `commands/art.py`
  (`@art options`, `@art status` seed column), `server/conf/settings.py`
  (+4 settings; 2 env-backed).
- Docs: `.env.example`, `docs/development/settings-and-environment.md`,
  `docs/gm/prompts.md` (new knobs), `docs/game/commands.md` +
  `docs/game/command-reference.md` (`@art options`) — the command-doc contract
  (`tests/test_command_docs.py`) applies.
- Tests: `world/art/tests/test_sd_worker.py` + new
  `world/art/tests/test_options.py`, `commands/tests` for `@art options`/
  `@art status`, `server/conf/tests/test_env_overrides.py` inventory tables,
  `.github/evennia-shards.json` registers new modules (world label owns them).
- No new dependencies. No database migration (AttributeProperty addition on a
  script is schemaless).
