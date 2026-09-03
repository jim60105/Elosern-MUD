# scenario-director — delta

## MODIFIED Requirements

### Requirement: ScenarioDirector prompt construction is deterministic, bounded, and faithful
`world/ai/scenario_director.py::build_scenario_prompt(context)` SHALL return a (system, user) message
pair. The system message SHALL be the prompt library's `scenario_director.system` key rendered via
`render_prompt("scenario_director.system", name_inspiration=<inspiration bank>)` — the library is the
sole source of the system prompt text, and the module SHALL NOT embed it as a Python constant. The
rendered system message SHALL fix the director role in 伊洛瑟恩大陸, the 正體中文 language, the
fidelity rule (reference only known world content, never invent ranks, archetypes, NPC tiers, item
keys, or rewards), and the JSON output contract that is the `QuestBlueprint` shape. The user message
SHALL serialize the request context (requested quest type, allowed rank, issuer branch, anchor)
with stable sorted JSON serialization. The prompt SHALL be bounded by fixed per-field length caps and
a bounded total size, and SHALL contain only plain JSON-compatible data with no live entity
references, so identical input always produces byte-identical prompts.

The system message SHALL additionally carry a deterministic name-inspiration bank: the module SHALL
compute `zlib.crc32` over the serialized bounded request context, roll a fixed number of names
through the read-only `world.rules.namegen.roll_name_for_race(None, "", Random(seed))`, and inject
them as the `name_inspiration` values together with the library text's guidance that the names are
inspiration only — directly usable, adjustable to the character's declared sex and background, and
`display_name` is recommended but optional. The output-schema optionality of `display_name` and
every semantic validator SHALL be unchanged by the injection.

#### Scenario: Identical contexts produce identical prompts
- **WHEN** `build_scenario_prompt()` is called twice with the same context
- **THEN** both calls return byte-identical system and user messages, including an identical
  name-inspiration bank

#### Scenario: The name-inspiration bank is context-seeded and rolled through the rule layer
- **WHEN** `build_scenario_prompt()` renders the system message
- **THEN** every injected name comes from `world.rules.namegen.roll_name_for_race` with a
  `Random` seeded from `zlib.crc32` of the serialized bounded context, and the same context always
  yields the same names while a different context may yield a different bank

#### Scenario: The injected names are framed as inspiration only
- **WHEN** the system message is inspected
- **THEN** the bank is presented with the library text marking the names as 僅供靈感 (adjustable to
  sex and background) and recommending — not requiring — that `npc_req` entries fill `display_name`

#### Scenario: The output contract stays unchanged by the injection
- **WHEN** a blueprint omits `display_name` on every `npc_req` entry, and another blueprint fills
  it with a name not present in the inspiration bank
- **THEN** both validate exactly as before the injection: `display_name` remains optional, no
  validator rejects a bank-external name, and the registered output schema is byte-identical to
  the pre-change schema

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
- **THEN** its template text equals the library's `scenario_director.system` key — the prompt-library
  file is the only place its text (including the naming-guidance sentence) is defined — and the
  module renders it rather than embedding any of the text as a Python constant

## ADDED Requirements

### Requirement: The scenario-director name inspiration reads the namegen rule layer without crossing the single-writer boundary
`world/ai/scenario_director.py` SHALL consume `world.rules.namegen` strictly as a pure read: no
`world/ai/` module SHALL write state through it, and the repository-wide state-writer ban SHALL
carry `world.rules.namegen` on its documented read-only-rule allowlist alongside
`world.quests.characterization`, so the transport-boundary contract test keeps failing any other
`world.rules` import from `world/ai/`.

#### Scenario: The read-only rule allowlist names exactly the pure rule modules
- **WHEN** the AI transport-boundary contract test resolves its read-only allowlist
- **THEN** `world.rules.namegen` and `world.quests.characterization` are the only exemptions under
  the state-writer prefixes, each documented as side-effect-free, and an `world/ai/` module that
  imports any other `world.rules` module still fails the scan

#### Scenario: Prompt construction leaves no generative state behind
- **WHEN** `build_scenario_prompt()` runs to completion with the inspiration bank
- **THEN** no database write, attribute write, or registry mutation occurred, and the rolled names
  exist only inside the returned message strings
