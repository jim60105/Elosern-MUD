## Why

All LLM prompts are currently hardcoded Python string constants scattered across
`world/ai/narrator.py`, `world/ai/npc_dialogue.py`, `world/ai/scenario_director.py`,
`typeclasses/npcs.py`, and `world/art/subjects.py`. Adjusting any prompt — story narration,
NPC dialogue, quest generation, image descriptions, or future character generation — requires a
code change and a rebuild, which is exactly wrong for a single-machine deployment where an admin
wants to tune AI behavior without touching code.

## What Changes

- Create a single top-level `prompts/` data folder as the **sole source of truth** for every LLM
  prompt the application owns: narrator, NPC dialogue, scenario director, NPC thinking feedback,
  and the art (image) description fragments — the approved visual style and the character/monster
  description templates. The hardcoded Python prompt constants are removed and replaced by
  registry lookups. The full image-generation prompt remains authored by the external art worker
  per design D11 (a swappable command); the mounted `prompts/` folder is world-readable inside the
  container so the worker can reuse it, but the worker contract itself is unchanged.
- Add a `world/prompts/` read-only registry package: a startup loader that reads every `*.yaml`
  file under `prompts/`, a validated frozen prompt registry with per-key placeholder allowlists,
  and deterministic template rendering. Validation failures are **bounded per key**: the affected
  generative layer degrades to its existing deterministic path (template renderer, greeting or
  silence, or the quest template pool) with a named error logged, and the server keeps starting —
  a broken prompt file can never make the deterministic game unplayable. A strict validate CLI
  surfaces every error before restart.
- Mount `prompts/` via compose at `/app/prompts` (read-only bind mount, configurable through
  `PROMPTS_DIR`), and bake the same folder into the container image so image-only runs still work.
- Keep the deterministic offline path untouched: prompts are only consumed by generative layers,
  and the existing per-layer degrade paths are unchanged.
- Ship the current prompt text verbatim in the initial `prompts/*.yaml` files so behavior is
  byte-identical until an admin edits a file.
- Add a Traditional Chinese docsify page `docs/gm/prompts.md` (registered in `docs/_sidebar.md`)
  explaining to admins where prompts live, the file format, per-key placeholder allowlists, how
  edits take effect, and how to validate changes.

## Capabilities

### New Capabilities
- `prompt-library`: The `prompts/` folder, the `world/prompts/` loader and frozen registry, per-key
  validation and placeholder allowlists, bounded per-key startup loading (a broken prompt degrades
  only its layer), the `PROMPT_ROOT` setting, the validate CLI, and the compose mount at
  `/app/prompts`.

### Modified Capabilities
- `narrator`: The narrator system prompt is sourced from the prompt library instead of a module
  constant; prompt construction stays deterministic and bounded.
- `npc-dialogue`: The NPC dialogue system prompt template is sourced from the prompt library with
  allowlisted `{name}` / `{desc}` / `{location}` placeholders.
- `scenario-director`: The ScenarioDirector system prompt is sourced from the prompt library.
- `art-subject-model`: The approved visual style fragment and the character/monster description
  templates are sourced from the prompt library; deterministic descriptions and source hashing are
  unchanged.
- `container-image`: The image bakes `prompts/` at `/app/prompts` and compose mounts the host
  folder (bind mount, read-only, `PROMPTS_DIR`-configurable).

## Impact

- **New code**: `world/prompts/` package (loader, registry, render, tests), initial `prompts/*.yaml`
  data files, `docs/gm/prompts.md`, `_sidebar.md` entry.
- **Modified code**: `world/ai/narrator.py`, `world/ai/npc_dialogue.py`,
  `world/ai/scenario_director.py`, `typeclasses/npcs.py`, `world/art/subjects.py`,
  `server/conf/settings.py` (`PROMPT_ROOT`), `server/conf/at_server_startstop.py` (startup load),
  `Containerfile` (COPY `prompts/`), `compose.yaml` (bind mount).
- **Tests**: new `world/prompts/tests/`; existing narrator / npc-dialogue / scenario-director /
  art tests keep passing because the shipped prompt text is identical; existing spec-traceability
  annotations remain valid.
- **Out of scope**: `world/ai/director_templates.py` (structured quest-proposal data, not prompt
  text), LLM endpoint profiles (`LLM_PROFILES`), output JSON schemas, the deterministic
  degradation paths, and the external art worker's own prompt-authoring (design D11 swap point).
- **No backward compatibility needed**: the project has no released users. The `prompts/` folder is
  additive; old prompt constants are removed, not duplicated.
