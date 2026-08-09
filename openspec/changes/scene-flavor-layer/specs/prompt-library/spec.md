## MODIFIED Requirements

### Requirement: The prompt library is the single source of truth for every LLM prompt
The project SHALL store all LLM prompt text in YAML files under one top-level `prompts/` directory
in the repo root, one file per layer or domain: `narrator.yaml`, `npc_dialogue.yaml`,
`scenario_director.yaml`, `scene_builder.yaml`, `npc.yaml`, `art.yaml`, and a forward-declared
`character_creation.yaml` seam. Each file SHALL declare `schema_version: 1` and a `prompts:`
mapping of prompt key to text block. The folder SHALL be the only place prompt text is defined;
Python modules SHALL NOT contain prompt text constants, and the removed hardcoded strings SHALL
NOT be duplicated anywhere in code.

#### Scenario: Every generative layer has a prompt file
- **WHEN** the `prompts/` directory is inspected
- **THEN** it contains `narrator.yaml`, `npc_dialogue.yaml`, `scenario_director.yaml`,
  `scene_builder.yaml`, `npc.yaml`, `art.yaml`, and `character_creation.yaml`, each declaring
  `schema_version: 1` and a `prompts:` mapping whose keys match the code-defined registry

#### Scenario: Prompt text exists only in the folder
- **WHEN** the codebase is searched for the narrator or scenario-director system-message text
- **THEN** the only occurrences are inside `prompts/*.yaml`, not in any Python module

#### Scenario: The forward-declared character-creation key is registered but unused
- **WHEN** the prompt registry is queried for `character_creation.system`
- **THEN** the key exists with its default text and a guarded test proves registration, while no
  runtime consumer calls it yet

#### Scenario: The scene-flavor key is registered with its four placeholders and consumed
- **WHEN** the prompt registry is queried for `scene_builder.system`
- **THEN** the key exists with its default text, its allowlist contains exactly
  `scene_sentence`, `quest_context`, `room_name`, and `region`, and the scene-flavor layer renders
  it (a guarded test proves the registration and the consumer)
