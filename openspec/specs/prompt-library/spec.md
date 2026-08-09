## Purpose

Defines the prompt library: the top-level `prompts/` data folder as the sole source of every LLM prompt the application owns, the `world/prompts/` read-only registry package that validates and renders it deterministically, the bounded per-key failure behavior that keeps the deterministic game playable when a prompt file is broken, and the validate CLI admins run before restarting.

## Requirements

### Requirement: The prompt library is the single source of truth for every LLM prompt
The project SHALL store all LLM prompt text in YAML files under one top-level `prompts/` directory
in the repo root, one file per layer or domain: `narrator.yaml`, `npc_dialogue.yaml`,
`scenario_director.yaml`, `npc.yaml`, `art.yaml`, and `character_creation.yaml`. Each file SHALL
declare `schema_version: 1` and a `prompts:` mapping of prompt key to text block. The folder SHALL
be the only place prompt text is defined; Python modules SHALL NOT contain prompt text constants,
and the removed hardcoded strings SHALL NOT be duplicated anywhere in code.

#### Scenario: Every generative layer has a prompt file
- **WHEN** the `prompts/` directory is inspected
- **THEN** it contains `narrator.yaml`, `npc_dialogue.yaml`, `scenario_director.yaml`, `npc.yaml`,
  `art.yaml`, and `character_creation.yaml`, each declaring `schema_version: 1` and a `prompts:`
  mapping whose keys match the code-defined registry

#### Scenario: Prompt text exists only in the folder
- **WHEN** the codebase is searched for the narrator or scenario-director system-message text
- **THEN** the only occurrences are inside `prompts/*.yaml`, not in any Python module

#### Scenario: The character-creation key is registered with its concept placeholders
- **WHEN** the prompt registry is queried for `character_creation.system`
- **THEN** the key exists with its default text, its allowlist contains `concept` and
  `race_catalog`, and the `character_creation` generative layer consumes it at runtime

### Requirement: The loader validates every prompt key and bounds failures to the affected layer
`world/prompts/loader.py` SHALL expose `load_prompt_library(root: str | None = None)` that reads
every YAML file under `PROMPT_ROOT` (the Django setting, default `<GAME_DIR>/prompts`) or the
explicit root, validates every key against the code-defined `PROMPT_SPECS` registry, and installs
a frozen mapping used by `render_prompt()`. Validation SHALL reject unknown keys, duplicate keys,
missing key files, empty or over-length text, and `{token}` placeholders outside the key's
allowlist, each with a named `PromptLibraryError` naming the file, the key, and the problem;
duplicate YAML mapping keys SHALL be detected by the loader's YAML parser rather than silently
keeping the last value. `server/conf/at_server_startstop.py::at_server_start()` SHALL call
`load_prompt_library()` before the AI layer registrations. A key that fails validation or is
missing SHALL be marked unavailable without aborting server startup: the consuming generative
layer SHALL resolve to its existing deterministic degrade path for as long as the key is
unavailable, the named error SHALL be logged, and the deterministic game SHALL remain fully
playable. The `character_creation.system` key SHALL be registered and validated, but its failure
SHALL be a logged warning that never blocks startup. `render_prompt()` SHALL
trigger a one-time auto-load on first use when no explicit load happened, and
`reset_prompt_library()` SHALL clear the loaded registry for tests.

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

### Requirement: Prompt rendering substitutes only allowlisted placeholders deterministically
`world/prompts` SHALL expose `render_prompt(key, **values) -> str` that returns the key's loaded
text with only its allowlisted `{token}` placeholders replaced by the supplied string values,
using exact `{token}` matching. A token SHALL NOT be substituted when it is adjacent to another
brace, so `{{name}}` and JSON example braces such as `{"name": "…"}` pass through untouched.
Supplied values whose names are not in the key's allowlist SHALL be rejected with a named error,
never silently ignored, so a consumer typo such as `namme=` fails loudly. Identical text and
values SHALL produce byte-identical output, and substitution SHALL be complete: every present
allowlisted token SHALL be replaced exactly once. The `npc_dialogue.system` key's allowlist SHALL
be exactly `name`, `desc`, `location`, and `persona`. Callers of `npc_dialogue.system` SHALL pass
`persona` on every call — the flattened block when one exists, or an empty string when not — so
the `{persona}` token is always substituted and never left literal in rendered output.

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
