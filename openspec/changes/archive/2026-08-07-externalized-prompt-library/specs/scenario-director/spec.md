## MODIFIED Requirements

### Requirement: ScenarioDirector prompt construction is deterministic, bounded, and faithful
`world/ai/scenario_director.py::build_scenario_prompt(context)` SHALL return a (system, user) message
pair. The system message SHALL be loaded from the prompt library's `scenario_director.system` key
via `render_prompt("scenario_director.system")` — the library is the sole source of the system
prompt text, and the module SHALL NOT embed it as a Python constant. The system message SHALL fix
the director role in 伊洛瑟恩大陸, the 正體中文 language, the
fidelity rule (reference only known world content, never invent ranks, archetypes, NPC tiers, item
keys, or rewards), and the JSON output contract that is the `QuestBlueprint` shape. The user message
SHALL serialize the request context (requested quest type, allowed rank, issuer branch, anchor)
with stable sorted JSON serialization. The prompt SHALL be bounded by fixed per-field length caps and
a bounded total size, and SHALL contain only plain JSON-compatible data with no live entity
references, so identical input always produces byte-identical prompts.

#### Scenario: Identical contexts produce identical prompts
- **WHEN** `build_scenario_prompt()` is called twice with the same context
- **THEN** both calls return byte-identical system and user messages

#### Scenario: An oversized context produces a bounded prompt
- **WHEN** `build_scenario_prompt()` is called with fields exceeding the caps
- **THEN** the returned messages stay within the fixed bounds and remain valid prompt text

#### Scenario: The prompt instructs the blueprint output contract
- **WHEN** the system message is inspected
- **THEN** it directs output as a `QuestBlueprint` JSON object in Traditional Chinese and forbids
  inventing world references beyond the known registries

#### Scenario: The prompt carries plain data, never live references
- **WHEN** the serialized user message is inspected for a request naming branch
  `guild_branch_altoria` and anchor `capital_altoria`
- **THEN** it contains those keys and contains no live entity object anywhere in the serialization

#### Scenario: The system message is sourced from the prompt library
- **WHEN** the ScenarioDirector system message is inspected
- **THEN** it equals `render_prompt("scenario_director.system")` and the prompt-library file is the
  only place its text is defined
