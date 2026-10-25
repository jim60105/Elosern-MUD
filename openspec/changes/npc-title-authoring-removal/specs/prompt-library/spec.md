# Spec Delta

## MODIFIED Requirements

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
  `display_name` is required on every `npc_req` entry, so the guidance text exists only in the prompt
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
- **THEN** it states that the rolled names are 僅供靈感 — directly usable or adjustable to the character's sex and background, countering same-name bias — while every `npc_req` entry MUST carry the required identity fields `display_name`

#### Scenario: An admin rewriting the text block without the token still loads cleanly
- **WHEN** an admin rewrites the `text` block without the `{name_inspiration}` token
- **THEN** it SHALL still load cleanly — a key renders with the tokens it declares

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written
