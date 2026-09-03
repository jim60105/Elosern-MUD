# prompt-library — delta

## ADDED Requirements

### Requirement: The scenario-director key is registered with the name-inspiration placeholder and carries the naming guidance
`world/prompts/registry.py` SHALL register `scenario_director.system` with an allowlist containing
exactly the `name_inspiration` placeholder, and `prompts/scenario_director.yaml` SHALL be the sole
place defining both the naming-guidance sentence (the rolled names are 僅供靈感 — directly usable or
adjustable to the character's sex and background, and filling `display_name` is recommended, not
required) and the `{name_inspiration}` token. The ScenarioDirector layer SHALL consume the key at
runtime by rendering that placeholder with its deterministically rolled inspiration bank. An
admin rewriting the `text` block without the token SHALL still load cleanly (a key renders with the
tokens it declares), and a typo in a placeholder name SHALL be caught by the loader's existing
allowlist validation.

#### Scenario: The key is registered with its placeholder and consumed
- **WHEN** the prompt registry is queried for `scenario_director.system`
- **THEN** the key exists with its default text, its allowlist contains exactly `name_inspiration`,
  and the ScenarioDirector prompt builder renders it with a rolled name bank at runtime

#### Scenario: The shipped YAML carries the inspiration-only guidance beside the token
- **WHEN** the shipped `prompts/scenario_director.yaml` text is inspected
- **THEN** it contains the `{name_inspiration}` token and the guidance that the names are
  inspiration only with `display_name` recommended but optional, so the guidance text exists only
  in the prompt folder and never as a Python constant

#### Scenario: An out-of-allowlist placeholder typo is still rejected
- **WHEN** a prompt file declares `{name_inspiraton}` (or any placeholder outside the key's
  allowlist) for `scenario_director.system`
- **THEN** the loader rejects that key with the named `PromptLibraryError` and the layer keeps
  degrading through the existing per-key failure path
