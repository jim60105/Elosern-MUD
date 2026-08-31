# Tasks: Env-overridable deployment settings

Implementation note: per the traceability timing decision in design.md, the `covers_requirement`
IDs can only validate after the delta spec syncs into `openspec/specs/` at archive time (the
`7893d28` precedent lands code, tests, and spec sync in one commit). During groups 2–4, verify
with the focused Evennia test labels, not the traceability check gate.

## 1. Settings helpers

- [x] 1.1 In `server/conf/settings.py`, add the private helpers `_env_str(name, default="")` and `_env_typed(name, convert, default, *, minimum=None, multiple=None)` above the art section, with the blank-is-unset and fail-closed semantics from design D1/D4 (error message: `setting <NAME>: invalid environment value '<raw>' (<rule>)`, raising `django.core.exceptions.ImproperlyConfigured`); include the boolean word list (`1/true/yes/on` / `0/false/no/off`, case-insensitive).
- [x] 1.2 Route the 15 env-overridable `ART_SD_*` settings through the helpers: `ART_SD_BASE_URL` keeps the `SD_WEBUI_BASE_URL` variable name (string: present-non-empty wins, absent/blank → `http://127.0.0.1:7860`); `ART_SD_TIMEOUT_SECONDS` / `ART_SD_STEPS` (int, positive), `ART_SD_CFG_SCALE` (float, positive), `ART_SD_SAMPLER` / `ART_SD_SCHEDULER` / `ART_SD_CHECKPOINT` (`_env_str`), the four `ART_SD_{SCENE,PORTRAIT}_{WIDTH,HEIGHT}` (int, positive, multiple of 8), the three caps (int, positive), `ART_SD_PREPIN_SAMPLES_FORMAT` (bool).
- [x] 1.3 Route `ART_SCHEDULER_ENABLED` (bool), `ART_SCHEDULER_INTERVAL_SECONDS` / `ART_SCHEDULER_LIMIT` (int, positive), and `ELOSERN_VUE_CLIENT` (bool) through the helpers. Confirm `GLOBAL_SCRIPTS` still reads the interval at script-creation time, and that the webclient template keeps consuming the effective `ELOSERN_VUE_CLIENT`.
- [x] 1.4 Verify `ART_SD_CLIENT` and `ART_STORE_ROOT` read no environment variable (no helper call, no `os.environ` reference) and that the existing `SD_WEBUI_BASE_URL` read is now helper-routed with identical behavior.
- [x] 1.5 In `server/conf/test_settings.py`, pop every env-backed override name (the 18 same-named keys plus `SD_WEBUI_BASE_URL`) from `os.environ` before the `from server.conf.settings import *` line (design D4.5).

## 2. Tests

- [x] 2.1 Create `server/conf/tests/test_env_overrides.py` (plain `unittest.TestCase`, no DB): subprocess harness helper that runs `sys.executable -c "import server.conf.settings as s; …"` with the repo root as cwd and a curated env (copy of `os.environ` minus `DJANGO_SETTINGS_MODULE` and any `ART_*` / `SD_WEBUI_BASE_URL` / `ELOSERN_VUE_CLIENT` keys), mirroring `world/ai/tests/test_profiles.py`.
- [x] 2.2 Defaults test: unset env → every `ART_SD_*`, `ART_SCHEDULER_*`, and `ELOSERN_VUE_CLIENT` setting equals the documented default (the values `test_art_settings.py` pins).
- [x] 2.3 Table-driven coercion tests: one subprocess case per env-backed setting — all 19 — each asserting the exact coerced value AND Python type (print `repr`), covering every boolean word family (`1/true/yes/on`, `0/false/no/off`), the float, all four dimension bindings (passing multiples of 8), blank-means-default for a typed knob and a URL, and free-text blank vs. content for sampler/scheduler/checkpoint.
- [x] 2.4 Fail-closed tests per rule family: non-integer and zero and negative for positive-bound ints, non-numeric and `0` / negative for `ART_SD_CFG_SCALE`, out-of-list boolean word, non-multiple-of-8 and zero/negative dimension — each asserting nonzero exit AND stderr containing `ImproperlyConfigured` and the variable name (not just the exit code).
- [x] 2.5 Code-only-seam tests: hostile `ART_SD_CLIENT` / `ART_STORE_ROOT` env values → effective settings unchanged.
- [x] 2.6 Precedence test: subprocess pre-seeds `sys.modules["server.conf.secret_settings"]` with a synthetic `types.ModuleType` defining `ART_SD_TIMEOUT_SECONDS = 90` while the env sets `120` → effective value `90` (mechanism verified during design).
- [x] 2.7 Sanitization test: subprocess sets `MUD_TEST_SETTINGS=1`, fakes `sys.argv = ["evennia", "test"]` (the test-settings import guard), sets `ART_SD_STEPS=12`, imports `server.conf.test_settings`, and asserts the effective `ART_SD_STEPS` is the default `30` (requires task 1.5).
- [x] 2.8 Inventory test (pure filesystem + `ast`): parse active `KEY=` lines from `.env.example`; assert each key is an environment-read string literal extracted from the `server/conf/settings.py` AST or belongs to an explicit reviewed key-to-reader allow-list (`OLLAMA_BASE_URL` via `world/ai/profiles.py`; `PROMPTS_DIR`, `EVENNIA_SUPERUSER_*`, `CONTAINER_UID`, `IMAGE_TAG`, `VERSION`, `RELEASE` via compose.yaml/Containerfile; `MUD_TEST_SETTINGS`, `DJANGO_SETTINGS_MODULE`, `TEST_DB_PATH`, `OPENSPEC_TEST_EVIDENCE`, `COVERAGE_FILE`, `ELOSERN_BROWSER_*` via the test/browser harness); assert `docs/development/settings-and-environment.md` exists, is linked from `docs/_sidebar.md`, and contains one table row per env-backed setting whose name column matches the settings AST and whose row names type/default/rule; assert `docs/gm/prompts.md` links the guide.
- [x] 2.9 Add the module-docstring constraint line to `server/conf/tests/test_art_settings.py` (CI/test invocations must not export `ART_SD_*` overrides; D4.5 sanitization makes this belt-and-braces).
- [x] 2.10 Annotate each test method with `@covers_requirement` using the canonical `settings-environment-overrides::<slug>` IDs for the five delta requirements (IDs verified against `tools.spec_traceability list` at archive-sync time; the check gate only accepts them once the spec is synced).
- [x] 2.11 Confirm the new module is owned by the manifest's `server` package label WITHOUT touching `.github/evennia-shards.json`, via `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.

## 3. Run the focused tests

- [x] 3.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb server.conf.tests.test_env_overrides server.conf.tests.test_art_settings` green.
- [x] 3.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb server web.webclient world.art` green (settings consumers: template flag + scheduler scripts + art worker).
- [x] 3.3 Smoke: `ART_SD_STEPS=twelve uv run --locked python -c "import server.conf.settings"` fails naming the variable; the same command without it succeeds.

## 4. Documentation

- [x] 4.1 Rewrite `.env.example`: replace the inert `ART_SD_*` warning section with commented example entries for all 18 new variables (own-line comments, types, defaults, bounds; never an uncommented empty typed entry); fix the trailing-comment style on the existing harness entries; keep pre-existing sections accurate.
- [x] 4.2 Write `docs/development/settings-and-environment.md` (zh-tw): three layers + precedence; full variable inventory tables (this change's 18, the pre-existing app vars, Evennia-owned vars, harness/test vars) with type/default/validation; what stays in `secret_settings.py` (secrets, `LLM_PROFILES`, `ART_SD_CLIENT`, `ART_STORE_ROOT` and why); bare-metal export recipe; restart/reload rule; the 4-step "make a setting env-overridable" recipe; troubleshooting row stating that an invalid value prevents EVERY Evennia process importing the settings (portal and server alike — disabling the art scheduler does not recover) and that recovery is correcting the variable and restarting.
- [x] 4.3 Add the sidebar entry under 開發者指南 in `docs/_sidebar.md`; give the `ART_SD_*` table in `docs/gm/prompts.md` an environment-variable column and link the guide; add a cross-link from `docs/gm/operations.md`.
- [x] 4.4 Verify the docs site renders the new page (`uv run --locked python -m http.server --directory docs 3000`, browser check of the sidebar link and tables).

## 5. Archive-time traceability sync

- [x] 5.1 At archive: sync the delta into `openspec/specs/settings-environment-overrides/spec.md`, confirm the five `covers_requirement` IDs against `uv run --locked python -m tools.spec_traceability list`, and land code + tests + spec sync + archive as one commit chain (7893d28 precedent).
- [x] 5.2 `uv run --locked python -m tools.spec_traceability check` green; `openspec validate --all --strict` green; `uv run --locked python -m compileall -q server` clean; `git diff --check` clean.
