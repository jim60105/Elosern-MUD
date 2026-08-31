# Env-overridable deployment settings

## Why

Deployment tuning values — especially the `ART_SD_*` sd-webui generation parameters — are hard-coded in `server/conf/settings.py` and cannot be changed without editing tracked code. The only sanctioned override point, `server/conf/secret_settings.py`, is a gitignored, containerignored Python file: it cannot be shared through the repository, cannot reach the container image, and requires every operator to write Python. The result is a real, already-observed failure mode: a previous session authored a `.env` full of `ART_SD_STEPS=12`, `ART_SD_CHECKPOINT=…` entries that are silently inert, because Evennia has no environment-to-settings mapping and only `SD_WEBUI_BASE_URL` and `PROMPT_ROOT` are explicitly read from the environment. A dead setting produces no error — the server boots happily with the wrong values until someone notices the output — which is the most expensive kind of misconfiguration.

## What Changes

- Add a small typed environment-override helper to `server/conf/settings.py` and apply it to every deployment-tunable knob that currently has no environment path: fifteen of the sixteen `ART_SD_*` generation/cap settings (every one except the `ART_SD_CLIENT` import seam, which stays code-only for security), the three `ART_SCHEDULER_*` drain-control settings, and the `ELOSERN_VUE_CLIENT` load flag (documented emergency rollback to the legacy webclient). Environment variables carry the same names as the settings.
- Overrides are validated and coerced at settings import: integers, positive floats, booleans from a defined truthy/falsy word list, and scene/portrait dimensions additionally constrained to positive multiples of 8. An invalid value fails startup with an error naming the variable, the bad value, and the expected type — never silently falls back to the default.
- Effective precedence becomes: code default < environment variable < `secret_settings.py`, matching the existing `ART_SD_BASE_URL` / `OLLAMA_BASE_URL` precedent and keeping `secret_settings.py` as the final word for operator-private values. `server/conf/test_settings.py` gains a sanitize step that pops every override name from `os.environ` before importing production settings, so a test run's effective settings can never depend on an inherited shell environment.
- Track `.env.example` (already authored, currently untracked) as the single reference for every environment variable this project and Evennia itself actually read, replacing the section that warned that `ART_SD_*` entries were inert — they will now be live.
- Add a Docsify developer guide (`docs/development/settings-and-environment.md`, linked from `docs/_sidebar.md`) documenting the three configuration mechanisms (settings.py defaults, environment overrides, secret_settings.py), the precedence rule, the full live-variable table, and the recipe for making a future setting env-overridable.
- Update the `ART_SD_*` reference table in `docs/gm/prompts.md` so every row states its environment variable.

No player command surface changes; `docs/game/commands.md` and `docs/game/command-reference.md` are untouched. No game-state, lore, or rules behavior changes: this is deployment configuration plumbing only.

## Capabilities

### New Capabilities

- `settings-environment-overrides`: Typed, fail-closed environment-variable overrides for deployment-tunable Evennia settings, the effective precedence order across the three configuration layers, and the operator-facing documentation of how to configure settings.

### Modified Capabilities

None. `internal-art-worker` still reads `ART_SD_*` "from settings" — the settings simply derive their initial values from the environment now, exactly as the spec already permits for `ART_SD_BASE_URL`. `container-image` requirements (env-var-configured GPU services, `.env` excluded from the build context, secrets never baked) are unchanged. `llm-client` / `llm-profiles` are untouched: per-layer LLM tuning stays in `LLM_PROFILES`/`secret_settings.py`.

## Impact

- Affected code: `server/conf/settings.py` (helper + 19 env-backed assignments), `server/conf/test_settings.py` (override-name sanitize), new `server/conf/tests/test_env_overrides.py` (auto-owned by the manifest's `server` package label — `.github/evennia-shards.json` must NOT change), `.env.example` (tracked), `docs/development/settings-and-environment.md` + `docs/_sidebar.md` (new page), `docs/gm/prompts.md` (table update).
- Architectural invariants: the single-writer boundary and lore-registry rules are untouched; consumers keep reading registry/settings values instead of duplicating constants — this change makes the values settable without code edits, which strengthens "consumers must read registry values".
- Spec-test traceability: every new requirement in `settings-environment-overrides` gets a `covers_requirement`-annotated test in the same change. The `spec_traceability check` gate rejects annotations for IDs not yet in `openspec/specs/`, so (following the `7893d28` precedent) the annotated tests, the implementation, and the archive-time spec sync land as one atomic unit; the gate is never weakened.
- No migrations, no backward-compatibility layer: the project is unreleased with zero users, so the previously authored (inert) `.env` entries simply become live with this change — no operator-visible behavior change happens silently because nothing was previously reading them.
- Estimated effort: well under one engineer-day.
