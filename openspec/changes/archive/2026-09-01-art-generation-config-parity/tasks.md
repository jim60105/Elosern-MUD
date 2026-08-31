# Tasks: art-generation-config-parity

## 1. Client enumeration + transport corrections

- [x] 1.1 Add `timeout_seconds: float | None = None` to `_http_json` (defaults to
  `ART_SD_TIMEOUT_SECONDS`); omit `Content-Type` on GET (payload is None); keep
  every existing deadline/cap/named-error behavior and test it.
- [x] 1.2 Add `list_options(...)` + the five wrappers `list_models`,
  `list_samplers`, `list_schedulers`, `list_styles`, `list_modules` with the
  reference field fallbacks, 100-item cap, ≤10 s per-call timeout, and named
  errors (design D1).
- [x] 1.3 Unit-test each endpoint mapping, the label→name scheduler fallback,
  malformed list / oversized list / non-200 / non-JSON cases with a fake
  transport capturing method+headers+timeout (no sockets).

## 2. Auth (secret-file-only)

- [x] 2.1 Add `ART_SD_USERNAME = ""` / `ART_SD_PASSWORD = ""` plain settings
  with "deliberately NOT environment-overridable" comments; no `_env_*` call.
- [x] 2.2 Send `Authorization: Basic` iff both non-empty on every request
  (txt2img + all option calls); password never in logs/errors.
- [x] 2.3 Tests: header absent with either empty, present with both set, on GET
  option calls too; SDError/log strings never contain the password.

## 3. Seed pipeline

- [x] 3.1 Introduce frozen `GeneratedImage(data: bytes, seed: int | None)`;
  `SDWebUIClient.generate` returns it, parsing `info` JSON defensively
  (non-negative int, bool/float rejected → None); never raises on seed issues.
- [x] 3.2 Add `seed: int | None = AttributeProperty(default=None)` to
  `ArtAssetRecord`; extend `world/art/queue.py::settle_generated` with a
  `seed` keyword (assign unconditionally on publish, None clears stale);
  `worker._settle_one` passes `image.data`/`image.seed`.
- [x] 3.3 Update `world/art/fake_sd_client.py` and
  `web/tests/browser/fake_sd_client.py` to the new interface (default seed
  12345, scriptable); update every `client.generate` caller/assertor.
- [x] 3.4 Tests: seed persisted on done record; garbage/missing info → done
  with seed None; fakes return the dataclass.

## 4. Styles + modules knobs

- [x] 4.1 Add `ART_SD_STYLES` / `ART_SD_MODULES` via `_env_str(..., "")`;
  request builder splits on commas, strips, drops empties; emits `styles` and
  `forge_additional_modules` + fixed `forge_unet_storage_dtype` only when
  non-empty (design D4).
- [x] 4.2 Extend `VALID_OVERRIDES`/`ENV_BACKED`/`DEFAULT_REPR` tables in
  `server/conf/tests/test_env_overrides.py` to exactly 21 entries; update the
  AST inventory expectations and `_test_settings_popped_names` guard.
- [x] 4.3 Tests: omission when empty/separator-only; verbatim lists when set;
  companion dtype constant exact.

## 5. `@art options` + `@art status` seed column

- [x] 5.1 Add `CmdArtOptions` (Developer) with kind validation, one-line-per-
  name output, header with kind+count+host-only, named-code-only error path,
  256-code-point name clamping; wire into the art command set.
- [x] 5.2 Extend `@art status` output with ` seed=<n>` only when present.
- [x] 5.3 Update `docs/game/commands.md` + `docs/game/command-reference.md`
  (new row + anchor); keep `tests/test_command_docs.py` green.
- [x] 5.4 Command tests: list rendering, invalid args no-request, unreachable
  server named code, denial for non-staff, seed column present/absent.

## 6. Inventory, shards, traceability

- [x] 6.1 `.env.example`: add `#ART_SD_STYLES=` / `#ART_SD_MODULES=` commented
  entries with type/semantics comments; note `ART_SD_USERNAME`/
  `ART_SD_PASSWORD` as secret_settings-only (no active entries).
- [x] 6.2 Update `docs/development/settings-and-environment.md` inventory
  tables (21 env-backed rows + secret-file table gains the auth pair) and the
  `docs/gm/prompts.md` table rows for the two knobs.
- [x] 6.3 No `.github/evennia-shards.json` change: new modules under
  `world.art/tests/` are owned by shard 4's `world.art` label (the ownership
  contract resolves labels recursively and asserts exact coverage). Verify with
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py
  --keepdb tests.test_evennia_test_optimization_contract`.
- [x] 6.4 Annotate tests with `@covers_requirement` using literal IDs for the
  three `art-sd-server-integration` requirements, the MODIFIED worker,
  staff-commands, and settings requirements. IDs are canonical only once the
  specs are synced (task 8.1): write the annotation with the slugs derived
  from the delta requirement headings, and the check gate only accepts them
  after sync — the `env-overridable-settings` archive (7893d28 precedent) is
  the working example of this ordering.

## 7. Verification

- [x] 7.1 Focused: `server.conf.tests world.art commands` + contract test green
  (keepdb, parallel).
- [x] 7.2 `compileall -q server world commands`; `git diff --check`;
  `openspec validate art-generation-config-parity --strict`.

## 8. Archive-time traceability sync (after implementation is verified)

- [x] 8.1 Sync this change's deltas into `openspec/specs/` as part of the
  archive workflow, confirm every `covers_requirement` ID against
  `uv run --locked python -m tools.spec_traceability list`, then land
  code + tests + spec sync + archive as one commit chain;
  `tools.spec_traceability check` and `openspec validate --all --strict`
  green. B's implementation may not start before this archive completes
  (B's MODIFIED settings requirement restates the synced post-A text).
