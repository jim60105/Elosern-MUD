# Spec Delta

## MODIFIED Requirements

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

#### Scenario: The monster-description key is registered with exactly the two public identity tokens
- **WHEN** the prompt registry is queried for `art.monster_description`
- **THEN** its allowlist is exactly `description` and `display_name` — never `examples`, because
  the visual registry row carries no examples field and multi-species examples are forbidden in a
  monster description — and the art subject seam renders the key at runtime

#### Scenario: Each prompt file declares the v1 schema envelope
- **WHEN** a prompt YAML file is read
- **THEN** it SHALL declare `schema_version: 1` and a `prompts:` mapping of prompt key to text block

#### Scenario: No prompt text constants in code
- **WHEN** Python modules are inspected for prompt text
- **THEN** they SHALL NOT contain prompt text constants, and the removed hardcoded strings SHALL NOT be duplicated anywhere in code

## ADDED Requirements

### Requirement: Prompt-library tests verify program logic, not shipped wording
Prompt tests SHALL assert code-level contracts for every prompt file — key loads, token/allowlist
parity, supplied-value substitution, render determinism, and degrade-path registry equality — and
SHALL NOT compare rendered output against literal shipped `prompts/*.yaml` wording.

#### Scenario: Determinism is two renders, not a wording pin
- **WHEN** a prompt-library test renders a shipped key twice with identical values
- **THEN** it asserts the two renders are byte-identical and that every token the template actually
  selects is substituted exactly as many times as the template spells it, with no unsubstituted
  `{token}` remaining — a declared token the template does not select is inert and is never
  required to appear — and it never compares the output to a literal shipped-template sentence

#### Scenario: Verbatim shipment pins retire for every prompt file
- **WHEN** the prompt suite is inspected for byte-for-byte comparisons of rendered shipped-library
  text against test-file constants (narrator, scenario director, npc dialogue, npc thinking,
  scene builder, action options, art descriptions)
- **THEN** no prompt-library-obligation test pins shipped sentences verbatim; each such check is
  replaced by the logic contract (loads, token parity, substitution of supplied values, render
  determinism), while consumer capability content probes stay with their owning capability tests

#### Scenario: Short semantic probes stay with the consumer capability
- **WHEN** a consumer capability scenario names contract vocabulary its system message must fix
  (e.g. the role, language, or fidelity phrases it lists)
- **THEN** the consumer capability's own prompt test MAY assert those short phrases appear, and
  that obligation lives outside the prompt-library suite's shipped-sentence ban

#### Scenario: Placeholder parity is guarded for both art description keys
- **WHEN** the shipped `art.character_description` and `art.monster_description` templates are
  compared against their `PROMPT_SPECS` allowlists
- **THEN** each template's `{token}` set is a subset of its allowlist (a shipped token outside the
  allowlist is already a load-time unknown-placeholder error) and each allowlist carries exactly
  its contract's tokens — the character key's five tokens, and the monster key's `description` plus
  `display_name`, never `examples` — so a token added to the allowlist without the contract fails
  the parity test, a shipped template that selects a subset of its declared tokens stays legal, and
  no declared token can be missing at render time

#### Scenario: A wording-only shipped edit breaks no test
- **WHEN** a deployment retunes a shipped template's framing wording inside its existing token
  skeleton — appending pose, lighting, or LoRA/quality tags as a prompt-authoring edit does — and
  the prompt suite plus the description-composition suites run against that wording
- **THEN** every test stays green, because no test compares rendered shipped-library output to
  literal framing text; only adding an undeclared `{token}` to a template breaks a test, through
  the unknown-placeholder load error, while adding an allowlisted token or dropping a declared one
  stays green because a key renders with the tokens it declares

#### Scenario: Brace pass-through is exercised on test-owned fixtures
- **WHEN** the loader's brace pass-through contract (a `{{token}}` or a JSON example brace such as
  `{"name": "…"}` stays literal no matter what values are supplied) is tested
- **THEN** the assertion runs against a test-owned inline fixture template carrying those brace
  forms, so the loader behavior stays covered without pinning the shipped files' JSON example
  fragments, whose content a deployment may retune word for word

#### Scenario: Semantic probes persist only on scenario-named vocabulary
- **WHEN** a prompt test asserts short shipped-text phrases as semantic contract probes (role,
  language, fidelity, or output-contract vocabulary)
- **THEN** the phrases it names are vocabulary spelled out in the requirement scenario its
  `@covers_requirement` cites — e.g. the persona frame's current-setting-over-history framing terms
  or the scenario-director's 僅供靈感 guidance terms — and a phrase no owning scenario names is
  dropped from the assertion rather than pinned incidentally

#### Scenario: Composition claims are asserted over test-owned framing
- **WHEN** a description-composition test needs to assert an ordering, exclusion, bound, or
  append claim rather than a library-seam claim
- **THEN** it authors its own inline prompt-file fixture with test-owned framing and asserts the
  claim against that fixture, so the claim holds for any framing the deployment later authors

#### Scenario: The monster contract is asserted on logic, not tokens-in-text
- **WHEN** `render_prompt("art.monster_description", description=…, display_name=…)` is called
  against a fixture template that uses only one of the two tokens
- **THEN** the render succeeds — an unused supplied value is inert — while supplying `examples=`
  raises `UnexpectedPromptValueError` because it is outside the allowlist
