## 1. Prompt data folder

- [x] 1.1 Create the `prompts/` directory at the repo root with `schema_version: 1` YAML files:
      `narrator.yaml`, `npc_dialogue.yaml`, `scenario_director.yaml`, `npc.yaml`, `art.yaml`, and
      the forward-declared `character_creation.yaml` seam (a valid default text; failure of this
      unused key is a logged warning, never a startup blocker).
- [x] 1.2 Move the narrator system message verbatim into `prompts/narrator.yaml` as the
      `narrator.system` key and delete `_SYSTEM_MESSAGE` from `world/ai/narrator.py`.
- [x] 1.3 Move the ScenarioDirector system message verbatim into
      `prompts/scenario_director.yaml` as the `scenario_director.system` key and delete
      `_SYSTEM_MESSAGE` from `world/ai/scenario_director.py`.
- [x] 1.4 Move the NPC dialogue system-message template verbatim into
      `prompts/npc_dialogue.yaml` as the `npc_dialogue.system` key (with `{name}`, `{desc}`,
      `{location}` placeholders) and delete the f-string from `world/ai/npc_dialogue.py`.
- [x] 1.5 Move the thinking-message template `（{name} 沉思片刻……）` into `prompts/npc.yaml` as the
      `npc.thinking` key; keep `typeclasses/npcs.py`'s per-entity `thinking_messages` attribute as
      an override with the library value as fallback.
- [x] 1.6 Move the approved-visual-style fragment and the character/monster description templates
      into `prompts/art.yaml` as `art.style`, `art.character_description`, and
      `art.monster_description` keys; remove `_APPROVED_STYLE` and the inline f-strings from
      `world/art/subjects.py`.

## 2. Prompt library package

- [x] 2.1 Create `world/prompts/` package with `registry.py` defining `PROMPT_SPECS`: every key
      from task 1 plus `character_creation.system`, each with its allowlisted placeholder tokens
      and a max text length.
- [x] 2.2 Implement `world/prompts/loader.py`: `load_prompt_library(root=None)` reads every
      `*.yaml` under `PROMPT_ROOT` (setting, default `<GAME_DIR>/prompts`; explicit root wins),
      validates keys, duplicates, empty/over-length text, and placeholder tokens, and installs a
      frozen mapping; `PromptLibraryError` names file, key, and problem. Use a custom
      `yaml.SafeLoader` subclass that rejects duplicate mapping keys instead of silently keeping
      the last value.
- [x] 2.3 Implement `render_prompt(key, **values)` with exact `{token}` substitution for
      allowlisted tokens only, never substituting a token adjacent to another brace (`{{name}}`
      stays literal) and rejecting supplied value names outside the key's allowlist; auto-load on
      first use (locked); `reset_prompt_library()` for tests.
- [x] 2.4 Add `world/prompts/validate.py` CLI (`uv run --locked python -m world.prompts.validate`)
      printing per-key status or every named error, exit 0/1.
- [x] 2.5 Add `PROMPT_ROOT` to `server/conf/settings.py` (default `<GAME_DIR>/prompts`,
      env-overridable) and call `load_prompt_library()` in
      `server/conf/at_server_startstop.py::at_server_start()` before AI layer registration;
      loading SHALL record per-key failures without aborting startup (see task 5.1 for the
      degrade-path tests).

## 3. Consumer migration

- [x] 3.1 `world/ai/narrator.py::build_narrator_prompt` sources the system message via
      `render_prompt("narrator.system")`; keep bounds and serialization unchanged.
- [x] 3.2 `world/ai/npc_dialogue.py::_system_message(npc_context)` renders
      `render_prompt("npc_dialogue.system", name=…, desc=…, location=…)`.
- [x] 3.3 `world/ai/scenario_director.py::build_scenario_prompt` sources the system message via
      `render_prompt("scenario_director.system")`.
- [x] 3.4 `typeclasses/npcs.py::_thinking_text()` falls back to
      `render_prompt("npc.thinking", name=…)` when the entity attribute is unset.
- [x] 3.5 `world/art/subjects.py` renders `art.style`, `art.character_description`,
      `art.monster_description`; scene descriptions still return the lore `scene_sentence`
      verbatim; source-description hashing behavior is unchanged.

## 4. Container wiring

- [x] 4.1 Add `COPY --chown=root:0 prompts/ /app/prompts/` to the `Containerfile` app-layout
      stage; confirm `.containerignore` does not exclude `prompts/`.
- [x] 4.2 Add `${PROMPTS_DIR:-./prompts}:/app/prompts:ro` to the `evennia` service volumes in
      `compose.yaml`.

## 5. Tests

- [x] 5.1 Add `world/prompts/tests/` covering: valid load, unknown key, duplicate key (top-level
      and nested, via the custom SafeLoader), missing file, empty/over-length text, unknown
      placeholder token, `{{name}}` literal passthrough, JSON-brace passthrough, rejected
      out-of-allowlist supplied values, auto-load, reset, deterministic rendering, the validate
      CLI exit codes, and per-key bounded failure (a broken key degrades its layer while the
      server keeps starting).
- [x] 5.2 Annotate prompt-library tests with `covers_requirement` for the four new
      `prompt-library::*` requirement IDs and the existing modified requirement IDs
      (`narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful`,
      `npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats`,
      `scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful`,
      `art-subject-model::subject-descriptions-are-deterministic-adult-safe-and-exclude-non-physical-truth`,
      `container-image::compose-yaml-for-local-and-networked-gpu-services`).
- [x] 5.3 Update `tests/test_container_contract.py::test_compose_exposes_ports_persists_state_and_keeps_gpu_services_external`
      to include the new `${PROMPTS_DIR:-./prompts}:/app/prompts:ro` volume assertion and add a
      scenario-level assertion for the read-only prompt mount and the `prompts/` bake.
- [x] 5.4 Run and keep green the existing narrator, npc-dialogue, scenario-director,
      art-subject-model, and LLMNPC tests (their substring assertions still hold against the
      shipped YAML text); update any test that imports the deleted prompt constants. Add
      full-string equality tests pinning each rendered system content against the original
      constant text byte-for-byte.
- [x] 5.5 Run `uv run --locked python -m tools.spec_traceability check` and the affected package
      tests (world.ai, world.art, typeclasses, tests/) until green.

## 6. Admin documentation (docsify)

- [x] 6.1 Write `docs/gm/prompts.md` in Traditional Chinese covering: prompt folder location in
      repo and container, the YAML schema (`schema_version`, `prompts:` mapping), the per-key
      table with placeholder allowlists, literal brace rules (`{{` stays literal), the edit
      workflow (validate CLI → restart or reload — edits never apply live), the bounded per-key
      failure behavior and what admins see in logs, the `PROMPTS_DIR` override and the read-only
      container mount, and how to preview the docs site
      (`uv run --locked python -m http.server --directory docs 3000`).
- [x] 6.2 Register the page in `docs/_sidebar.md` under 遊戲主持人 following the existing sidebar
      conventions.
- [x] 6.3 Verify the docsify page renders (headings, code blocks, sidebar entry) and links are
      consistent with the hash-route layout; confirm the page is reachable from the sidebar.

## 7. Final verification

- [x] 7.1 Run `openspec validate externalized-prompt-library --strict`.
- [x] 7.2 Run the full affected test domains (commands server typeclasses world web.webclient)
      with `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb`
      plus `tests/`, and `git diff --check`.
- [x] 7.3 Confirm no Python module still embeds prompt text (grep the removed phrases against
      `world/` and `typeclasses/`).
