# Design: Env-overridable deployment settings

## Context

`server/conf/settings.py` hard-codes the deployment knobs; only two values derive from the environment today (`ART_SD_BASE_URL` ← `SD_WEBUI_BASE_URL`, `PROMPT_ROOT` ← `PROMPT_ROOT`). Evennia itself has no environment-to-settings mapping (verified by scanning `evennia/settings_default.py` and the launcher: only `TEST_DB_PATH`, `EVENNIA_SUPERUSER_USERNAME/EMAIL/PASSWORD`, and `WEBSOCKET_CLIENT_PROXY_PORT` are read from the environment). `secret_settings.py` is the official override point but is gitignored and containerignored, so it cannot be repo-shared or reach the image. A prior session's `.env` therefore filled itself with inert `ART_SD_*` entries — a silent-failure class this change eliminates by making those entries live.

Verified environment facts:

- `server.conf.settings` imports standalone in a bare `uv run python` subprocess (no Django setup needed), printing only the benign `secret_settings.py not found` line. This makes subprocess-black-box testing viable, following the `world/ai/tests/test_profiles.py` precedent (clean env by stripping `DJANGO_SETTINGS_MODULE`).
- The shard manifest owns server tests via the package label `server`, which the contract resolves by walking `test*.py` under the directory — a new module under `server/conf/tests/` is auto-owned; `.github/evennia-shards.json` must NOT change.
- `test_settings.py` does `from server.conf.settings import *`, so env overrides apply to test runs too.
- compose.yaml passes `.env` twice: shell interpolation for `${VAR:-default}` and `env_file: .env` for the container. Podman-compose forwards an empty `VAR=` as an empty string into the container.

## Goals / Non-Goals

**Goals:**

- Every sd-webui generation/cap knob and art-drain knob becomes settable through a same-named environment variable, validated and coerced at settings import.
- Fail closed on invalid values with an error naming variable, value, and expectation — the antithesis of today's silent inertness.
- Document the configuration model once (Docsify developer guide) and keep `.env.example` as the canonical live-variable inventory.

**Non-Goals:**

- No `.env` auto-loading in Python (no new dependency; compose already injects `.env` for the container path, and bare-metal runs export vars per the documented recipe).
- No hot reload: settings are read at process start/reload, like every other Evennia setting.
- No env override for per-layer LLM tuning (stays in `LLM_PROFILES` / `secret_settings.py`, per `llm-profiles`).
- No secrets through the environment: `SECRET_KEY` and friends stay in `secret_settings.py` (evennia-project-skeleton: secrets never baked; env vars leak through process listings and `compose inspect`, so this change deliberately keeps the env-free-for-secrets line).
- No player-command surface changes.

## Decisions

### D1 — Helper lives in `settings.py` itself, not in a package module

Settings modules cannot safely import project packages at Django settings-load time (import-cycle risk with `world.*` importing Django-backed code). The helpers are two small private functions defined before use in `server/conf/settings.py`:

```python
def _env_str(name, default=""):   # free-text knobs: raw value or default; never coerces
def _env_typed(name, convert, default, *, minimum=None, multiple=None):
    """Absent OR blank-after-strip -> default (an open, empty knob means 'unset').
    Present-with-content -> convert(raw.strip()) with bounds.
    Any conversion/bound failure raises ImproperlyConfigured naming name, raw, rule."""
```

Boolean conversion uses a fixed word list — truthy `1/true/yes/on`, falsy `0/false/no/off`, case-insensitive (a bare `bool("False")` would be True; this trap is exactly why the word list exists). Dimensions (`ART_SD_SCENE_*`, `ART_SD_PORTRAIT_*`) additionally pass `multiple=8` (SDXL-friendliness is an existing settings contract asserted by `test_art_settings.py`). `_env_str` stays for free-text knobs (`ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`): empty-string is their legitimate "server default" value, so no bounds.

Alternative considered: a `world/settings_env.py` helper — rejected: `world/` is subject to the single-writer/registry invariants and `settings.py` must stay importable before the app registry exists; two private functions do not justify a package import.

### D2 — Scope: which knobs go env, which stay code-only

Env-overridable (15 `ART_SD_*` + 3 `ART_SCHEDULER_*` + 1 flag = 19):

- 15 of the 16 `ART_SD_*` settings (all except `ART_SD_CLIENT`, see below): `ART_SD_BASE_URL` (refactored to use the same helper; same behavior), `ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, `ART_SD_CFG_SCALE` (float, positive), `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT` (strings), `ART_SD_SCENE_WIDTH/HEIGHT`, `ART_SD_PORTRAIT_WIDTH/HEIGHT` (int, positive, multiple of 8), `ART_SD_MAX_RESPONSE_BYTES`, `ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS` (int, positive), `ART_SD_PREPIN_SAMPLES_FORMAT` (bool).
- The three `ART_SCHEDULER_*` settings: `ART_SCHEDULER_ENABLED` (bool), `ART_SCHEDULER_INTERVAL_SECONDS`, `ART_SCHEDULER_LIMIT` (int, positive).
- `ELOSERN_VUE_CLIENT` (bool): the Vue/legacy XOR flag becomes env-settable so an operator can execute the documented emergency rollback to the legacy webclient without a rebuild.

Stay code-only, deliberately:

- `ART_SD_CLIENT` — **security**: a same-named env var would let any process environment import an arbitrary dotted path at engine startup (import-injection via env). The seam stays settings/`secret_settings.py`-only: no env read at all.
- `ART_STORE_ROOT` — an env typo silently relocates generated art off the persistent volume; the rare nonstandard-layout case uses `secret_settings.py` explicitly.
- `DATABASES`, ports, `SERVERNAME` — Evennia/infrastructure-owned, fixed by the design doc.

The settings block declares 16 `ART_SD_*` settings in total (base URL, timeout, steps, cfg, sampler, scheduler, checkpoint, 4 sizes, 3 caps, prepin flag, client class); every one except `ART_SD_CLIENT` gains an env path.

### D3 — Precedence: default < env < secret_settings, unchanged structure

`secret_settings.py` is imported at the bottom of `settings.py` today, so assigning env-derived values above that import yields `default < env < secret_settings` with zero structural change. This is kept: `secret_settings.py` remains the final word for operator-private overrides (and the escape hatch when an inherited environment carries unwanted vars).

### D4 — Fail closed with a named, actionable error

Any present-but-invalid value raises `django.core.exceptions.ImproperlyConfigured` with the message `setting <NAME>: invalid environment value '<raw>' (<rule>)`. Rationale: silent fallback would restore exactly the failure mode this change exists to kill. Accepted tradeoff (see Risks): a crash-loop in compose is loud and debuggable, which is the desired behavior for a mis-set deployment knob.

### D4.5 — Test settings sanitize the override names

Because `server/conf/test_settings.py` star-imports production settings, an inherited shell/CI `ART_SD_*` value would now silently shift a test run's effective settings (the same silent-inertness class this change kills elsewhere). `test_settings.py` therefore pops every env-backed variable name (the 18 same-named keys + `SD_WEBUI_BASE_URL`) from `os.environ` before importing production settings. Document-only mitigation was rejected: docs are not an isolation mechanism, and the failure would be a confusing unrelated test failure. The override subprocess tests (D5) keep their own curated env and are unaffected — they test the unsanitized production path directly.

### D5 — Test strategy: subprocess black box + in-process defaults

Effective-value and failure behavior can only be observed at settings import, so the new module `server/conf/tests/test_env_overrides.py` runs `uv`-free bare subprocesses (`sys.executable -c "import server.conf.settings as s; print(...)"`) with a curated environment (strip `DJANGO_SETTINGS_MODULE` and any inherited `ART_*`/`SD_WEBUI_BASE_URL`/`ELOSERN_VUE_CLIENT`, following `test_profiles.py`). Coverage is table-driven, not sampled, because a generic helper test cannot catch one omitted or mis-wired assignment: (a) unset → every documented default; (b) one valid override per env-backed setting — all 19, each asserting the exact coerced value AND its Python type via `repr`, so a hard-coded value, a missing `int()` bound, or an accidental string-bool is caught; (c) every distinct rule once per family — zero and a negative for each positive-bound int, a non-numeric and a non-positive float for `ART_SD_CFG_SCALE`, both boolean word families plus an out-of-list word, a blank URL, a blank typed knob, free-text blank vs. free-text content, and all four dimension bindings each with a passing multiple of 8 and a failing non-multiple; (d) failure assertions match the stderr text for `ImproperlyConfigured` and the variable name, not just a nonzero exit code; (e) hostile `ART_SD_CLIENT` / `ART_STORE_ROOT` variables → values unchanged; (f) precedence → the subprocess pre-seeds `sys.modules["server.conf.secret_settings"]` with a synthetic `types.ModuleType` (verified mechanism) defining `ART_SD_TIMEOUT_SECONDS = 90` while the env sets `120`, asserting `90`; (g) sanitization → importing `server.conf.test_settings` with `ART_SD_STEPS=12` in the environment yields the default `30`. `test_art_settings.py` stays as the in-process default pinning (now guaranteed stable by D4.5 sanitization).

Placement under `server/conf/tests/` inherits the manifest's `server` package label; editing `.github/evennia-shards.json` would actually break the ownership contract.

### D6 — Docs: one developer guide as the single model description

New `docs/development/settings-and-environment.md` (zh-tw, matching docs site language; sidebar entry under 開發者指南) documents: the three layers and precedence; the full live-variable inventory (this change's 18 new variables + pre-existing `OLLAMA_BASE_URL`, `SD_WEBUI_BASE_URL`, `PROMPT_ROOT`, `PROMPTS_DIR`, `EVENNIA_SUPERUSER_*`, `WEBSOCKET_CLIENT_PROXY_PORT`, `MUD_TEST_SETTINGS`); what stays in `secret_settings.py` (secrets, `LLM_PROFILES`, code-only knobs); the bare-metal export recipe; the reload-restart rule; and the "make a new setting env-overridable" 4-step recipe (helper call → `.env.example` entry + comment → doc table row → test). Cross-link from `docs/gm/prompts.md` (its `ART_SD_*` table gains an env-column) and `docs/gm/operations.md`. `.env.example` header is rewritten: the "NOT environment variables" warning section is replaced by live `ART_SD_*`/`ART_SCHEDULER_*`/`ELOSERN_VUE_CLIENT` entries (comments on their own lines — trailing `#` comments are not stripped by dotenv parsers); trailing-comment style is also cleaned from the existing harness entries.

Alternative considered: a GM-facing page only — rejected: operators of prompts already read `docs/gm/prompts.md` (cross-linked), while the mechanism/precedence model is developer material; one page, two entry points.

## Risks / Trade-offs

- **Crash-loop on typo** (e.g. `ART_SD_STEPS=twelve`): intentional per D4; the error names the variable and value, and the compose logs show it at boot. Blast radius is any Evennia process importing these settings (portal and server alike) — disabling the art scheduler does NOT recover from an invalid unrelated value; recovery is correcting the variable and restarting. The guide's troubleshooting row states exactly this.
- ~~Inherited-env pollution of test runs~~ — resolved structurally by D4.5 (test settings pop the override names), not by documentation; the `ART_SD_STEPS=12 → 30` scenario in the delta spec pins it.
- **Empty `VAR=` under Podman**: podman-compose forwards an uncommented empty `VAR=` as an empty string into the container; typed/boolean knobs treat present-but-empty as "use the default" (chosen over fail-closed here because an empty value carries no intent to corrupt — it is an unset knob that the shell left open), the three free-text knobs legitimately take it as their "server default" value, and `.env.example` ships typed knobs only as commented examples.
- **Traceability timing**: `tools.spec_traceability check` rejects `covers_requirement` IDs not yet in `openspec/specs/`, so the annotated test lands in the archive commit together with the spec sync (the `7893d28` precedent: implementation commit carries tests + delta + synced main spec atomically). During active implementation, local runs use the focused Evennia tests, not the check gate.
- **Settings import side effects grow**: the helper reads `os.environ` at import — already true for `ART_SD_BASE_URL`, `PROMPT_ROOT`, and `LLM_PROFILES`; the new code adds no I/O beyond env lookup and `int`/`float` parsing, keeping import cheap and side-effect-free apart from the sanctioned env read.
