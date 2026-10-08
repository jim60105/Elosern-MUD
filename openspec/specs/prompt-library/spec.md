## Purpose

Defines the prompt library: the top-level `prompts/` data folder as the sole source of every LLM prompt the application owns, the `world/prompts/` read-only registry package that validates and renders it deterministically, the bounded per-key failure behavior that keeps the deterministic game playable when a prompt file is broken, and the validate CLI admins run before restarting.

## Requirements

### Requirement: The prompt library is the single source of truth for every LLM prompt
The project SHALL store all LLM prompt text in YAML files under one top-level `prompts/` directory
in the repo root, one file per layer or domain: `narrator.yaml`, `npc_dialogue.yaml`,
`scenario_director.yaml`, `scene_builder.yaml`, `npc.yaml`, `art.yaml`, and `character_creation.yaml`.
The folder SHALL be the only place prompt text is defined.

#### Scenario: Every generative layer has a prompt file
- **WHEN** the `prompts/` directory is inspected
- **THEN** it contains `narrator.yaml`, `npc_dialogue.yaml`, `scenario_director.yaml`,
  `scene_builder.yaml`, `npc.yaml`, `art.yaml`, and `character_creation.yaml`, each declaring
  `schema_version: 1` and a `prompts:` mapping whose keys match the code-defined registry

#### Scenario: Prompt text exists only in the folder
- **WHEN** the codebase is searched for the narrator or scenario-director system-message text
- **THEN** the only occurrences are inside `prompts/*.yaml`, not in any Python module

#### Scenario: The character-creation key is registered with its concept placeholders
- **WHEN** the prompt registry is queried for `character_creation.system`
- **THEN** the key exists with its default text, its allowlist contains `concept` and
  `race_catalog`, and the `character_creation` generative layer consumes it at runtime

#### Scenario: The scene-flavor key is registered with its four placeholders and consumed
- **WHEN** the prompt registry is queried for `scene_builder.system`
- **THEN** the key exists with its default text, its allowlist contains exactly
  `scene_sentence`, `quest_context`, `room_name`, and `region`, and the scene-flavor layer renders
  it (a guarded test proves the registration and the consumer)

#### Scenario: Each prompt file declares the v1 schema envelope
- **WHEN** a prompt YAML file is read
- **THEN** it SHALL declare `schema_version: 1` and a `prompts:` mapping of prompt key to text block

#### Scenario: No prompt text constants in code
- **WHEN** Python modules are inspected for prompt text
- **THEN** they SHALL NOT contain prompt text constants, and the removed hardcoded strings SHALL NOT be duplicated anywhere in code

### Requirement: The loader validates every prompt key and bounds failures to the affected layer
`world/prompts/loader.py` SHALL expose `load_prompt_library(root: str | None = None)` that reads
every YAML file under `PROMPT_ROOT` (the Django setting, default `<GAME_DIR>/prompts`) or the
explicit root, validates every key against the code-defined `PROMPT_SPECS` registry, and installs
a frozen mapping used by `render_prompt()`. A key that fails validation or is missing SHALL be
marked unavailable without aborting server startup, keeping the deterministic game fully playable.

#### Scenario: A valid library loads and renders deterministically
- **WHEN** `load_prompt_library()` runs against the repo's `prompts/` directory
- **THEN** every registered key resolves to its text, and two renders of the same key with the
  same values are byte-identical

#### Scenario: A malformed file fails that key, not the server
- **WHEN** a prompt file contains an unknown key, a duplicate key, an empty or over-length text
  block, or a placeholder outside the key's allowlist
- **THEN** loading records a `PromptLibraryError` naming the file, key, and problem, marks only
  that key unavailable, and server startup and the deterministic game continue

#### Scenario: A missing key file degrades its layer instead of blocking startup
- **WHEN** a key in `PROMPT_SPECS` has no file under `PROMPT_ROOT`
- **THEN** the key is marked unavailable with a logged named error, and the layer consuming it
  resolves to its deterministic degrade path while every other layer keeps working

#### Scenario: Duplicate YAML keys are rejected, never silently merged
- **WHEN** a prompt file repeats a mapping key at the top level or inside a `prompts:` entry
- **THEN** loading rejects the file with a `PromptLibraryError` naming the duplicated key, and no
  "last value wins" silent override occurs

#### Scenario: First use auto-loads from the default root
- **WHEN** `render_prompt()` is called before any explicit `load_prompt_library()`
- **THEN** the library auto-loads once from `PROMPT_ROOT` and the render succeeds

#### Scenario: Tests can reset and reload with an explicit root
- **WHEN** a test calls `load_prompt_library(fixture_root)` then `reset_prompt_library()`
- **THEN** subsequent renders use the fixture library until the next explicit load, and no state
  leaks between tests

#### Scenario: Validation rejects every named malformation with a PromptLibraryError
- **WHEN** validation runs over the library
- **THEN** it SHALL reject unknown keys, duplicate keys, missing key files, empty or over-length text, and `{token}` placeholders outside the key's allowlist, each with a named `PromptLibraryError` naming the file, the key, and the problem

#### Scenario: Duplicate YAML mapping keys are caught by the parser
- **WHEN** a YAML file repeats a mapping key
- **THEN** duplicate YAML mapping keys SHALL be detected by the loader's YAML parser rather than silently keeping the last value

#### Scenario: Startup loads the library before the AI layer registrations
- **WHEN** `server/conf/at_server_startstop.py::at_server_start()` runs
- **THEN** it SHALL call `load_prompt_library()` before the AI layer registrations

#### Scenario: An unavailable key degrades only its layer with a logged error
- **WHEN** a key is marked unavailable
- **THEN** the consuming generative layer SHALL resolve to its existing deterministic degrade path for as long as the key is unavailable, the named error SHALL be logged, and the deterministic game SHALL remain fully playable

#### Scenario: A character_creation.system failure warns and never blocks startup
- **WHEN** the `character_creation.system` key is registered, validated, and fails
- **THEN** its failure SHALL be a logged warning that never blocks startup

#### Scenario: First use auto-loads once and tests can reset the registry
- **WHEN** `render_prompt()` is used with no explicit load, or `reset_prompt_library()` is called
- **THEN** `render_prompt()` SHALL trigger a one-time auto-load on first use when no explicit load happened, and `reset_prompt_library()` SHALL clear the loaded registry for tests

### Requirement: Prompt rendering substitutes only allowlisted placeholders deterministically
`world/prompts` SHALL expose `render_prompt(key, **values) -> str` that returns the key's loaded
text with only its allowlisted `{token}` placeholders replaced by the supplied string values,
using exact `{token}` matching. Identical text and values SHALL produce byte-identical output.

#### Scenario: Allowlisted placeholders are substituted
- **WHEN** `render_prompt("npc_dialogue.system", name="艾洛西亞", desc="…", location="王都",
  persona="性格：…")` is called
- **THEN** the returned text contains the supplied values in place of `{name}`, `{desc}`,
  `{location}`, and `{persona}` exactly once each

#### Scenario: An empty persona value substitutes without error
- **WHEN** `render_prompt("npc_dialogue.system", name="艾洛西亞", desc="…", location="王都",
  persona="")` is called
- **THEN** the render succeeds and the `{persona}` token is replaced by the empty string — the
  output equals the template text with only the identity placeholders filled, with no literal
  `{persona}` remaining and no error raised

#### Scenario: JSON braces in a prompt pass through untouched
- **WHEN** a prompt containing `{"name": "…", "items": [{"item_key": "healing_potion"}]}` is
  rendered with no matching placeholder values
- **THEN** the braces and JSON structure are unchanged in the output

#### Scenario: Double-braced tokens are literal text, not placeholders
- **WHEN** a prompt contains `{{name}}` or `{{location}}`
- **THEN** those tokens are emitted literally, never substituted, regardless of supplied values

#### Scenario: A placeholder outside the allowlist is rejected
- **WHEN** a prompt text contains a `{token}` not in the key's allowlist
- **THEN** the loader rejects that key with a named `PromptLibraryError` naming the file, key,
  and placeholder, and the key is marked unavailable without aborting startup

#### Scenario: An unknown supplied value name is rejected
- **WHEN** `render_prompt()` is called with a value whose name is not in the key's allowlist
- **THEN** a named error is raised and the value is never silently ignored

#### Scenario: Tokens adjacent to another brace pass through untouched
- **WHEN** a token is adjacent to another brace
- **THEN** it SHALL NOT be substituted, so `{{name}}` and JSON example braces such as `{"name": "…"}` pass through untouched

#### Scenario: A consumer typo in a value name fails loudly
- **WHEN** a consumer passes a supplied value whose name is not in the key's allowlist, such as `namme=`
- **THEN** it is rejected with a named error rather than silently ignored, so the typo fails loudly

#### Scenario: Substitution is complete
- **WHEN** a render supplies values for allowlisted tokens
- **THEN** substitution is complete: every present allowlisted token is replaced exactly once

#### Scenario: The npc_dialogue.system allowlist is exactly four tokens
- **WHEN** the `npc_dialogue.system` key's allowlist is inspected
- **THEN** it is exactly `name`, `desc`, `location`, and `persona`

#### Scenario: Callers always pass persona
- **WHEN** any caller invokes `npc_dialogue.system`
- **THEN** it SHALL pass `persona` on every call — the flattened block when one exists, or an empty string when not — so the `{persona}` token is always substituted and never left literal in rendered output

### Requirement: A validate CLI checks the library without starting the server
`world/prompts/validate.py` SHALL provide a module entry point (`uv run --locked python -m
world.prompts.validate`) that loads the prompt library from `PROMPT_ROOT` and prints either a
per-key success summary or every named error with its file, key, and problem, exiting 0 on
success and 1 on failure, so an admin can verify prompt edits before restarting the server.

#### Scenario: A valid library validates cleanly
- **WHEN** the CLI runs against the repo's `prompts/` directory
- **THEN** it prints a per-key success summary and exits 0

#### Scenario: A broken library reports the named error
- **WHEN** a prompt file contains a validation error
- **THEN** the CLI prints the `PromptLibraryError` message naming file, key, and problem, and
  exits 1

### Requirement: The scenario-director key is registered with the name-inspiration placeholder and carries the naming guidance
`world/prompts/registry.py` SHALL register `scenario_director.system` with an allowlist containing
exactly the `name_inspiration` placeholder, and `prompts/scenario_director.yaml` SHALL be the sole
place defining both the naming-guidance sentence and the `{name_inspiration}` token.

#### Scenario: The key is registered with its placeholder and consumed
- **WHEN** the prompt registry is queried for `scenario_director.system`
- **THEN** the key exists with its default text, its allowlist contains exactly `name_inspiration`,
  and the ScenarioDirector prompt builder renders it with a rolled name bank at runtime

#### Scenario: The shipped YAML carries the inspiration-only guidance beside the required-identity statement
- **WHEN** the shipped `prompts/scenario_director.yaml` text is inspected
- **THEN** it contains the `{name_inspiration}` token and the guidance that the names are
  inspiration only (directly usable or adjustable to sex and background) while `display_name` and
  `title` are required on every `npc_req` entry, so the guidance text exists only in the prompt
  folder and never as a Python constant

#### Scenario: An out-of-allowlist placeholder typo is still rejected
- **WHEN** a prompt file declares `{name_inspiraton}` (or any placeholder outside the key's
  allowlist) for `scenario_director.system`
- **THEN** the loader rejects that key with the named `PromptLibraryError` and the layer keeps
  degrading through the existing per-key failure path

#### Scenario: The ScenarioDirector layer consumes the key at runtime
- **WHEN** the ScenarioDirector layer builds its prompt
- **THEN** it consumes the key at runtime by rendering the `name_inspiration` placeholder with its deterministically rolled inspiration bank

#### Scenario: The naming-guidance sentence states the inspiration-only rule and required identity fields
- **WHEN** the naming-guidance sentence is inspected
- **THEN** it states that the rolled names are 僅供靈感 — directly usable or adjustable to the character's sex and background, countering same-name bias — while every `npc_req` entry MUST carry the required identity fields `display_name` and `title`

#### Scenario: An admin rewriting the text block without the token still loads cleanly
- **WHEN** an admin rewrites the `text` block without the `{name_inspiration}` token
- **THEN** it SHALL still load cleanly — a key renders with the tokens it declares

### Requirement: The NPC persona frame key is registered with exactly the block placeholder
The prompt registry SHALL register `npc_dialogue.persona_frame` in `prompts/npc_dialogue.yaml` with an allowlist of exactly `block`. The NPC dialogue layer SHALL render it only when a persona block exists and SHALL pass the rendered frame as the `persona` value of `npc_dialogue.system`.

#### Scenario: The frame key is registered and consumed
- **WHEN** the prompt registry is queried for `npc_dialogue.persona_frame`
- **THEN** the key exists with its default text, its allowlist is exactly `block`, and a prompt built for an NPC with a card contains the rendered frame around the card block

#### Scenario: No frame without a card
- **WHEN** a prompt is built for an NPC with no persona block
- **THEN** the frame is not rendered and the system message is byte-identical to the pre-persona rendering

#### Scenario: The frame text frames the block as current setting over immutable history
- **WHEN** the `npc_dialogue.persona_frame` text is authored
- **THEN** it SHALL present `{block}` as the speaking NPC's current character setting that governs subsequent replies and SHALL state that earlier conversation and already confirmed events remain history the current setting does not rewrite
