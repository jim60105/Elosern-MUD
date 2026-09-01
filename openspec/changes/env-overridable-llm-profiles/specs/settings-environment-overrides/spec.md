# settings-environment-overrides Delta Spec

## ADDED Requirements

### Requirement: LLM profile knobs accept global and per-layer environment overrides
`server/conf/settings.py` SHALL derive the initial value of every `LLMProfile` field from a
declarative knob table covering exactly these knobs and their documented bounds:
`LLM_BASE_URL` (URL string, default `http://127.0.0.1:11434`), `LLM_PATH` (non-empty
string, default `/v1/chat/completions`), `LLM_API_KEY`, `LLM_APP_TITLE`, `LLM_APP_URL`
(free-text strings whose empty value means omit), `LLM_MODEL` (non-empty string, default
`llama3.2`), `LLM_TEMPERATURE` (float `0..2`, default `0.7`), `LLM_FREQUENCY_PENALTY` and
`LLM_PRESENCE_PENALTY` (omittable floats `-2..2`), `LLM_TOP_K` (omittable positive int),
`LLM_TOP_P` (omittable float `0 < x <= 1`), `LLM_REPETITION_PENALTY` (omittable float
`> 0`), `LLM_MIN_P` (omittable float `0..1`), `LLM_TOP_A` (omittable float `>= 0`),
`LLM_REASONING_ENABLED` (tri-state boolean: absent/blank yields `None`, truthy/falsy words
yield `True`/`False`), `LLM_REASONING_EFFORT` (omittable closed set
`minimal/low/medium/high`, case-insensitive, stored lowercase), `LLM_REASONING_STYLE`
(closed set `openrouter/vllm/off`, default `openrouter`), `LLM_MAX_COMPLETION_TOKENS`
(omittable positive int), `LLM_MAX_TOKENS` (positive int), `LLM_TIMEOUT_SECONDS` (positive
int), `LLM_MAX_RETRIES` (non-negative int), `LLM_SUPPORTS_RESPONSE_FORMAT` (boolean), and
`LLM_ENABLED` (boolean). Each knob SHALL additionally be readable from a per-layer
override named `LLM_<LAYER>_<SUFFIX>` (layer name upper-cased with underscores preserved,
suffix identical to the global name minus the `LLM_` prefix), and the resolved per-layer
value SHALL take precedence over the global value, which SHALL take precedence over the
layer's code default. Absent or blank-after-strip SHALL yield the next level down. An
invalid value SHALL fail settings import naming the variable, the raw value, and the rule,
identically to the existing typed knobs.

The knob table and a pure `llm_env_names()` function returning the exact generated
variable-name set (global plus every per-layer name) SHALL live in an import-safe module
(`server/conf/llm_knobs.py`) that performs no environment reads. `server/conf/settings.py`
SHALL publish `LLM_ENV_NAMES` derived from that function, and
`server/conf/test_settings.py` SHALL remove every name the function returns from
`os.environ` before importing production settings, so a test run's effective settings
never inherit shell LLM configuration.

#### Scenario: A global knob reaches every layer
- **WHEN** the settings module is imported with `LLM_MODEL=gpt-4o-mini` and no per-layer
  variables
- **THEN** every layer's effective profile model is `gpt-4o-mini`

#### Scenario: A per-layer override wins over the global value
- **WHEN** `LLM_MODEL=llama3.2` and `LLM_CHARACTER_CREATION_MODEL=qwen2.5-32b-instruct`
  are both present
- **THEN** the `character_creation` profile's model is `qwen2.5-32b-instruct`, every other
  layer's profile model is `llama3.2`, and no other field is affected

#### Scenario: An invalid LLM knob fails the boot
- **WHEN** the settings module is imported with `LLM_TOP_P=1.5`
- **THEN** the import fails naming `LLM_TOP_P`, the raw value, and the bounds rule

#### Scenario: Blank optional knobs omit rather than zero
- **WHEN** the settings module is imported with `LLM_FREQUENCY_PENALTY` present-but-blank
- **THEN** every profile's `frequency_penalty` is `None` (omitted), not `0`

#### Scenario: Test settings sanitize every generated name
- **WHEN** `server/conf/test_settings.py` is imported with `LLM_MODEL` and
  `LLM_ACTION_OPTIONS_MAX_TOKENS` exported in the shell environment
- **THEN** the effective settings equal their code defaults because both names were
  removed from `os.environ` before the production settings import

#### Scenario: The published name set equals the inert definition
- **WHEN** the settings module has loaded
- **THEN** `LLM_ENV_NAMES` equals `frozenset(llm_env_names())` exactly (set equality, not
  a cardinality count), and the function's global subset equals the documented knob list
  above

### Requirement: The base URL environment reader is the settings module
The environment variable that selects the LLM endpoint base URL SHALL be named
`LLM_BASE_URL` and SHALL be read by `server/conf/settings.py`, not by
`world/ai/profiles.py`. The name `OLLAMA_BASE_URL` SHALL NOT be read by any module, SHALL
NOT appear in `.env.example` or `compose.yaml`, and SHALL NOT be listed in the inventory
contract's external-reader allow-list.

#### Scenario: The old variable name is inert
- **WHEN** the settings module is imported with `OLLAMA_BASE_URL` set and `LLM_BASE_URL`
  unset
- **THEN** every profile's base URL is the code default and no environment read for
  `OLLAMA_BASE_URL` occurs

#### Scenario: Compose injects the renamed variable
- **WHEN** the compose configuration is rendered with `LLM_BASE_URL` unset on the host
- **THEN** the evennia service receives `LLM_BASE_URL` with the host-gateway default and
  no `OLLAMA_BASE_URL` entry

## MODIFIED Requirements

### Requirement: Configuration layers follow default, environment, secret precedence
The effective value of an environment-overridable setting SHALL be resolved in the order
code default < same-named environment variable < `server/conf/secret_settings.py`: the
environment assignment SHALL happen in `settings.py` above the existing `secret_settings`
import, and a setting defined in `secret_settings.py` SHALL therefore override the
environment value without any change to the import structure. For the LLM profile family
the environment level is two-tier (code default < global `LLM_<SUFFIX>` variable <
per-layer `LLM_<LAYER>_<SUFFIX>` variable) and the secret level merges **per layer**:
settings resolution SHALL snapshot the fully environment-resolved raw profile map before
the `secret_settings` import, and a `secret_settings.py` `LLM_PROFILES` map SHALL replace
wholesale only the layers it names, every other layer keeping its environment-resolved
entry. Secrets (`SECRET_KEY` and equivalents) SHALL NOT be moved to the environment:
`secret_settings.py` remains their only sanctioned location, subject only to the scoped
`LLM_API_KEY` exception introduced by the endpoint-wire configuration.

#### Scenario: An environment value overrides the code default
- **WHEN** `ART_SD_TIMEOUT_SECONDS=120` is present and no `secret_settings` module defines it
- **THEN** the effective setting is the integer `120`

#### Scenario: A secret-settings value overrides the environment
- **WHEN** `ART_SD_TIMEOUT_SECONDS=120` is present and a `server.conf.secret_settings` module that
  defines `ART_SD_TIMEOUT_SECONDS = 90` is imported over it
- **THEN** the effective setting is `90` and no environment value reached it

#### Scenario: Secret settings replace only the layers they name
- **WHEN** `LLM_MODEL=llama3.2` and `LLM_ACTION_OPTIONS_MAX_TOKENS=400` are present and
  `secret_settings.py` defines an `LLM_PROFILES` map whose sole entry is a complete
  `character_creation` profile
- **THEN** the `action_options` profile's `max_tokens` is `400` and every layer absent
  from the secret map keeps its environment-resolved values, while `character_creation`
  equals the secret entry

### Requirement: Environment inventory and configuration guide are version-controlled and exact
The repository SHALL track `.env.example` as the exact inventory of environment variables
this project reads: every active (uncommented) entry SHALL be a variable that
`server/conf/settings.py` or a documented external reader (Evennia's launcher, compose.yaml
interpolation) actually reads, and no variable the runtime ignores SHALL be presented as an
entry. Environment reads generated by the LLM knob table SHALL be contract-checked against
the inert knob module's pure `llm_env_names()` definition — exact set equality between the
global `LLM_*` knob entries of `.env.example` — parsed from `NAME=` assignments with
comment style irrelevant, because typed knobs ship commented in that file by convention —
and the function's global names, plus equality of `settings.LLM_ENV_NAMES` and the
function, in addition to literal syntax-tree extraction for every other reader. Per-layer
`LLM_<LAYER>_<SUFFIX>` names SHALL be documented through the global entries plus their
documented suffix grammar rather than enumerated in `.env.example`. The repository SHALL
provide a Docsify developer guide at
`docs/development/settings-and-environment.md`, linked from `docs/_sidebar.md`,
documenting the three configuration layers, their precedence, the full variable inventory
with types and defaults, what must stay in `secret_settings.py`, the bare-metal export
recipe, the restart-to-apply rule, and the procedure for making a future setting
env-overridable; the `ART_SD_*` table in `docs/gm/prompts.md` SHALL reference that guide.

#### Scenario: No dead variables are advertised
- **WHEN** the active entries of `.env.example` are parsed and each key is checked against the
  environment reads extracted from the `server/conf/settings.py` syntax tree, the inert
  knob module's generated-name definition, and an explicit key-to-reader allow-list for
  external readers (launcher, compose.yaml, harness, tooling)
- **THEN** every key resolves to a real reader or a generated knob name (not a comment or
  docstring mention) and the check reports any key that has no reader

#### Scenario: Table-generated knobs match the inert definition exactly
- **WHEN** the inventory check compares the parsed global `LLM_*` entries of `.env.example`
  (comment style irrelevant) against the knob module's generated global names
- **THEN** the two sets are exactly equal, and no LLM knob needs an external-reader
  allow-list entry

#### Scenario: The guide and its sidebar entry exist
- **WHEN** the documentation tree is inspected
- **THEN** `docs/development/settings-and-environment.md` exists, names every environment-overridable
  setting with its type, default, and validation rule, and `docs/_sidebar.md` links the page
