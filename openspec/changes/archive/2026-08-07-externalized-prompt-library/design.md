## Context

Every LLM prompt in the game is currently a hardcoded Python string constant:

- `world/ai/narrator.py::_SYSTEM_MESSAGE` — story narration system prompt.
- `world/ai/npc_dialogue.py::_system_message()` — NPC dialogue system prompt template with
  `{name}` / `{desc}` / `{location}` placeholders.
- `world/ai/scenario_director.py::_SYSTEM_MESSAGE` — quest-generation system prompt.
- `typeclasses/npcs.py::_DEFAULT_THINKING_MESSAGES` — per-entity thinking feedback template.
- `world/art/subjects.py::_APPROVED_STYLE` and the inline `character_description()` /
  `monster_description()` f-strings — the deterministic descriptions that become image prompts.

Changing any of them is a code change plus an image rebuild. The project is a single-machine
deployment (Ollama + sd-webui on the same host) whose owner wants to tune AI behavior without
touching Python. Design doc D9 already draws the line for tunable data — "balance numbers are data
that should be tunable without touching Python" — and prompts are exactly that class of content.

## Goals / Non-Goals

**Goals:**
- One top-level `prompts/` data folder as the sole source of truth for every LLM prompt, shipped
  in the repo, baked into the image, and bind-mounted into the container so edits apply after a
  restart or reload.
- A `world/prompts/` read-only registry package: YAML loader, per-key validation (known keys,
  non-empty text, size bounds, placeholder allowlists), deterministic rendering, and a validate
  CLI admins can run before restarting.
- Bounded per-key startup loading with named errors: a broken prompt file marks only its key
  unavailable with the file, key, and problem in the logged error, the consuming generative layer
  degrades to its existing deterministic path, and server startup continues.
- Preserve byte-identical prompt determinism: the initial YAML ships the current prompt text
  verbatim, and the frozen registry renders identical output for identical input.
- A Traditional Chinese docsify page (`docs/gm/prompts.md`) explaining how to edit prompts,
  registered in `docs/_sidebar.md`.

**Non-Goals:**
- Not moving `world/ai/director_templates.py` (structured `QuestBlueprint` proposal values, not
  prompt text).
- Not moving output JSON schemas or `LLM_PROFILES` (endpoint configuration, already
  settings-driven).
- Not changing any deterministic degrade path, the art queue/worker contract, or the
  single-writer boundary.
- Not inventing LLM behavior for character creation: the wizard remains deterministic; the library
  simply registers a forward-declared `character_creation` prompt key (the same seam idiom the
  design already uses for the unused `scene_builder` LLM profile) so the prompt lives here when the
  feature that consumes it lands.
- No backward compatibility or migration — the project has no released users.

## Decisions

### D-1: A top-level `prompts/` directory, not code constants and not a package directory

Prompts live in repo root `prompts/` (one YAML file per layer), `COPY`ed into the image at
`/app/prompts` and bind-mounted from the host. Rationale:

- Data stays outside importable code, so a mount can never shadow a package (the same lesson the
  design applied when art output moved out of `world/art/`).
- The folder is the admin-facing surface: `prompts/narrator.yaml`,
  `prompts/npc_dialogue.yaml`, `prompts/scenario_director.yaml`, `prompts/npc.yaml`,
  `prompts/art.yaml`, and `prompts/character_creation.yaml` (forward seam).
- The code registry maps each key to its file, so the loader knows exactly which file to read for
  which key and reports `file → key` in errors.

Alternative considered: embedding defaults in Python with YAML as override. Rejected — two copies
of prompt text would drift; the design's D9 precedent is "data that should be tunable without
touching Python", so YAML files are the single source of truth, and tests read the repo's own
`prompts/` directory.

### D-2: Frozen keyed registry in `world/prompts/`, validated at load

`world/prompts/` is a read-only registry package (same class as `world/lore/`), a leaf that
imports only standard library, Django settings for the root, and YAML parsing:

- `registry.py` — `PROMPT_SPECS`: each known key declares its allowed placeholder tokens and a
  max length. Keys: `narrator.system`, `npc_dialogue.system`, `scenario_director.system`,
  `npc.thinking`, `art.style`, `art.character_description`, `art.monster_description`, and the
  forward-declared `character_creation.system`.
- `loader.py` — reads `prompts/*.yaml` under `PROMPT_ROOT` (setting, default
  `<GAME_DIR>/prompts`), validates, and builds a frozen mapping. Any failure is recorded as a
  named `PromptLibraryError` naming the file, key, and problem — unknown key, duplicate key,
  missing file, empty text, over-length text, or a `{token}` outside the key's allowlist — while
  the remaining keys stay available (see D-3 for the per-key bounded behavior). Duplicate keys
  are detected with a custom `yaml.SafeLoader` subclass that rejects repeated mapping keys —
  `yaml.safe_load()` silently keeps the last value, which would hide an admin's edit.
- `render.py` (or part of the loader module) — `render_prompt(key, **values)` substitutes only
  allowlisted tokens via an exact `{token}` regex that rejects tokens adjacent to another brace
  (so `{{name}}` passes through untouched); everything else in the text, including JSON example
  braces such as `{"name": "…"}`, passes through unchanged. Supplied `**values` outside the key's
  allowlist are rejected with a named error, so a consumer typo such as `namme=` fails loudly
  instead of silently dropping NPC context.

Placeholder allowlists live in code, not in the YAML: they are wired to the concrete data each
caller passes (`name`, `desc`, `location`, …), so admins edit only the `text` block while the
loader still catches typos like `{nmme}`.

### D-3: Bounded per-key failure at startup; auto-load on first use

A broken prompt file must never take the deterministic game offline. `load_prompt_library()` at
startup validates every key and records failures per key; a key that fails validation or is
missing is marked unavailable, a named `PromptLibraryError` is logged with file, key, and
problem, and the consuming generative layer resolves to its existing deterministic degrade path
(narrator → template renderer, npc-dialogue → greeting or silence, scenario-director → template
pool, art → unchanged descriptions) for as long as the key is unavailable. Server startup
continues. The unused `character_creation.system` seam can never block startup: its failure is a
logged warning only. This mirrors the offline-playability invariant: an invalid prompt is treated
exactly like an unavailable LLM.

`render_prompt()` triggers a one-time auto-load on first use so pure-logic tests and offline
callers get the repo's own `prompts/` directory without server startup; an explicit
`load_prompt_library(root=...)` and a `reset_prompt_library()` give tests deterministic control
(used in `try/finally` so one test's root cannot leak into the next). The first load is guarded by
a lock so concurrent callers cannot double-load. Prompt edits take effect only after a validate +
full restart (or reload): the loader reads the files once at load time, never on every call.
`evennia reload` re-runs `at_server_start`, so prompt edits apply on reload as well as restart.

### D-4: Deterministic rendering keeps the prompt-construction contracts intact

The three `build_*_prompt` functions keep their exact signatures, bounds, and serialization; only
the system-message source changes from a module constant to `render_prompt(...)`. The existing
"identical inputs produce byte-identical prompts" tests keep passing because the initial YAML
contains the current text verbatim. `typeclasses/npcs.py::_thinking_text()` keeps the per-entity
`thinking_messages` attribute as an override and falls back to `render_prompt("npc.thinking",
name=...)` when unset. `world/art/subjects.py` renders `art.style`,
`art.character_description`, and `art.monster_description`; `scene_description` continues to
return the lore-owned `scene_sentence` verbatim. Editing a style/description template changes the
source-description hash, which the existing art pipeline already reports for staff review instead
of silently replacing completed images.

### D-5: Container: bake defaults, bind-mount for admin edits

- `Containerfile`: add `COPY --chown=root:0 prompts/ /app/prompts/` so image-only runs work.
- `compose.yaml`: add `${PROMPTS_DIR:-./prompts}:/app/prompts:ro` to the `evennia` service
  volumes. The server never writes prompts, so the mount is read-only; admins edit files on the
  host and restart (or reload). `.containerignore` does not exclude `prompts/`. The same mounted
  directory is world-readable inside the container, so an external art worker that wants to reuse
  the shipped prompt fragments can read it too — the worker contract (JSON-lines over
  `ART_WORKER_CMD`) is unchanged.
- `server/conf/settings.py`: `PROMPT_ROOT = os.path.join(GAME_DIR, "prompts")`, overridable via
  the `PROMPT_ROOT` environment variable for bare-metal or nonstandard layouts.

Alternative considered: a persistent named volume seeded from image defaults. Rejected — prompts
are configuration, not generated state; a host bind mount is the most direct way for the admin to
edit them, and the image copy keeps standalone runs working.

### D-6: Validate CLI and docs

A `world/prompts/validate.py` entry (`uv run --locked python -m world.prompts.validate`) loads the
library from `PROMPT_ROOT` and prints per-key status or every named error with exit code 1 —
the same pattern as `world.imports.validate`. The docsify page `docs/gm/prompts.md` (Traditional
Chinese, registered in `docs/_sidebar.md` under 遊戲主持人) documents: where prompts live in the
repo and the container, the YAML schema, the per-key table with placeholder allowlists, literal
brace rules (`{{` escapes), how edits take effect (validate → restart or reload, never live
edits), the bounded per-key failure behavior, the `PROMPTS_DIR` override and read-only mount, and
how to preview the docs site locally.

## Risks / Trade-offs

- **A broken prompt file degrades only its layer** → the named error is logged with file, key,
  and problem, the validate CLI catches it before restart, and reverting the file restores the
  previous behavior; the deterministic game stays fully playable throughout.
- **Placeholder substitution versus literal braces** → only allowlisted `{token}` forms not
  adjacent to another brace are replaced; JSON examples, `{{` escapes, and arbitrary braces pass
  through, and unknown tokens are load-time errors.
- **Prompt text duplication between YAML and the git history of the Python constants** → the
  initial YAML is a verbatim move; the Python constants are deleted, so there is exactly one copy
  going forward.
- **Tests that previously asserted constant content** → they keep asserting the same substrings;
  the loader test suite pins the registry contract (keys, allowlists, bounds, per-key failure),
  and full-string equality tests pin the shipped YAML against the original constants byte-for-byte.
- **Mount shadowing** → the bind mount covers the image copy, but both carry the same repo
  content; nothing writes either location, so there is no divergence risk.
- **Admin edits do not apply live** → documented: validate first, then restart or reload; the
  loader reads files once per load, never per call.
